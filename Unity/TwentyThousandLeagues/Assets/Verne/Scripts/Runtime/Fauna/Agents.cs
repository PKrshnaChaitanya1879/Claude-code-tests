using UnityEngine;
using UnityEngine.AI;

namespace Verne
{
    /// <summary>
    /// (M4) NavMesh walking for the divers: a heavy, deliberate agent (the dress weighs on them; "I am not superman"
    /// goes for them too), placed on the scene's baked NavMesh. Returns null when there is no NavMesh within 2 m,
    /// so callers keep their straight-leg fallback.
    /// </summary>
    public static class Agents
    {
        static int s_Priority = 40;

        public static NavMeshAgent Attach(GameObject go, float speed)
        {
            if (!NavMesh.SamplePosition(go.transform.position, out var hit, 2f, NavMesh.AllAreas)) return null;
            var a = go.GetComponent<NavMeshAgent>();
            if (a == null) a = go.AddComponent<NavMeshAgent>();
            a.radius = 0.35f; a.height = 1.9f; a.baseOffset = 0f;
            a.speed = speed; a.acceleration = 1.2f; a.angularSpeed = 100f;
            a.stoppingDistance = 0.3f; a.autoBraking = true;
            a.obstacleAvoidanceType = ObstacleAvoidanceType.MedQualityObstacleAvoidance;
            a.avoidancePriority = s_Priority = s_Priority >= 60 ? 40 : s_Priority + 1;
            if (!a.Warp(hit.position)) { Object.Destroy(a); return null; }
            return a;
        }
    }
}
