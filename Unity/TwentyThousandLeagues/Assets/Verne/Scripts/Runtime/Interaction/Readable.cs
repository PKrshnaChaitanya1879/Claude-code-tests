using System;
using UnityEngine;
using UnityEngine.Events;

namespace Verne
{
    /// <summary>A note, a book or a plaque: shows its text on the reading card.</summary>
    public class Readable : Interactable
    {
        [TextArea(3, 12)] public string title;
        [TextArea(4, 20)] public string body;
        public string signature;
        [Tooltip("A painting or object shown large beside the text (GUM: see the painting next to its words).")]
        public Texture image;
        public UnityEvent onRead = new UnityEvent();

        protected override void Awake() { base.Awake(); if (verb == "Use") verb = "Read"; }
        protected override void OnBegin(Interactor who) { ReadingCard.Show(title, body, signature, image); onRead.Invoke(); base.OnBegin(who); }
    }
}
