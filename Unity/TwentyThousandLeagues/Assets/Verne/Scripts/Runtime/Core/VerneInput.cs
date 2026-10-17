using UnityEngine;
#if VERNE_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace Verne
{
    /// <summary>
    /// One place that reads keyboard, mouse and gamepad. The project runs with "Both" input
    /// handlers, so the legacy Input Manager covers keyboard and mouse and the Input System
    /// package adds the gamepad. Everything else in the game asks this class, never Input directly.
    /// </summary>
    public static class VerneInput
    {
        /// <summary>When true (pause menu, notes), gameplay input reads as zero.</summary>
        public static bool GameplayBlocked
        {
            get => s_Blocked || Time.frameCount <= s_SuppressUntilFrame;
            set { if (s_Blocked && !value) s_SuppressUntilFrame = Time.frameCount + 1; s_Blocked = value; }
        }
        static bool s_Blocked;
        static int s_SuppressUntilFrame = -1;

        static bool Legacy => true;

        public static Vector2 Move
        {
            get
            {
                if (GameplayBlocked) return Vector2.zero;
                Vector2 v = Vector2.zero;
                if (Legacy)
                {
                    if (Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.UpArrow)) v.y += 1f;
                    if (Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.DownArrow)) v.y -= 1f;
                    if (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow)) v.x += 1f;
                    if (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow)) v.x -= 1f;
                }
#if VERNE_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
                var pad = Gamepad.current;
                if (pad != null)
                {
                    Vector2 s = pad.leftStick.ReadValue();
                    if (s.sqrMagnitude > v.sqrMagnitude) v = s;
                }
#endif
                return Vector2.ClampMagnitude(v, 1f);
            }
        }

        /// <summary>Look delta in degrees for this frame (already scaled by sensitivity and invert).</summary>
        public static Vector2 Look
        {
            get
            {
                if (GameplayBlocked) return Vector2.zero;
                var s = GameSettings.Current;
                Vector2 d = Vector2.zero;
                if (Legacy && Cursor.lockState == CursorLockMode.Locked)
                    d += new Vector2(Input.GetAxisRaw("Mouse X"), Input.GetAxisRaw("Mouse Y")) * (2.0f * s.mouseSensitivity);
#if VERNE_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
                var pad = Gamepad.current;
                if (pad != null)
                {
                    Vector2 r = pad.rightStick.ReadValue();
                    // response curve: fine aim near centre, quick turns at full deflection
                    r = r * r.magnitude;
                    d += r * (140f * s.padSensitivity * Time.unscaledDeltaTime);
                }
#endif
                if (s.invertY) d.y = -d.y;
                return d;
            }
        }

        public static bool InteractDown => !GameplayBlocked && (Input.GetKeyDown(KeyCode.E) || Input.GetMouseButtonDown(0) || PadDown(PadButton.South));
        public static bool InteractHeld => !GameplayBlocked && (Input.GetKey(KeyCode.E) || Input.GetMouseButton(0) || PadHeld(PadButton.South));
        public static bool InteractUp => !GameplayBlocked && (Input.GetKeyUp(KeyCode.E) || Input.GetMouseButtonUp(0) || PadUp(PadButton.South));
        public static bool SprintHeld => !GameplayBlocked && (Input.GetKey(KeyCode.LeftShift) || PadHeld(PadButton.LeftStickPress));
        public static bool CrouchDown => !GameplayBlocked && (Input.GetKeyDown(KeyCode.C) || Input.GetKeyDown(KeyCode.LeftControl) || PadDown(PadButton.East));
        public static bool KneelDown => !GameplayBlocked && (Input.GetKeyDown(KeyCode.K) || PadDown(PadButton.North));
        /// <summary>The Ruhmkorff lamp's screw (L / right shoulder).</summary>
        public static bool LampDown => !GameplayBlocked && (Input.GetKeyDown(KeyCode.L) || PadDown(PadButton.RightShoulder));
        public static bool JumpDown => !GameplayBlocked && (Input.GetKeyDown(KeyCode.Space) || PadDown(PadButton.West));
        public static bool PauseDown => Input.GetKeyDown(KeyCode.Escape) || Input.GetKeyDown(KeyCode.P) || PadDown(PadButton.Start);
        public static bool SubmitDown => Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter) || Input.GetKeyDown(KeyCode.Space) || PadDown(PadButton.South);
        public static bool CancelDown => Input.GetKeyDown(KeyCode.Escape) || Input.GetKeyDown(KeyCode.Backspace) || PadDown(PadButton.East);

        /// <summary>Menu navigation: -1, 0 or +1 per axis, with key repeat handled by the caller.</summary>
        public static Vector2Int MenuNav
        {
            get
            {
                int x = 0, y = 0;
                if (Input.GetKeyDown(KeyCode.UpArrow) || Input.GetKeyDown(KeyCode.W)) y = 1;
                if (Input.GetKeyDown(KeyCode.DownArrow) || Input.GetKeyDown(KeyCode.S)) y = -1;
                if (Input.GetKeyDown(KeyCode.LeftArrow) || Input.GetKeyDown(KeyCode.A)) x = -1;
                if (Input.GetKeyDown(KeyCode.RightArrow) || Input.GetKeyDown(KeyCode.D)) x = 1;
#if VERNE_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
                var pad = Gamepad.current;
                if (pad != null)
                {
                    if (pad.dpad.up.wasPressedThisFrame) y = 1;
                    if (pad.dpad.down.wasPressedThisFrame) y = -1;
                    if (pad.dpad.left.wasPressedThisFrame) x = -1;
                    if (pad.dpad.right.wasPressedThisFrame) x = 1;
                }
#endif
                return new Vector2Int(x, y);
            }
        }

        public enum PadButton { South, East, West, North, Start, LeftStickPress, RightShoulder }

        static bool PadDown(PadButton b)
        {
#if VERNE_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
            var c = Control(b); return c != null && c.wasPressedThisFrame;
#else
            return false;
#endif
        }
        static bool PadHeld(PadButton b)
        {
#if VERNE_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
            var c = Control(b); return c != null && c.isPressed;
#else
            return false;
#endif
        }
        static bool PadUp(PadButton b)
        {
#if VERNE_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
            var c = Control(b); return c != null && c.wasReleasedThisFrame;
#else
            return false;
#endif
        }

#if VERNE_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
        static UnityEngine.InputSystem.Controls.ButtonControl Control(PadButton b)
        {
            var pad = Gamepad.current;
            if (pad == null) return null;
            switch (b)
            {
                case PadButton.South: return pad.buttonSouth;
                case PadButton.East: return pad.buttonEast;
                case PadButton.West: return pad.buttonWest;
                case PadButton.North: return pad.buttonNorth;
                case PadButton.Start: return pad.startButton;
                case PadButton.RightShoulder: return pad.rightShoulder;
                default: return pad.leftStickButton;
            }
        }
#endif

        public static bool UsingGamepad
        {
            get
            {
#if VERNE_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
                var pad = Gamepad.current;
                return pad != null && pad.lastUpdateTime > System.Math.Max(LastMouseTime, 0.01);
#else
                return false;
#endif
            }
        }

        static double LastMouseTime
        {
            get
            {
#if VERNE_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
                double t = 0;
                if (Mouse.current != null) t = Mouse.current.lastUpdateTime;
                if (Keyboard.current != null) t = System.Math.Max(t, Keyboard.current.lastUpdateTime);
                return t;
#else
                return 0;
#endif
            }
        }

        public static void LockCursor(bool locked)
        {
            Cursor.lockState = locked ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !locked;
        }
    }
}
