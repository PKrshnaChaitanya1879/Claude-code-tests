using System.Collections;
using UnityEngine;

namespace Verne
{
    /// <summary>
    /// The summit (II.IX), once Captain Nemo has arrived and the visitor stands near: Nemo, "picking up a piece of
    /// chalk-stone, advanced to a rock of black basalt, and traced the one word: ATLANTIS" (one letter at a time, his
    /// arm at work); a light letterbox-free pause; then, after the long watch, "the moon appeared through the mass of
    /// waters and threw her pale rays on the buried continent. It was but a gleam" (a cool light that rises and goes);
    /// then the return to the Nautilus. Control is never taken from the visitor.
    /// </summary>
    public class ChalkWriter : MonoBehaviour
    {
        public GameObject[] letters;
        public DiverGuide nemo;
        public Light moon;
        public float startRadius = 9f;
        bool m_Started; float m_Near;

        void Start() { if (letters != null) foreach (var l in letters) if (l != null) l.SetActive(false); }

        void Update()
        {
            if (m_Started) return;
            var p = PlayerMotor.Instance;
            if (p == null) return;
            if (Vector3.Distance(p.transform.position, transform.position) > startRadius) { m_Near = 0f; return; }
            m_Near += Time.deltaTime;
            if (nemo != null && !nemo.Arrived && m_Near < 25f) return;    // the visitor got there first: Nemo catches up, or the rite begins anyway
            m_Started = true;
            StartCoroutine(Rite());
        }

        IEnumerator Rite()
        {
            var puppet = nemo != null ? nemo.GetComponent<DiverPuppet>() : null;
            if (nemo != null) nemo.hold = true;
            if (puppet != null)
            {
                var to = transform.position - puppet.transform.position; to.y = 0f;
                if (to.sqrMagnitude > 1e-3f) puppet.transform.rotation = Quaternion.LookRotation(to);
            }
            Hud.Toast("“Captain Nemo ... picking up a piece of chalk-stone, advanced to a rock of black basalt, and traced the one word:”", 6f);
            yield return new WaitForSeconds(2.5f);
            if (letters != null)
                foreach (var l in letters)
                {
                    if (l == null) continue;
                    if (puppet != null) puppet.gesture = DiverPuppet.Gesture.Beckon;      // the arm raised, writing
                    yield return new WaitForSeconds(0.35f);
                    l.SetActive(true);
                    if (puppet != null) puppet.gesture = DiverPuppet.Gesture.Idle;
                    yield return new WaitForSeconds(0.45f);
                }
            Hud.Toast("ATLANTIS", 5f);
            yield return new WaitForSeconds(6f);
            Hud.Toast("“What a light shot through my mind! Atlantis, the ancient Meropis of Theopompus, the Atlantis of Plato.”", 7f);
            yield return new WaitForSeconds(16f);
            Hud.Toast("“Captain Nemo remained motionless, as if petrified in mute ecstasy, leaning on a mossy stone.”", 6f);
            yield return new WaitForSeconds(12f);
            // the moon's gleam
            Hud.Toast("“At this moment the moon appeared through the mass of waters and threw her pale rays on the buried continent. It was but a gleam, but what an indescribable effect!”", 9f);
            if (moon != null)
            {
                for (float t = 0; t < 1f; t += Time.deltaTime / 3f) { moon.intensity = Mathf.SmoothStep(0f, 0.35f, t); yield return null; }
                yield return new WaitForSeconds(3f);
                for (float t = 0; t < 1f; t += Time.deltaTime / 5f) { moon.intensity = Mathf.SmoothStep(0.35f, 0f, t); yield return null; }
                moon.intensity = 0f;
            }
            yield return new WaitForSeconds(3f);
            Hud.Toast("“The Captain rose, cast one last look on the immense plain, and then bade me follow him.”", 6f);
            yield return new WaitForSeconds(7f);
            SceneFlow.Load(SceneFlow.Nautilus);
        }
    }
}
