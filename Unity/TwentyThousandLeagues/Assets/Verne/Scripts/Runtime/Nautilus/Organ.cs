using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Captain Nemo's organ (I.X; plate im083). Sitting down at it plays the opening of Bach's
    /// Toccata in D minor (public domain), synthesised as a pipe organ (Source/audio/organ_bwv565.py).
    /// Using it again lifts the hands from the keys.
    /// </summary>
    public class Organ : Interactable
    {
        public AudioClip piece;
        AudioSource m_Src;

        protected override void Awake()
        {
            base.Awake();
            verb = "Play"; noun = "the organ";
            if (piece == null) piece = Resources.Load<AudioClip>("VerneAudio/music/organ_bwv565");
            m_Src = gameObject.AddComponent<AudioSource>();
            m_Src.clip = piece; m_Src.playOnAwake = false; m_Src.loop = false;
            m_Src.spatialBlend = 0.6f; m_Src.minDistance = 4f; m_Src.maxDistance = 40f; m_Src.volume = 0.9f;
        }

        public override string Prompt => m_Src != null && m_Src.isPlaying ? "Lift your hands from the keys" : "Play the organ";

        protected override void OnBegin(Interactor who)
        {
            if (m_Src == null || m_Src.clip == null) { Hud.Toast("The organ is silent."); return; }
            if (m_Src.isPlaying) { m_Src.Stop(); return; }
            m_Src.Play();
            Hud.Toast("J. S. Bach, Toccata in D minor. The organ fills the saloon.", 4f);
            base.OnBegin(who);
        }
    }
}
