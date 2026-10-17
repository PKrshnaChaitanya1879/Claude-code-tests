using UnityEngine;

namespace Verne
{
    /// <summary>
    /// The robing-room bench where the visitors are dressed (I.XV: "A dozen diving apparatuses hung from
    /// the partition"). Each use puts on the next piece in the book's order, and that piece disappears
    /// from the bench (the Blender kit_* objects):
    ///   Excursion I  (Crespo):   dress → Rouquayrol reservoir → Ruhmkorff lamp → air-gun → copper helmet
    ///   Excursion II (Atlantis): dress → reservoir (no lamps: "They will be useless") → iron-pointed stick → helmet
    /// Once the helmet is screwed on the player moves in the heavy "suited" gait.
    /// </summary>
    public class SuitStation : Interactable
    {
        public struct Step { public string piece, kit, line; }

        [Tooltip("The kit objects on the bench, found by name under this transform's scene (kit_dress, kit_reservoir ...).")]
        public GameObject kitDress, kitReservoir, kitLamp, kitGun, kitStick, kitHelmet;
        public AudioClip donClip;

        int m_Step;
        Step[] m_Steps;

        public static bool Dressed { get; private set; }
        public static bool HasLamp { get; private set; }

        static readonly Step[] s_Crespo =
        {
            new Step { piece = "the india-rubber dress", kit = "dress", line = "Heavy and impervious clothes, made of india-rubber without seam: trousers and waistcoat, the boots weighted with heavy leaden soles." },
            new Step { piece = "the Rouquayrol reservoir", kit = "reservoir", line = "The reservoir of thick iron plates, fixed on the back by braces, like a soldier's knapsack." },
            new Step { piece = "the Ruhmkorff lamp", kit = "lamp", line = "The Ruhmkorff lamp hung from my belt; it is lit by turning a screw." },
            new Step { piece = "the air-gun", kit = "gun", line = "An air-gun: the butt, hollow in the centre, served as a reservoir for compressed air." },
            new Step { piece = "the copper helmet", kit = "helmet", line = "The copper helmet was screwed upon the collar. The apparatus began to act, and I could breathe with ease." },
        };
        static readonly Step[] s_Atlantis =
        {
            new Step { piece = "the diving-dress", kit = "dress", line = "In a few moments we had put on our diving-dresses." },
            new Step { piece = "the reservoir", kit = "reservoir", line = "They placed on our backs the reservoirs, abundantly filled with air, but no electric lamps were prepared. \"They will be useless.\"" },
            new Step { piece = "the iron-pointed stick", kit = "stick", line = "I felt them put an iron-pointed stick into my hand." },
            new Step { piece = "the copper helmet", kit = "helmet", line = "My head disappeared in its metal case. I finished harnessing myself." },
        };

        protected override void Awake()
        {
            base.Awake();
            verb = "Put on";
            if (donClip == null) donClip = Resources.Load<AudioClip>("VerneAudio/sfx/button_click");
            Dressed = false; HasLamp = false;
        }

        void Start()
        {
            m_Steps = Chapter.Excursion >= 2 ? s_Atlantis : s_Crespo;
            m_Step = 0;
            foreach (var k in new[] { kitDress, kitReservoir, kitLamp, kitGun, kitStick, kitHelmet }) if (k != null) k.SetActive(true);
        }

        public override string Prompt => m_Steps == null ? "Put on the diving dress" : m_Step < m_Steps.Length ? "Put on " + m_Steps[m_Step].piece : "Dressed";

        GameObject Kit(string k)
        {
            switch (k)
            {
                case "dress": return kitDress;
                case "reservoir": return kitReservoir;
                case "lamp": return kitLamp;
                case "gun": return kitGun;
                case "stick": return kitStick;
                case "helmet": return kitHelmet;
            }
            return null;
        }

        protected override void OnBegin(Interactor who)
        {
            if (m_Steps == null || m_Step >= m_Steps.Length) return;
            var st = m_Steps[m_Step];
            Hud.Toast(st.line, 5f);
            var kit = Kit(st.kit);
            if (kit != null) kit.SetActive(false);
            if (st.kit == "lamp") HasLamp = true;
            PlayOneShot(donClip, 0.5f);
            m_Step++;
            var p = PlayerMotor.Instance;
            if (m_Step == 1 && p != null) p.SetMode(MoveMode.Suited);   // leaden soles from the first piece: "impossible for me to take a step" quickly
            if (m_Step >= m_Steps.Length)
            {
                Dressed = true;
                interactable = false;
            }
            base.OnBegin(who);
        }
    }
}
