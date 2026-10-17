using System.Collections;
using UnityEngine;
using UnityEngine.UI;

namespace Verne
{
    /// <summary>
    /// The burial in the coral cemetery (I.XXIV), as the book tells it, once Captain Nemo has stopped in the glade
    /// and the visitor has come near: the grave dug slowly, the pickaxe sparkling on flint, the fish fleeing; the
    /// bearers lower the body in its white linen; Nemo with arms crossed on his breast and all his men kneel in
    /// prayer (the player may kneel too, K); the grave is filled into a slight mound; they rise, kneel again and
    /// extend their hands in a last adieu; then the procession returns to the Nautilus. A light letterbox for the
    /// length of the rite only (cinematic, not overdone); control is never taken from the player.
    /// </summary>
    public class BurialRite : MonoBehaviour
    {
        public DiverGuide nemo;
        public DiverPuppet digger;
        public DiverPuppet[] bearers;
        public Transform shroud;
        public GameObject mound;          // hidden until the grave is filled
        public Vector3 grave;             // world position of the grave
        public float startRadius = 8f;

        bool m_Started, m_PlayerKnelt;
        ParticleSystem m_Sparks;
        RectTransform m_Top, m_Bottom;

        void Start()
        {
            if (mound != null) mound.SetActive(false);
            if (bearers != null) foreach (var b in bearers) if (b != null) b.gesture = DiverPuppet.Gesture.Carry;
            BuildSparks();
            BuildLetterbox();
        }

        void Update()
        {
            if (m_Started) { WatchKneel(); return; }
            var p = PlayerMotor.Instance;
            if (p == null || nemo == null || !nemo.Arrived) return;
            var dg = digger != null ? digger.GetComponent<DiverGuide>() : null;
            if (dg != null && !dg.Arrived) return;      // the man with the pickaxe has reached the grave
            if (Vector3.Distance(p.transform.position, grave) < startRadius) StartCoroutine(Rite());
        }

        void WatchKneel()
        {
            var p = PlayerMotor.Instance;
            if (!m_PlayerKnelt && p != null && p.stance == Stance.Kneeling) { m_PlayerKnelt = true; Hud.Toast("I knelt with them.", 3f); }
        }

        IEnumerator Rite()
        {
            m_Started = true;
            nemo.hold = true;
            var nemoPuppet = nemo.GetComponent<DiverPuppet>();
            var diggerGuide = digger != null ? digger.GetComponent<DiverGuide>() : null;
            if (diggerGuide != null) diggerGuide.hold = true;
            StartCoroutine(Letterbox(true));
            Hud.Toast("“I understood all! This glade was a cemetery, this hole a tomb, this oblong object the body of the man who had died in the night!”", 6f);
            // the digging
            if (digger != null)
            {
                digger.transform.rotation = Quaternion.LookRotation(Flat(grave - digger.transform.position));
                digger.gesture = DiverPuppet.Gesture.Dig;
            }
            yield return new WaitForSeconds(2f);
            Hud.Toast("“I heard the strokes of the pickaxe, which sparkled when it hit upon some flint lost at the bottom of the waters.”", 6f);
            for (int i = 0; i < 4; i++)
            {
                yield return new WaitForSeconds(1.3f);
                if (m_Sparks != null) { m_Sparks.transform.position = grave + Vector3.up * 0.1f + Random.insideUnitSphere * 0.15f; m_Sparks.Emit(18); }
                yield return new WaitForSeconds(1.3f);
            }
            if (digger != null) digger.gesture = DiverPuppet.Gesture.Idle;
            // the bearers lower the body
            Hud.Toast("“The body, enveloped in a tissue of white linen, was lowered into the damp grave.”", 6f);
            if (bearers != null) foreach (var b in bearers) if (b != null) b.gesture = DiverPuppet.Gesture.Lower;
            if (shroud != null)
            {
                Vector3 from = shroud.position, to = grave + Vector3.down * 0.25f;
                for (float t = 0; t < 1f; t += Time.deltaTime / 3.5f) { shroud.position = Vector3.Lerp(from, to, Mathf.SmoothStep(0, 1, t)); yield return null; }
                shroud.position = to;
            }
            yield return new WaitForSeconds(0.8f);
            // the prayer
            if (nemoPuppet != null) nemoPuppet.gesture = DiverPuppet.Gesture.KneelCross;
            foreach (var d in Party()) if (d != nemoPuppet) d.gesture = DiverPuppet.Gesture.Kneel;
            Hud.Toast("“Captain Nemo, with his arms crossed on his breast, and all the friends of him who had loved them, knelt in prayer.”  (K: kneel)", 8f);
            yield return new WaitForSeconds(9f);
            // the grave filled in, a slight mound
            foreach (var d in Party()) d.gesture = DiverPuppet.Gesture.Idle;
            if (shroud != null) shroud.gameObject.SetActive(false);
            if (mound != null) mound.SetActive(true);
            Hud.Toast("“The grave was then filled in with the rubbish taken from the ground, which formed a slight mound.”", 5f);
            yield return new WaitForSeconds(4f);
            // the last adieu
            foreach (var d in Party()) d.gesture = DiverPuppet.Gesture.KneelAdieu;
            Hud.Toast("“Approaching the grave, they knelt again, and all extended their hands in sign of a last adieu.”", 7f);
            yield return new WaitForSeconds(7f);
            foreach (var d in Party()) d.gesture = DiverPuppet.Gesture.Idle;
            StartCoroutine(Letterbox(false));
            Hud.Toast("“Then the funeral procession returned to the Nautilus, passing under the arches of the forest.”", 7f);
            yield return new WaitForSeconds(8f);
            SceneFlow.Load(SceneFlow.Nautilus);
        }

        System.Collections.Generic.IEnumerable<DiverPuppet> Party()
        {
            var n = nemo != null ? nemo.GetComponent<DiverPuppet>() : null;
            if (n != null) yield return n;
            if (digger != null) yield return digger;
            if (bearers != null) foreach (var b in bearers) if (b != null) yield return b;
        }

        static Vector3 Flat(Vector3 v) { v.y = 0f; return v.sqrMagnitude > 1e-4f ? v : Vector3.forward; }

        void BuildSparks()
        {
            var go = new GameObject("Pickaxe sparks");
            go.transform.SetParent(transform, false);
            m_Sparks = go.AddComponent<ParticleSystem>();
            m_Sparks.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = m_Sparks.main;
            main.playOnAwake = false; main.loop = false; main.startLifetime = new ParticleSystem.MinMaxCurve(0.15f, 0.45f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.8f, 2.4f); main.startSize = new ParticleSystem.MinMaxCurve(0.015f, 0.04f);
            main.startColor = new Color(1f, 0.75f, 0.35f); main.gravityModifier = 0.3f; main.simulationSpace = ParticleSystemSimulationSpace.World;
            var em = m_Sparks.emission; em.enabled = false;
            var sh = m_Sparks.shape; sh.shapeType = ParticleSystemShapeType.Hemisphere; sh.radius = 0.05f;
            var r = go.GetComponent<ParticleSystemRenderer>();
            var shader = Shader.Find("Universal Render Pipeline/Particles/Unlit");
            if (shader != null)
            {
                var m = new Material(shader);
                m.SetColor("_BaseColor", new Color(3f, 1.8f, 0.6f, 1f));
                m.SetFloat("_Surface", 1f); m.SetFloat("_Blend", 2f);
                m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.One); m.SetFloat("_ZWrite", 0f);
                m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.renderQueue = 3000;
                r.sharedMaterial = m;
            }
        }

        void BuildLetterbox()
        {
            var canvas = VerneUI.CreateCanvas("Burial letterbox", 4, transform);
            canvas.GetComponent<GraphicRaycaster>().enabled = false;
            m_Top = Bar(canvas.transform, true); m_Bottom = Bar(canvas.transform, false);
        }

        static RectTransform Bar(Transform parent, bool top)
        {
            var img = VerneUI.Panel(parent, top ? "Top bar" : "Bottom bar", Color.black);
            img.raycastTarget = false;
            var r = img.rectTransform;
            r.anchorMin = new Vector2(0, top ? 1 : 0); r.anchorMax = new Vector2(1, top ? 1 : 0); r.pivot = new Vector2(0.5f, top ? 1 : 0);
            r.sizeDelta = new Vector2(0, 0);
            return r;
        }

        IEnumerator Letterbox(bool on)
        {
            float target = on ? 0.11f : 0f;   // ~2.39:1 on 16:9
            float start = m_Top != null ? m_Top.sizeDelta.y : 0f;
            for (float t = 0; t < 1f; t += Time.unscaledDeltaTime / 0.6f)
            {
                float h = Mathf.Lerp(start, target * 1080f, Mathf.SmoothStep(0, 1, t));
                if (m_Top != null) m_Top.sizeDelta = new Vector2(0, h);
                if (m_Bottom != null) m_Bottom.sizeDelta = new Vector2(0, h);
                yield return null;
            }
        }
    }
}
