using UnityEngine;

namespace Verne
{
    /// <summary>
    /// A diver in the stiff india-rubber dress, as a puppet of rigid Blender parts (Source/blender/diver_parts.py)
    /// animated procedurally: the heavy walk on leaden soles, idle breathing, and the gestures the book's
    /// scenes need (I.XV–XVII, XXIV): beckon, kneel, kneel with a hand to the breast, dig with the pickaxe,
    /// carry on the shoulders, lower, and the last adieu. Poses blend smoothly; nothing snaps.
    /// Joints (built by the bootstrap): Hips, Torso, Head, Shoulder.L/R, Elbow.L/R, Hand.R, Hip.L/R, Knee.L/R, Ankle.L/R.
    /// Rotations about X: negative swings a limb forward.
    /// </summary>
    public class DiverPuppet : MonoBehaviour
    {
        public enum Gesture { Idle, Walk, Beckon, Kneel, KneelCross, Dig, Carry, Lower, Adieu, KneelAdieu }
        public Gesture gesture = Gesture.Idle;
        [Tooltip("Steps per second at full walking pace (heavy: 'I am not superman').")]
        public float cadence = 0.75f;
        public float speed;                       // set by the mover, m/s
        public float blend = 3f;

        Transform m_Hips, m_Torso, m_Head, m_ShL, m_ShR, m_ElL, m_ElR, m_HipL, m_HipR, m_KnL, m_KnR, m_AnL, m_AnR;
        float m_AnW;
        Vector3 m_HipsRest;
        float m_Phase, m_T;
        // current joint angles (degrees about X unless noted) and root drop
        float aTorso, aHead, aShL, aShR, aElL, aElR, aHipL, aHipR, aKnL, aKnR, aShRz, drop;

        void Awake()
        {
            m_Hips = Find("Hips"); m_Torso = Find("Torso"); m_Head = Find("Head");
            m_ShL = Find("Shoulder.L"); m_ShR = Find("Shoulder.R"); m_ElL = Find("Elbow.L"); m_ElR = Find("Elbow.R");
            m_HipL = Find("Hip.L"); m_HipR = Find("Hip.R"); m_KnL = Find("Knee.L"); m_KnR = Find("Knee.R");
            m_AnL = Find("Ankle.L"); m_AnR = Find("Ankle.R");
            if (m_Hips != null) m_HipsRest = m_Hips.localPosition;
            m_Phase = Random.value * 6.28f;
        }

        Transform Find(string n)
        {
            foreach (var t in GetComponentsInChildren<Transform>(true)) if (t.name == n) return t;
            return null;
        }

        void Update()
        {
            float dt = Time.deltaTime; m_T += dt;
            float walk = Mathf.Clamp01(speed / 0.9f);
            m_Phase += dt * cadence * Mathf.PI * 2f * Mathf.Lerp(0.4f, 1f, walk) * (gesture == Gesture.Walk ? 1f : 0f);
            float s = Mathf.Sin(m_Phase), c = Mathf.Cos(m_Phase);
            float breath = Mathf.Sin(m_T * 1.3f);

            // targets
            float tTorso = breath * 1f, tHead = 0f, tShL = 4f, tShR = 4f, tElL = -10f, tElR = -10f, tHipL = 0f, tHipR = 0f, tKnL = 0f, tKnR = 0f, tShRz = 0f, tDrop = 0f;
            switch (gesture)
            {
                case Gesture.Walk:
                    tHipL = -24f * s * walk; tHipR = 24f * s * walk;
                    // a knee bends while its leg swings FORWARD (hip angle falling), straight while it bears weight
                    tKnL = Mathf.Max(0f, 38f * c) * walk; tKnR = Mathf.Max(0f, -38f * c) * walk;
                    tShL = 14f * s * walk; tShR = -14f * s * walk;
                    tTorso = -6f * walk + 2f * Mathf.Abs(s);
                    tDrop = -0.035f * Mathf.Abs(s) * walk;
                    break;
                case Gesture.Beckon:
                    tShR = -85f; tElR = -55f + 30f * Mathf.Sin(m_T * 5f); tShRz = 10f; break;
                case Gesture.Kneel:
                    tHipL = 0f; tHipR = 0f; tKnL = 88f; tKnR = 88f; tDrop = -0.38f; tTorso = -10f; tHead = -14f; tShL = -8f; tShR = -8f; break;
                case Gesture.KneelCross:
                    tKnL = 88f; tKnR = 88f; tDrop = -0.38f; tTorso = -12f; tHead = -20f; tShR = -55f; tElR = -95f; tShRz = -20f; tShL = 2f; break;
                case Gesture.Dig:
                {
                    float sw = Mathf.Sin(m_T * 2.4f);          // the pickaxe rises and falls ("sparks on the flint", M4 timeline)
                    tShL = tShR = Mathf.Lerp(-160f, -35f, sw * 0.5f + 0.5f); tElL = tElR = Mathf.Lerp(-30f, -5f, sw * 0.5f + 0.5f);
                    tTorso = Mathf.Lerp(-5f, -28f, sw * 0.5f + 0.5f); tHipL = -10f; tHipR = 10f; tKnL = tKnR = 10f; tDrop = -0.05f; break;
                }
                case Gesture.Carry:
                    tShL = tShR = -100f; tElL = tElR = -75f; tTorso = -3f; break;   // hands at the shoulder, the burden on it
                case Gesture.Lower:
                    tShL = tShR = -65f; tElL = tElR = -20f; tTorso = -32f; tKnL = tKnR = 35f; tHipL = tHipR = -25f; tDrop = -0.12f; break;
                case Gesture.KneelAdieu:     // "they knelt again, and all extended their hands in sign of a last adieu"
                    tKnL = 88f; tKnR = 88f; tDrop = -0.38f; tTorso = -6f; tHead = -6f; tShL = tShR = -78f + 3f * Mathf.Sin(m_T * 0.8f); tElL = tElR = -8f; break;
                case Gesture.Adieu:
                    tShR = -165f + 8f * Mathf.Sin(m_T * 1.2f); tElR = -5f; tShRz = 12f; tHead = 6f; break;
            }
            float k = 1f - Mathf.Exp(-blend * dt);
            aTorso = Mathf.Lerp(aTorso, tTorso, k); aHead = Mathf.Lerp(aHead, tHead, k);
            aShL = Mathf.Lerp(aShL, tShL, k); aShR = Mathf.Lerp(aShR, tShR, k); aElL = Mathf.Lerp(aElL, tElL, k); aElR = Mathf.Lerp(aElR, tElR, k);
            aHipL = Mathf.Lerp(aHipL, tHipL, k); aHipR = Mathf.Lerp(aHipR, tHipR, k); aKnL = Mathf.Lerp(aKnL, tKnL, k); aKnR = Mathf.Lerp(aKnR, tKnR, k);
            aShRz = Mathf.Lerp(aShRz, tShRz, k); drop = Mathf.Lerp(drop, tDrop, k);

            if (m_Hips != null) m_Hips.localPosition = m_HipsRest + Vector3.up * drop;
            Set(m_Torso, aTorso); Set(m_Head, aHead);
            Set(m_ShL, aShL); Set(m_ElL, aElL); Set(m_HipL, aHipL); Set(m_KnL, aKnL); Set(m_HipR, aHipR); Set(m_KnR, aKnR); Set(m_ElR, aElR);
            // lead soles stay flat: the ankle undoes most of hip + knee (and lets the toe lift a little on the swing)
            m_AnW = Mathf.Lerp(m_AnW, gesture == Gesture.Walk ? 0.85f : 0f, k);
            Set(m_AnL, -(aHipL + aKnL) * m_AnW); Set(m_AnR, -(aHipR + aKnR) * m_AnW);
            if (m_ShR != null) m_ShR.localRotation = Quaternion.Euler(aShR, 0f, aShRz);
        }

        static void Set(Transform t, float x) { if (t != null) t.localRotation = Quaternion.Euler(x, 0f, 0f); }
    }
}
