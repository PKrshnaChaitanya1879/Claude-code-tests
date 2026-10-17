using System;
using UnityEngine;

namespace Verne
{
    public enum MoveMode { Air, Suited, Water }
    public enum Stance { Standing, Crouching, Kneeling }

    /// <summary>
    /// Weighty first-person movement in the spirit of BioShock: human speeds, real acceleration
    /// and braking, head-bob that follows the gait, landings that dip the view.
    ///   Air    aboard the Nautilus, ordinary clothes.
    ///   Suited in the diving dress inside the ship ("glued to the deck by my leaden soles"): a shuffle.
    ///   Water  on the sea bottom: slow, heavy boots, reduced effective gravity, drag.
    /// The camera sits inside the CharacterController capsule, so it can never enter a wall.
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    [DisallowMultipleComponent]
    public class PlayerMotor : MonoBehaviour
    {
        [Serializable]
        public struct ModeParams
        {
            public float walkSpeed, sprintSpeed, crouchSpeed;
            public float accel, decel;           // m/s²
            public float gravity;                // effective, after buoyancy
            public float jumpSpeed;
            public float bobFrequency;           // steps per metre factor
            public float bobAmplitude;           // metres
            public float stepLength;             // metres per footstep
            public float lookDamping;            // 0 = raw, 1 = heavy
        }

        public static PlayerMotor Instance { get; private set; }

        [Header("References")]
        public Transform head;                   // pitch pivot at eye height
        public Camera viewCamera;

        [Header("Body")]
        public float standHeight = 1.75f;
        public float crouchHeight = 1.15f;
        public float kneelHeight = 1.0f;
        public float radius = 0.3f;
        public float eyeBelowTop = 0.14f;

        [Header("Modes")]
        public MoveMode mode = MoveMode.Air;
        public ModeParams air = new ModeParams
        {
            walkSpeed = 1.55f, sprintSpeed = 2.9f, crouchSpeed = 0.9f, accel = 6.5f, decel = 9f,
            gravity = 9.81f, jumpSpeed = 3.0f, bobFrequency = 1.0f, bobAmplitude = 0.028f, stepLength = 0.72f, lookDamping = 0.0f
        };
        public ModeParams suited = new ModeParams
        {
            walkSpeed = 0.35f, sprintSpeed = 0.35f, crouchSpeed = 0.25f, accel = 0.9f, decel = 2.5f,
            gravity = 9.81f, jumpSpeed = 0f, bobFrequency = 0.6f, bobAmplitude = 0.05f, stepLength = 0.35f, lookDamping = 0.35f
        };
        public ModeParams water = new ModeParams
        {
            walkSpeed = 0.95f, sprintSpeed = 1.35f, crouchSpeed = 0.55f, accel = 1.6f, decel = 2.2f,
            gravity = 3.2f, jumpSpeed = 1.6f, bobFrequency = 0.55f, bobAmplitude = 0.045f, stepLength = 0.8f, lookDamping = 0.25f
        };

        [Header("Look")]
        public float pitchMin = -80f, pitchMax = 82f;

        public Stance stance { get; private set; } = Stance.Standing;
        public bool Grounded => m_Grounded;
        public Vector3 Velocity => m_Velocity;
        public float SpeedNormalized => m_HorizontalSpeed / Mathf.Max(0.01f, Params.walkSpeed);
        public bool MovementLocked { get; set; }
        public bool LookLocked { get; set; }
        public Ladder ActiveLadder { get; set; }

        /// <summary>Raised at every footfall with (surface tag, loudness 0..1).</summary>
        public event Action<string, float> Footstep;
        /// <summary>Raised on landing with the impact speed in m/s.</summary>
        public event Action<float> Landed;

        CharacterController m_CC;
        Vector3 m_Velocity;
        float m_HorizontalSpeed;
        bool m_Grounded, m_WasGrounded;
        float m_Yaw, m_Pitch;
        Vector2 m_LookSmoothed;
        float m_StepAccum, m_BobPhase;
        float m_LandDip, m_LandDipVel;
        float m_CurrentHeight;
        Vector3 m_HeadBase;
        float m_HeadTilt;
        float m_AirTime;

        public ModeParams Params => mode == MoveMode.Water ? water : (mode == MoveMode.Suited ? suited : air);

        void Awake()
        {
            Instance = this;
            m_CC = GetComponent<CharacterController>();
            m_CC.radius = radius;
            m_CC.height = standHeight;
            m_CC.center = new Vector3(0, standHeight * 0.5f, 0);
            m_CC.skinWidth = Mathf.Max(0.02f, radius * 0.1f);
            m_CC.minMoveDistance = 0f;
            m_CC.slopeLimit = 42f;
            m_CC.stepOffset = 0.32f;
            m_CurrentHeight = standHeight;
            m_Yaw = transform.eulerAngles.y;
            if (viewCamera == null) viewCamera = GetComponentInChildren<Camera>();
            if (head == null && viewCamera != null) head = viewCamera.transform.parent;
        }

        void OnDestroy() { if (Instance == this) Instance = null; }

        public void SetMode(MoveMode m) { mode = m; }

        public void Teleport(Vector3 position, float yaw)
        {
            m_CC.enabled = false;
            transform.position = position;
            m_CC.enabled = true;
            m_Yaw = yaw; m_Pitch = 0f;
            m_Velocity = Vector3.zero;
        }

        public void SetLook(float yaw, float pitch) { m_Yaw = yaw; m_Pitch = Mathf.Clamp(pitch, pitchMin, pitchMax); }
        public float Yaw => m_Yaw;
        public float Pitch => m_Pitch;

        public void SetStance(Stance s)
        {
            if (s == stance) return;
            if (s == Stance.Standing && !HasHeadroom(standHeight)) return;
            if (s == Stance.Crouching && stance == Stance.Kneeling && !HasHeadroom(crouchHeight)) return;
            stance = s;
        }

        bool HasHeadroom(float targetHeight)
        {
            float extra = targetHeight - m_CC.height;
            if (extra <= 0f) return true;
            Vector3 top = transform.position + Vector3.up * (m_CC.height - radius);
            return !Physics.SphereCast(top, radius * 0.95f, Vector3.up, out _, extra + 0.02f, ~0, QueryTriggerInteraction.Ignore);
        }

        void Update()
        {
            float dt = Mathf.Min(Time.deltaTime, 0.05f);
            var p = Params;

            // ---- stance input
            if (!MovementLocked)
            {
                if (VerneInput.CrouchDown) SetStance(stance == Stance.Crouching ? Stance.Standing : Stance.Crouching);
                if (VerneInput.KneelDown) SetStance(stance == Stance.Kneeling ? Stance.Standing : Stance.Kneeling);
            }

            // ---- look (slightly damped in the dress and underwater: the helmet has weight)
            if (!LookLocked)
            {
                Vector2 look = VerneInput.Look;
                float k = p.lookDamping <= 0f ? 1f : 1f - Mathf.Exp(-dt * Mathf.Lerp(60f, 9f, p.lookDamping));
                m_LookSmoothed = Vector2.Lerp(m_LookSmoothed, look, k);
                if (p.lookDamping <= 0f) m_LookSmoothed = look;
                m_Yaw += m_LookSmoothed.x;
                m_Pitch = Mathf.Clamp(m_Pitch - m_LookSmoothed.y, pitchMin, pitchMax);
            }
            transform.rotation = Quaternion.Euler(0f, m_Yaw, 0f);

            // ---- capsule height follows stance
            float targetH = stance == Stance.Standing ? standHeight : (stance == Stance.Crouching ? crouchHeight : kneelHeight);
            m_CurrentHeight = Mathf.MoveTowards(m_CurrentHeight, targetH, dt * 2.2f);
            m_CC.height = m_CurrentHeight;
            m_CC.center = new Vector3(0f, m_CurrentHeight * 0.5f, 0f);

            // ---- movement
            Vector2 input = MovementLocked || stance == Stance.Kneeling ? Vector2.zero : VerneInput.Move;
            Vector3 wish = Vector3.zero;
            float targetSpeed = 0f;

            if (ActiveLadder != null && !MovementLocked)
            {
                ClimbLadder(input, dt);
                ApplyHead(dt, p);
                return;
            }

            if (input.sqrMagnitude > 0.0001f)
            {
                wish = transform.TransformDirection(new Vector3(input.x, 0f, input.y));
                bool sprint = VerneInput.SprintHeld && input.y > 0.3f && stance == Stance.Standing;
                targetSpeed = stance == Stance.Crouching ? p.crouchSpeed : (sprint ? p.sprintSpeed : p.walkSpeed);
                targetSpeed *= input.magnitude;
                // backing up and strafing are slower, as a person walks
                float back = Mathf.Clamp01(-input.y);
                targetSpeed *= Mathf.Lerp(1f, 0.7f, back) * Mathf.Lerp(1f, 0.85f, Mathf.Abs(input.x));
            }

            Vector3 horiz = new Vector3(m_Velocity.x, 0f, m_Velocity.z);
            Vector3 targetVel = wish.normalized * targetSpeed;
            float rate = targetVel.sqrMagnitude > horiz.sqrMagnitude ? p.accel : p.decel;
            if (!m_Grounded) rate *= mode == MoveMode.Water ? 0.6f : 0.25f; // little air control
            horiz = Vector3.MoveTowards(horiz, targetVel, rate * dt);

            // gravity and jumping
            float vy = m_Velocity.y;
            if (m_Grounded)
            {
                vy = -1.5f; // keep the controller pressed to slopes
                if (VerneInput.JumpDown && p.jumpSpeed > 0f && stance == Stance.Standing && !MovementLocked)
                {
                    vy = p.jumpSpeed;
                    m_Grounded = false;
                }
            }
            else
            {
                vy -= p.gravity * dt;
                if (mode == MoveMode.Water) vy = Mathf.Max(vy, -2.6f); // terminal sink speed in water
                else vy = Mathf.Max(vy, -30f);
            }

            m_Velocity = new Vector3(horiz.x, vy, horiz.z);
            float preVy = m_Velocity.y;
            CollisionFlags flags = m_CC.Move(m_Velocity * dt);
            m_WasGrounded = m_Grounded;
            m_Grounded = (flags & CollisionFlags.Below) != 0 || m_CC.isGrounded;
            if ((flags & CollisionFlags.Above) != 0 && m_Velocity.y > 0f) m_Velocity.y = 0f;

            // real horizontal speed after collisions (walking into a wall stops the bob)
            Vector3 actual = m_CC.velocity; actual.y = 0f;
            m_HorizontalSpeed = actual.magnitude;
            if (m_HorizontalSpeed < horiz.magnitude * 0.5f) m_Velocity = new Vector3(actual.x, m_Velocity.y, actual.z);

            if (!m_Grounded) m_AirTime += dt;
            if (m_Grounded && !m_WasGrounded)
            {
                float impact = -preVy;
                if (m_AirTime > 0.15f && impact > 1.0f)
                {
                    m_LandDipVel -= Mathf.Clamp(impact * 0.05f, 0.02f, 0.25f) * (mode == MoveMode.Water ? 0.6f : 1f) * 10f;
                    Landed?.Invoke(impact);
                    Footstep?.Invoke(SurfaceUnderfoot(), Mathf.Clamp01(impact / 5f));
                }
                m_AirTime = 0f;
            }

            // footsteps by distance
            if (m_Grounded && m_HorizontalSpeed > 0.08f)
            {
                m_StepAccum += m_HorizontalSpeed * dt;
                float stepLen = p.stepLength * (stance == Stance.Crouching ? 0.7f : 1f);
                if (m_StepAccum >= stepLen)
                {
                    m_StepAccum -= stepLen;
                    float loud = Mathf.Clamp01(m_HorizontalSpeed / Mathf.Max(0.1f, p.sprintSpeed)) * (stance == Stance.Crouching ? 0.5f : 1f);
                    Footstep?.Invoke(SurfaceUnderfoot(), Mathf.Lerp(0.35f, 1f, loud));
                }
            }
            else m_StepAccum = Mathf.Min(m_StepAccum, p.stepLength * 0.5f);

            ApplyHead(dt, p);
        }

        void ClimbLadder(Vector2 input, float dt)
        {
            var l = ActiveLadder;
            float climb = input.y * l.climbSpeed;
            // looking down while pressing forward descends, as in most shooters
            if (m_Pitch > 35f) climb = -climb;
            Vector3 move = l.transform.up * climb + transform.right * input.x * 0.4f;
            // gently pull toward the ladder's centre line
            Vector3 toLine = l.ClosestPointOnLine(transform.position) - transform.position;
            toLine.y = 0f;
            move += toLine * 4f;
            m_Velocity = move;
            m_CC.Move(move * dt);
            m_Grounded = false;
            m_HorizontalSpeed = Mathf.Abs(climb);
            m_StepAccum += Mathf.Abs(climb) * dt;
            if (m_StepAccum > 0.35f) { m_StepAccum = 0f; Footstep?.Invoke("ladder", 0.6f); }
            if (VerneInput.JumpDown) { ActiveLadder = null; m_Velocity = -l.transform.forward * 1.5f; }
        }

        void ApplyHead(float dt, ModeParams p)
        {
            if (head == null) return;

            // spring for landing dip
            float k = 90f, c = 14f;
            m_LandDipVel += (-k * m_LandDip - c * m_LandDipVel) * dt;
            m_LandDip += m_LandDipVel * dt;

            float eyeY = m_CurrentHeight - eyeBelowTop;
            if (stance == Stance.Kneeling) eyeY = m_CurrentHeight - 0.12f;

            // gait bob: vertical at twice the step frequency, lateral at the step frequency
            float speed01 = Mathf.Clamp01(m_HorizontalSpeed / Mathf.Max(0.1f, p.walkSpeed));
            float bobScale = GameSettings.Current.headBob;
            if (m_Grounded || mode == MoveMode.Water)
                m_BobPhase += dt * m_HorizontalSpeed / Mathf.Max(0.1f, p.stepLength) * Mathf.PI; // half a lateral cycle per step
            float amp = p.bobAmplitude * speed01 * bobScale;
            float bobY = Mathf.Sin(m_BobPhase * 2f) * amp;
            float bobX = Mathf.Cos(m_BobPhase) * amp * 0.6f;

            // idle breathing sway, stronger in the helmet
            float t = Time.time;
            float breath = (mode == MoveMode.Air ? 0.004f : 0.009f) * bobScale;
            bobY += Mathf.Sin(t * (mode == MoveMode.Air ? 1.3f : 0.9f)) * breath;

            m_HeadBase = new Vector3(bobX, eyeY + bobY + m_LandDip, 0f);

            // keep the eye inside the capsule's top hemisphere no matter what
            float maxEye = m_CurrentHeight - radius * 0.35f;
            m_HeadBase.y = Mathf.Min(m_HeadBase.y, maxEye);
            m_HeadBase.x = Mathf.Clamp(m_HeadBase.x, -radius * 0.4f, radius * 0.4f);

            head.localPosition = Vector3.Lerp(head.localPosition, m_HeadBase, 1f - Mathf.Exp(-dt * 18f));

            // roll a touch into strafes, tilt forward a little when kneeling
            float strafe = Vector3.Dot(m_Velocity, transform.right);
            float targetTilt = -strafe * (mode == MoveMode.Air ? 0.6f : 1.2f) * bobScale;
            m_HeadTilt = Mathf.Lerp(m_HeadTilt, targetTilt, 1f - Mathf.Exp(-dt * 5f));
            float kneelPitch = stance == Stance.Kneeling ? 8f : 0f;
            head.localRotation = Quaternion.Euler(m_Pitch + kneelPitch * 0.3f, 0f, m_HeadTilt);
        }

        string SurfaceUnderfoot()
        {
            if (Physics.SphereCast(transform.position + Vector3.up * (radius + 0.05f), radius * 0.8f, Vector3.down, out var hit, 0.4f, ~0, QueryTriggerInteraction.Ignore))
            {
                var s = hit.collider.GetComponentInParent<Surface>();
                if (s != null) return s.kind;
                var pm = hit.collider.sharedMaterial;
                if (pm != null) return pm.name.ToLowerInvariant();
            }
            return mode == MoveMode.Water ? "sand" : "iron";
        }
    }
}
