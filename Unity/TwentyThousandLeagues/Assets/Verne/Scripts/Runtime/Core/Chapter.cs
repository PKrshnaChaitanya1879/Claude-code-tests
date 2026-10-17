namespace Verne
{
    /// <summary>
    /// Where the player is in Chapter One. Excursion 1 = the forest of Crespo and the coral cemetery
    /// (Part I, ch. XIV–XVII, XXIV); excursion 2 = the night walk to Atlantis (Part II, ch. IX).
    /// Boarding the Nautilus after the first excursion prepares the second.
    /// </summary>
    public static class Chapter
    {
        public static int Excursion = 1;

        /// <summary>Called by SceneFlow when a scene is loaded.</summary>
        public static void OnSceneLoading(string scene)
        {
            if (scene == SceneFlow.Mission1) Excursion = 2;          // back aboard, the next invitation waits
            else if (scene == SceneFlow.Mission2) Excursion = 2;     // the night walk can be repeated from aboard
        }

        public static string NextMissionScene => Excursion >= 2 ? SceneFlow.Mission2 : SceneFlow.Mission1;
        /// <summary>Depth of the sea door, metres: five fathoms at Crespo (I.XV), 150 fathoms off Atlantis (II.IX).</summary>
        public static float OutsideDepth => Excursion >= 2 ? 274f : 9f;
    }
}
