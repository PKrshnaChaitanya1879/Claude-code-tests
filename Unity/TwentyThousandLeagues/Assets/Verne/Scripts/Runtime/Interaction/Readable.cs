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
        public UnityEvent onRead = new UnityEvent();

        protected override void Awake() { base.Awake(); if (verb == "Use") verb = "Read"; }
        protected override void OnBegin(Interactor who) { ReadingCard.Show(title, body, signature); onRead.Invoke(); base.OnBegin(who); }
    }
}
