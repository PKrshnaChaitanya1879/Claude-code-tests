using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Sets the Nautilus up for the excursion that is next (Chapter.Excursion): Nemo's note on the
    /// writing-table, the depth outside the sea door, and where that door leads.
    /// </summary>
    [DefaultExecutionOrder(-50)]
    public class ChapterAboard : MonoBehaviour
    {
        public Readable note;
        public FloodingCell cell;
        public SceneExit seaDoor;

        void Awake()
        {
            bool night = Chapter.Excursion >= 2;
            if (note != null)
            {
                if (night)
                {
                    note.title = "Midnight";
                    note.body = "“You have hitherto only visited the submarine depths by daylight, under the brightness of the sun. Would it suit you to see them in the darkness of the night? I warn you, the way will be tiring. We shall have far to walk, and must climb a mountain. The roads are not well kept.”\n\n“Come then, sir, we will put on our diving-dresses.”";
                    note.signature = "Captain Nemo, Part II, Chapter IX";
                }
                else
                {
                    note.title = "A note of invitation";
                    note.body = "Captain Nemo invites Professor Aronnax to a hunting-party, which will take place to-morrow morning in the forests of the island of Crespo. He hopes that nothing will prevent the Professor from being present, and he will with pleasure see him joined by his companions.";
                    note.signature = "Captain Nemo, Commander of the Nautilus";
                }
            }
            if (cell != null) cell.outsideDepth = Chapter.OutsideDepth;
            if (seaDoor != null) seaDoor.scene = Chapter.NextMissionScene;
        }
    }
}
