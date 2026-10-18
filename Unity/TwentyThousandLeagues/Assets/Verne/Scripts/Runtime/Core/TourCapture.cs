using System.Collections;
using System.IO;
using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Development aid: walks the real player to a list of viewpoints in play mode and saves a screenshot at each
    /// (Logs/tour/scene_name.png), so the look can be judged frame by frame on the target machine. Added only by the
    /// editor's Verne → Capture Tour; never present in a build.
    /// </summary>
    public class TourCapture : MonoBehaviour
    {
        public struct View { public string name; public Vector3 pos; public float yaw, pitch; public bool lamp; }
        public View[] views;
        public string scene;
        public float settle = 2.5f, intro = 9f;
        public System.Action onDone;

        IEnumerator Start()
        {
            Directory.CreateDirectory("Logs/tour");
            yield return new WaitForSecondsRealtime(intro);
            foreach (var v in views)
            {
                var m = PlayerMotor.Instance;
                if (m != null)
                {
                    var p = v.pos;
                    float yawV = v.yaw;
                    if (v.name.StartsWith("divers"))
                    {   // stand beside the first diver of the party, looking at him walking
                        var d = Object.FindAnyObjectByType<DiverPuppet>();
                        if (d != null)
                        {
                            var dp = d.transform.position; var side = d.transform.right;
                            p = dp + side * 2.6f + d.transform.forward * 1.2f; p.y = -9999f;
                            var look = dp - (dp + side * 2.6f + d.transform.forward * 1.2f);
                            yawV = Mathf.Atan2(look.x, look.z) * Mathf.Rad2Deg;
                        }
                    }
                    if (p.y < -9000f && Physics.Raycast(new Vector3(p.x, 400f, p.z), Vector3.down, out var hit, 2000f, ~0, QueryTriggerInteraction.Ignore)) p.y = hit.point.y + 0.05f;
                    else if (p.y < -9000f) p.y = 0.05f;
                    m.Teleport(p, yawV);
                    m.SetLook(yawV, v.pitch);
                    var lamp = m.GetComponentInChildren<RuhmkorffLamp>(true);
                    if (lamp != null) lamp.SendMessage("SetOn", v.lamp, SendMessageOptions.DontRequireReceiver);
                }
                if (v.name.Contains("window"))
                    foreach (var sp in Object.FindObjectsByType<SlidingPanels>(FindObjectsSortMode.None)) sp.SetOpen(1f);
                yield return new WaitForSecondsRealtime(v.name.Contains("window") ? settle + 3f : settle);
                ScreenCapture.CaptureScreenshot(Path.Combine("Logs/tour", scene + "_" + v.name + ".png"));
                yield return new WaitForSecondsRealtime(0.6f);
            }
            File.WriteAllText(Path.Combine("Logs/tour", scene + "_done.txt"), System.DateTime.Now.ToString("HH:mm:ss"));
            onDone?.Invoke();
        }
    }
}
