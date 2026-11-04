using UnityEngine;

namespace Verne
{
    /// <summary>
    /// The eruption as it was filmed at West Mata (GUM 4 Nov): a cloud of milky-yellow gas and steam billowing up from the
    /// crater, lit from below by the lava; the light in the crater flickering with the fountains; and every so often a steam
    /// explosion, where seawater flashes into steam against the lava: a flash, a blast of steam, and rock thrown out.
    /// "The submarine crater threw up lava, but no flames" (II.IX).
    /// </summary>
    public class VolcanoEruption : MonoBehaviour
    {
        public ParticleSystem plume, blast, fountain;
        public Light crater;
        public Light[] cloudLights;
        public float burstMin = 8f, burstMax = 18f;
        float m_Base, m_Next, m_Flash;
        float[] m_CloudBase;
        AudioClip m_Blast;

        void Start()
        {
            if (crater != null) m_Base = crater.intensity;
            if (cloudLights != null) { m_CloudBase = new float[cloudLights.Length]; for (int i = 0; i < cloudLights.Length; i++) m_CloudBase[i] = cloudLights[i] != null ? cloudLights[i].intensity : 0f; }
            m_Next = Time.time + Random.Range(2f, burstMax);
        }

        void Update()
        {
            float t = Time.time;
            if (t >= m_Next)
            {
                m_Next = t + Random.Range(burstMin, burstMax);
                m_Flash = 1f;
                if (blast != null) blast.Emit(Random.Range(18, 32));
                if (fountain != null) fountain.Emit(Random.Range(90, 160));   // the blast throws a sheaf of molten rock with it
                if (m_Blast == null) m_Blast = Resources.Load<AudioClip>("VerneAudio/sfx/steam_blast");
                if (m_Blast != null) VerneAudio.PlayAt(m_Blast, transform.position, 0.85f, 0.1f, 0.35f);   // heard from afar: water carries the low thump
            }
            m_Flash = Mathf.MoveTowards(m_Flash, 0f, Time.deltaTime / 1.6f);
            // the fountains: an unsteady, breathing light, never a steady lamp
            float flicker = 0.8f + 0.2f * Mathf.PerlinNoise(t * 1.7f, 0.3f) + 0.12f * Mathf.PerlinNoise(t * 6f, 4.1f);
            float flash = m_Flash * m_Flash * 2.5f;
            if (crater != null) crater.intensity = m_Base * (flicker + flash);
            if (cloudLights != null)
                for (int i = 0; i < cloudLights.Length; i++)
                    if (cloudLights[i] != null) cloudLights[i].intensity = m_CloudBase[i] * (0.85f + 0.15f * Mathf.PerlinNoise(t * 0.6f + i * 3f, 1.7f) + flash * 0.8f);
        }
    }
}
