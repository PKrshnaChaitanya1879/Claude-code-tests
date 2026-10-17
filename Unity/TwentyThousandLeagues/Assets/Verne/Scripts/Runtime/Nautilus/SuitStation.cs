using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Where the diving dress hangs (I.XV: "A dozen diving apparatuses hung from the partition").
    /// M1 version: one interaction dresses the player in the right order and switches to the heavy
    /// "suited" gait. M2 replaces it with the full suit-up: dress, reservoir, lamp or stick, helmet.
    /// </summary>
    public class SuitStation : Interactable
    {
        [TextArea] public string[] steps =
        {
            "The india-rubber dress, without seam: trousers and waistcoat.",
            "The Rouquayrol reservoir, fixed on the back by braces, like a soldier's knapsack.",
            "The Ruhmkorff lamp, hanging from the belt.",
            "The copper helmet, screwed on to the collar. The apparatus began to act; I could breathe with ease.",
        };
        int m_Step;

        protected override void Awake() { base.Awake(); verb = "Put on"; noun = "the diving dress"; }

        public override string Prompt => m_Step < steps.Length ? (m_Step == 0 ? "Put on the diving dress" : "Continue dressing") : "Dressed";

        protected override void OnBegin(Interactor who)
        {
            if (m_Step >= steps.Length) return;
            Hud.Toast(steps[m_Step], 4.5f);
            m_Step++;
            if (m_Step >= steps.Length)
            {
                var p = PlayerMotor.Instance;
                if (p != null) p.SetMode(MoveMode.Suited);
                interactable = false;
            }
            base.OnBegin(who);
        }
    }
}
