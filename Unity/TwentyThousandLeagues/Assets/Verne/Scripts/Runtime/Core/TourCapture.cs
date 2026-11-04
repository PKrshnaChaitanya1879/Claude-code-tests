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
        public bool walkTest;

        /// <summary>
        /// The walk test: the real player, driven by the movement input, follows the guide's waypoints from the first to the
        /// last. Where it makes no headway it is stuck: the spot and whatever is in front are logged, then it is set 2 m on
        /// and carries on. Logs/tour/scene_walk.txt.
        /// </summary>
        IEnumerator Walk()
        {
            var log = new System.Text.StringBuilder();
            var m = PlayerMotor.Instance;
            var guide = Object.FindAnyObjectByType<DiverGuide>();
            if (m == null || guide == null || guide.waypoints == null || guide.waypoints.Length < 2) { log.AppendLine("no player or guide"); File.WriteAllText(Path.Combine("Logs/tour", scene + "_walk.txt"), log.ToString()); yield break; }
            var lamp = m.GetComponentInChildren<RuhmkorffLamp>(true);
            if (lamp != null) lamp.SendMessage("SetOn", false, SendMessageOptions.DontRequireReceiver);
            float ts = Time.timeScale; Time.timeScale = 1f;   // the motor clamps a frame to 0.05 s: real time, or the test outruns it
            var wps = guide.waypoints;
            var start = wps[0] + (wps[0] - wps[1]).normalized * 3f; start.y += 0.3f;
            m.Teleport(start, 0f);
            int stuck = 0; float t0 = Time.realtimeSinceStartup;
            for (int i = 0; i < wps.Length; i++)
            {
                var target = wps[i];
                Vector3 last = m.transform.position; float since = 0f;
                while (true)
                {
                    var p = m.transform.position;
                    var d = target - p; d.y = 0f;
                    if (d.magnitude < 1.4f) break;
                    float yaw = Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
                    m.SetLook(yaw, 0f);
                    VerneInput.AutoMove = new Vector2(0f, 1f);
                    yield return null;
                    since += Mathf.Min(Time.deltaTime, 0.05f);   // the motor's own clock
                    if (since > 4f)
                    {
                        if (new Vector2(m.transform.position.x - last.x, m.transform.position.z - last.z).magnitude < 0.6f)   // a walk at 0.95 m/s covers ~3.5 m
                        {
                            stuck++;
                            string what = Physics.SphereCast(m.transform.position + Vector3.up * 0.9f, 0.3f, d.normalized, out var h, 2f, ~0, QueryTriggerInteraction.Ignore) ? h.collider.name + " (" + h.collider.GetType().Name + ")" : "nothing in front (slope or step)";
                            log.AppendLine($"STUCK at ({p.x:0.0}, {p.y:0.0}, {p.z:0.0}) going to waypoint {i} ({target.x:0}, {target.z:0}): {what}");
                            m.Teleport(p + d.normalized * 2f + Vector3.up * 1.0f, yaw);
                        }
                        last = m.transform.position; since = 0f;
                    }
                    if (Time.realtimeSinceStartup - t0 > 420f) { log.AppendLine("timed out"); i = wps.Length; break; }
                }
                log.AppendLine($"reached waypoint {i} ({target.x:0.0}, {target.y:0.0}, {target.z:0.0}) at {Time.realtimeSinceStartup - t0:0}s");
            }
            VerneInput.AutoMove = null; Time.timeScale = ts;
            log.Insert(0, stuck == 0 ? "WALK OK: the whole way on foot, never stuck\n" : $"WALK: stuck {stuck} times\n");
            File.WriteAllText(Path.Combine("Logs/tour", scene + "_walk.txt"), log.ToString());
        }

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
                    if (v.name.StartsWith("diversfront"))
                    {   // in front of the first diver, looking back at him as he walks toward the camera (his feet and helmet port)
                        var d = Object.FindAnyObjectByType<DiverPuppet>();
                        if (d != null)
                        {
                            var dp = d.transform.position; var f = d.transform.forward;
                            p = dp + f * 3.2f; p.y = -9999f;
                            var look = dp - p; look.y = 0f;
                            yawV = Mathf.Atan2(look.x, look.z) * Mathf.Rad2Deg;
                        }
                    }
                    else if (v.name.StartsWith("divers"))
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
            if (walkTest) yield return Walk();
            File.WriteAllText(Path.Combine("Logs/tour", scene + "_done.txt"), System.DateTime.Now.ToString("HH:mm:ss"));
            onDone?.Invoke();
        }
    }
}
