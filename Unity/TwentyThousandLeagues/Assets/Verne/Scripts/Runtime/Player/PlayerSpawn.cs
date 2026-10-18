using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Marks where the player starts in a scene and in what mode. At play time it builds the
    /// player rig from code (CharacterController, head pivot, camera, interactor, footsteps) so
    /// there is no prefab to break.
    /// </summary>
    public class PlayerSpawn : MonoBehaviour
    {
        public MoveMode mode = MoveMode.Air;
        public float nearClip = 0.05f;
        public float farClip = 400f;
        [Tooltip("Underwater: the decal for the visitor's own lamp-following contact shadow (LampShadow).")]
        public Material shadowMaterial;

        void Start()
        {
            if (PlayerMotor.Instance != null) return;
            var motor = Build(transform.position, transform.eulerAngles.y, mode, nearClip, farClip);
            if (motor != null)
            {
                // the divers' NavMesh agents step round the visitor instead of into him
                var ob = motor.gameObject.AddComponent<UnityEngine.AI.NavMeshObstacle>();
                ob.shape = UnityEngine.AI.NavMeshObstacleShape.Capsule; ob.radius = 0.4f; ob.height = 1.8f; ob.center = new Vector3(0, 0.9f, 0); ob.carving = false;
            }
            if (motor != null && shadowMaterial != null)
            {
                var ls = motor.gameObject.AddComponent<LampShadow>();
                ls.material = shadowMaterial; ls.radius = 0.45f;
            }
        }

        public static PlayerMotor Build(Vector3 pos, float yaw, MoveMode mode, float near = 0.05f, float far = 400f)
        {
            // remove any editor/preview camera so the player camera is the only one tagged MainCamera
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None))
                if (c.CompareTag("MainCamera") && c.GetComponentInParent<PlayerMotor>() == null) c.gameObject.SetActive(false);

            var root = new GameObject("Player");
            root.layer = LayerMask.NameToLayer("Player") >= 0 ? LayerMask.NameToLayer("Player") : 0;
            root.transform.SetPositionAndRotation(pos, Quaternion.Euler(0, yaw, 0));
            var cc = root.AddComponent<CharacterController>();
            cc.center = new Vector3(0, 0.875f, 0);

            var head = new GameObject("Head").transform;
            head.SetParent(root.transform, false);
            head.localPosition = new Vector3(0, 1.6f, 0);

            var camGo = new GameObject("Player Camera");
            camGo.tag = "MainCamera";
            camGo.transform.SetParent(head, false);
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = near;
            cam.farClipPlane = far;
            cam.fieldOfView = GameSettings.Current.fieldOfView;
            camGo.AddComponent<AudioListener>();
            camGo.AddComponent<Interactor>();
            camGo.AddComponent<PlayerCamera>();

            var motor = root.AddComponent<PlayerMotor>();
            motor.head = head;
            motor.viewCamera = cam;
            motor.SetMode(mode);
            motor.SetLook(yaw, 0f);
            root.AddComponent<Footsteps>();
            head.gameObject.AddComponent<RuhmkorffLamp>();   // follows the look a little, so the beam lands where you look

            VerneInput.LockCursor(true);
            return motor;
        }
    }
}
