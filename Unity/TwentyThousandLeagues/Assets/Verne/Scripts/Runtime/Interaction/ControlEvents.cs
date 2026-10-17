using System;
using UnityEngine;
using UnityEngine.Events;

namespace Verne
{
    [Serializable] public class FloatEvent : UnityEvent<float> { }
    [Serializable] public class IntEvent : UnityEvent<int> { }
}
