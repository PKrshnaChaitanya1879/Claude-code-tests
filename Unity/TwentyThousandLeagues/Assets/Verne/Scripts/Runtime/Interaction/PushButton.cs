using System;
using UnityEngine;
using UnityEngine.Events;

namespace Verne
{
    /// <summary>A push button or knob: travels in, clicks, springs back.</summary>
    public class PushButton : Interactable
    {
        public Transform cap;
        public float travel = 0.008f;
        public AudioClip click;
        float m_Press;
        Vector3 m_Rest;

        protected override void Awake() { base.Awake(); if (cap == null) cap = transform; m_Rest = cap.localPosition; }
        protected override void OnBegin(Interactor who) { m_Press = 1f; PlayOneShot(click, 0.7f); base.OnBegin(who); }
        void Update()
        {
            m_Press = Mathf.MoveTowards(m_Press, IsHeld ? 1f : 0f, Time.deltaTime * 8f);
            cap.localPosition = m_Rest - Vector3.forward * (travel * m_Press);
        }
    }
}
