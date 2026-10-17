using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Events;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;
using static Verne.EditorTools.Greybox;

namespace Verne.EditorTools
{
    /// <summary>
    /// Builds the four scenes. M1 = playable greybox at the book's true dimensions (Design Bible §2),
    /// with working controls; later milestones swap the greybox for Blender models.
    /// Nautilus axes: +Z toward the bow, +X starboard, floor of the main deck at y = 0.
    /// </summary>
    public static class SceneBuilders
    {
        public static readonly List<string> Notes = new List<string>();
        static string ScenePath(string n) => VerneBootstrap.Generated + "/Scenes/" + n + ".unity";

        // ------------------------------------------------------------------ helpers
        static Scene NewScene(string name)
        {
            var s = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            s.name = name;
            return s;
        }

        static void Save(Scene s, string name)
        {
            EditorSceneManager.SaveScene(s, ScenePath(name));
            Notes.Add($"saved {ScenePath(name)}");
        }

        static Volume GlobalVolume(string grade)
        {
            var go = new GameObject("Grade (" + grade + ")");
            var v = go.AddComponent<Volume>();
            v.isGlobal = true;
            v.priority = 0;
            v.sharedProfile = ProjectSetup.LoadGrade(grade);
            return v;
        }

        static Light Sun(string name, Vector3 euler, Color color, float intensity, bool shadows = true)
        {
            var go = new GameObject(name);
            go.transform.rotation = Quaternion.Euler(euler);
            var l = go.AddComponent<Light>();
            l.type = LightType.Directional;
            l.color = color;
            l.intensity = intensity;
            l.shadows = shadows ? LightShadows.Soft : LightShadows.None;
            l.shadowStrength = 0.9f;
            RenderSettings.sun = l;
            return l;
        }

        static void Ambient(Color sky, Color equator, Color ground)
        {
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = sky;
            RenderSettings.ambientEquatorColor = equator;
            RenderSettings.ambientGroundColor = ground;
            RenderSettings.skybox = null;
            RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom;
        }

        static void Fog(bool on, Color color, float density)
        {
            RenderSettings.fog = on;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogColor = color;
            RenderSettings.fogDensity = density;
        }

        static GameObject Spawn(Vector3 pos, float yaw, MoveMode mode, float far = 400f)
        {
            var go = new GameObject("Player Spawn");
            go.transform.SetPositionAndRotation(pos, Quaternion.Euler(0, yaw, 0));
            var sp = go.AddComponent<PlayerSpawn>();
            sp.mode = mode;
            sp.farClip = far;
            return go;
        }

        static Camera PreviewCamera(Vector3 pos, Vector3 euler, Color bg)
        {
            var go = new GameObject("Main Camera");
            go.tag = "MainCamera";
            go.transform.SetPositionAndRotation(pos, Quaternion.Euler(euler));
            var c = go.AddComponent<Camera>();
            c.clearFlags = CameraClearFlags.SolidColor;
            c.backgroundColor = bg;
            c.nearClipPlane = 0.05f;
            c.farClipPlane = 400f;
            c.fieldOfView = 55f;
            var d = c.GetUniversalAdditionalCameraData();
            d.renderPostProcessing = true;
            go.AddComponent<AudioListener>();
            return c;
        }

        static T Wire<T>(GameObject go) where T : Component => go.AddComponent<T>();

        // ------------------------------------------------------------------ Title
        public static void Title()
        {
            var s = NewScene("Title");
            Ambient(new Color(0.10f, 0.22f, 0.26f), new Color(0.04f, 0.09f, 0.11f), new Color(0.01f, 0.02f, 0.03f));
            Fog(true, new Color(0.05f, 0.16f, 0.19f), 0.028f);
            Sun("Sun (refracted)", new Vector3(62, 25, 0), new Color(0.75f, 0.92f, 0.95f), 1.4f);
            var root = new GameObject("Seabed").transform;
            Seabed(root, 120f, 2f, 3.0f, 0.03f, "Sand", 7);
            Rocks(root, 26, 50f, 11, "Rock");
            KelpStand(root, new Vector3(-6, 0, 24), 18, 7f, 13);
            var hero = AssetDatabase.LoadAssetAtPath<GameObject>(NautilusExterior.PrefabPath);
            if (hero != null)
            {
                var n = (GameObject)PrefabUtility.InstantiatePrefab(hero, root);
                n.transform.SetPositionAndRotation(new Vector3(14f, 6.5f, 46f), Quaternion.Euler(0f, -72f, 0f));
            }
            var cam = PreviewCamera(new Vector3(0, 2.2f, -4), new Vector3(-8, 14, 0), new Color(0.05f, 0.16f, 0.19f));
            var t = new GameObject("Title Screen").AddComponent<TitleScreen>();
            t.driftCamera = cam.transform;
            GlobalVolume("Title");
            Save(s, "Title");
        }

        // ------------------------------------------------------------------ Nautilus
        public static void Nautilus()
        {
            var s = NewScene("Nautilus");
            Ambient(new Color(0.28f, 0.25f, 0.21f), new Color(0.16f, 0.14f, 0.12f), new Color(0.06f, 0.05f, 0.05f));
            Fog(false, Color.black, 0f);
            var ship = new GameObject("Nautilus (greybox, true dimensions)").transform;

            const float X0 = -3.2f, X1 = 3.2f;   // 6.4 m inner width (beam 8 m minus double hull)
            const float CX = -2.0f;                // aft corridor wall (corridor on the port side)

            // forward rooms, bow to midships (Design Bible §2): Aronnax 2.5 m, Nemo 5, saloon 10, library 5, dining 5
            var aronnax = Room(ship, "Aronnax's room", X0, X1, 25f, 27.5f, 2.6f, "Oak", "Carpet", "Plaster", "carpet");
            var nemo = Room(ship, "Nemo's room", X0, X1, 20f, 25f, 2.8f, "IronPaint", "Iron", "Plaster", "iron");
            var saloon = Room(ship, "Saloon", X0, X1, 10f, 20f, 5f, "Tapestry", "Carpet", "LuminousCeiling", "carpet");
            var library = Room(ship, "Library", X0, X1, 5f, 10f, 3.2f, "Ebony", "Carpet", "Ceiling", "carpet");
            var dining = Room(ship, "Dining room", X0, X1, 0f, 5f, 3.2f, "Oak", "Oak", "LuminousCeiling", "wood");
            var hall = Room(ship, "Central staircase", X0, X1, -2f, 0f, 3.2f, "IronPaint", "Iron", "Ceiling", "iron");

            // bow end (air reservoir behind it) and the cross partitions with their doors (x = 0)
            Wall("Bow partition", ship, new Vector2(X0, 27.5f), new Vector2(X1, 27.5f), 0, 2.6f, "IronPaint");
            Wall("Aronnax | Nemo", ship, new Vector2(X0, 25f), new Vector2(X1, 25f), 0, 2.8f, "Oak", new Opening(3.2f, 0.9f, 2.1f));
            Wall("Nemo | Saloon (water-tight)", ship, new Vector2(X0, 20f), new Vector2(X1, 20f), 0, 5f, "IronPaint", new Opening(0.85f, 0.9f, 2.1f)); // beside the organ
            Wall("Saloon | Library", ship, new Vector2(X0, 10f), new Vector2(X1, 10f), 0, 5f, "Tapestry", new Opening(3.2f, 1.4f, 2.4f));
            Wall("Library | Dining (water-tight)", ship, new Vector2(X0, 5f), new Vector2(X1, 5f), 0, 3.2f, "Ebony", new Opening(3.2f, 1.6f, 2.4f));
            Wall("Dining | Staircase", ship, new Vector2(X0, 0f), new Vector2(X1, 0f), 0, 3.2f, "Oak", new Opening(3.2f, 1.2f, 2.2f));

            // side walls: saloon has its two crystal windows (I.XIII: "two oblong openings")
            SideWalls(ship, X0, X1, 20f, 27.5f, 2.8f, "IronPaint");
            Wall("Saloon port", ship, new Vector2(X0, 10f), new Vector2(X0, 20f), 0, 5f, "Tapestry", new Opening(5f, 4.2f, 2.0f, 1.0f));
            Wall("Saloon starboard", ship, new Vector2(X1, 10f), new Vector2(X1, 20f), 0, 5f, "Tapestry", new Opening(5f, 4.2f, 2.0f, 1.0f));
            SideWalls(ship, X0, X1, -2f, 10f, 3.2f, "IronPaint");

            // aft: corridor on the port side, rooms to starboard (Ned & Conseil, kitchen, bath, crew, robing room)
            Room(ship, "Aft corridor", X0, CX, -15f, -2f, 2.4f, null, "Iron", "Ceiling", "iron");
            Wall("Hall | aft", ship, new Vector2(X0, -2f), new Vector2(X1, -2f), 0, 3.2f, "IronPaint", new Opening(0.6f, 1.0f, 2.1f));
            Wall("Aft corridor port (hull)", ship, new Vector2(X0, -15f), new Vector2(X0, -2f), 0, 2.4f, "Iron");
            var aft = new (string name, float z0, float z1, string wall, string floor, string surf, bool locked)[]
            {
                ("Cabin of Ned and Conseil", -4f, -2f, "Oak", "Oak", "wood", false),
                ("Kitchen", -7f, -4f, "IronPaint", "Iron", "iron", false),
                ("Bathroom", -8.5f, -7f, "Marble", "Marble", "marble", false),
                ("Crew's quarters", -12.5f, -8.5f, "IronPaint", "Iron", "iron", true),
                ("Robing room", -15f, -12.5f, "IronPaint", "Iron", "iron", false),
            };
            Transform robing = null;
            foreach (var r in aft)
            {
                var t = Room(ship, r.name, CX, X1, r.z0, r.z1, 2.4f, r.wall, r.floor, "Ceiling", r.surf);
                Wall(r.name + " starboard", ship, new Vector2(X1, r.z0), new Vector2(X1, r.z1), 0, 2.4f, "Iron");
                if (r.name != "Robing room") Wall(r.name + " aft", ship, new Vector2(CX, r.z0), new Vector2(X1, r.z0), 0, 2.4f, r.wall); // the robing room's aft wall is the cell's inner-door wall
                // door to the corridor, as a real Door with a leaf
                float mid = (r.z0 + r.z1) * 0.5f;
                Wall(r.name + " corridor wall", ship, new Vector2(CX, r.z0), new Vector2(CX, r.z1), 0, 2.4f, r.wall, new Opening(mid - r.z0, 0.85f, 2.05f));
                var door = HingedDoor(t, r.name + " door", new Vector3(CX, 0, mid - 0.425f), 0f, 0.85f, 2.05f, "Oak");
                if (r.locked) { door.locked = true; door.lockedMessage = "The door was shut. (I.XI)"; }
                if (r.name == "Robing room") robing = t;
            }
            Wall("Corridor end", ship, new Vector2(X0, -15f), new Vector2(CX, -15f), 0, 2.4f, "Iron");

            // ---- art for both blocks (Blender, Source/blender/nautilus_interior_fore.py and _aft.py) or greybox furniture
            bool art = NautilusInterior.Place(ship) != null;
            Art = art;
            s_AftArt = NautilusInterior.Place(ship, NautilusInterior.Aft);

            // the flooding cell, aft of the robing room
            BuildFloodingCell(ship, robing, CX, -17.5f, -15f);

            FurnishAronnax(aronnax);
            FurnishNemo(nemo);
            FurnishSaloon(saloon, X0, X1);
            FurnishLibrary(library, X0, X1);
            FurnishDining(dining);
            if (art) HideGreyboxWhereArt(ship, 0f, 27.6f);
            if (s_AftArt != null) HideGreyboxWhereArt(ship, -17.6f, -0.01f);
            else Notes.Add("Aft block FBX missing: the aft rooms stay greybox.");
            var chapter = ship.gameObject.AddComponent<ChapterAboard>();
            chapter.note = s_Note; chapter.cell = s_Cell; chapter.seaDoor = s_SeaDoor;
            Ladder(hall, new Vector3(2.4f, 0, -1.6f), 3.2f);

            Spawn(new Vector3(0.8f, 0.05f, 26.2f), 180f, MoveMode.Air, 120f);
            GlobalVolume("Nautilus");
            Save(s, "Nautilus");
        }

        static bool Art;
        static Transform s_AftArt;
        static Readable s_Note;
        static FloodingCell s_Cell;
        static SceneExit s_SeaDoor;

        /// <summary>The greybox boxes stay as exact, invisible colliders where the Blender rooms are shown.</summary>
        static void HideGreyboxWhereArt(Transform ship, float z0, float z1)
        {
            int n = 0;
            foreach (var r in ship.GetComponentsInChildren<MeshRenderer>(true))
            {
                if (r.GetComponentInParent<NautilusArtMarker>() != null) continue;
                if (r.GetComponentInParent<Interactable>() != null || r.GetComponentInParent<Gauge>() != null) continue;
                string nm = r.name;
                if (nm.StartsWith("Crystal") || nm.StartsWith("Iron panel") || nm.StartsWith("Sea beyond") || nm.Contains("Lever") || nm == "needle" || nm == "Water surface") continue;
                float z = r.bounds.center.z;
                if (z < z0 - 0.1f || z > z1) continue;
                r.enabled = false; n++;
            }
            Notes.Add($"{n} greybox pieces hidden in the forward block; their colliders remain.");
        }

        static Transform Room(Transform ship, string name, float x0, float x1, float z0, float z1, float h, string wallMat, string floorMat, string ceilMat, string surface)
        {
            var t = new GameObject(name).transform;
            t.SetParent(ship, false);
            Slabs(name, t, x0, x1, z0, z1, 0f, h, floorMat, ceilMat, surface);
            if (ceilMat == "LuminousCeiling" || ceilMat == "Ceiling")
            {
                // one soft, unshadowed fill per room, the electric light "uniform and unintermittent"
                var area = (x1 - x0) * (z1 - z0);
                PointLight(name + " light", t, new Vector3((x0 + x1) * 0.5f, h - 0.25f, (z0 + z1) * 0.5f), new Color(1f, 0.93f, 0.82f), ceilMat == "LuminousCeiling" ? 2.2f : 1.4f, Mathf.Sqrt(area) * 1.6f + h);
            }
            return t;
        }

        static void SideWalls(Transform ship, float x0, float x1, float z0, float z1, float h, string mat)
        {
            Wall($"Port hull {z0}..{z1}", ship, new Vector2(x0, z0), new Vector2(x0, z1), 0, h, mat);
            Wall($"Starboard hull {z0}..{z1}", ship, new Vector2(x1, z0), new Vector2(x1, z1), 0, h, mat);
        }

        static Door HingedDoor(Transform parent, string name, Vector3 hinge, float yaw, float width, float height, string mat)
        {
            var pivot = new GameObject(name).transform;
            pivot.SetParent(parent.parent, false);
            pivot.localPosition = hinge;
            pivot.localRotation = Quaternion.Euler(0, yaw, 0);
            Box(name + " leaf", pivot, new Vector3(0.02f, height * 0.5f, width * 0.5f), new Vector3(0.05f, height - 0.02f, width - 0.03f), mat, 1.6f, true, null, false);
            var d = pivot.gameObject.AddComponent<Door>();
            d.leaf = pivot;
            d.kind = Door.Kind.Hinge;
            d.openAngle = -100f;
            d.noun = "";
            d.reach = 2.4f;
            pivot.gameObject.layer = ProjectSetup.InteractableLayer;
            return d;
        }

        static void Ladder(Transform parent, Vector3 foot, float height)
        {
            var go = new GameObject("Iron ladder to the platform");
            go.transform.SetParent(parent, false);
            go.transform.localPosition = foot;
            go.transform.localRotation = Quaternion.Euler(0, 180, 0);
            for (int i = 0; i < 2; i++) Box("rail", go.transform, new Vector3(i == 0 ? -0.22f : 0.22f, height * 0.5f, 0), new Vector3(0.04f, height, 0.04f), "Iron", 1f, false);
            for (float y = 0.3f; y < height; y += 0.3f) Box("rung", go.transform, new Vector3(0, y, 0), new Vector3(0.44f, 0.03f, 0.03f), "Iron", 1f, false);
            var trig = new GameObject("Climb volume");
            trig.transform.SetParent(go.transform, false);
            trig.transform.localPosition = new Vector3(0, height * 0.5f, 0.3f);
            var bc = trig.AddComponent<BoxCollider>();
            bc.isTrigger = true; bc.size = new Vector3(0.7f, height + 0.4f, 0.7f);
            var l = trig.AddComponent<Verne.Ladder>();
            l.length = height;
            var hatch = new GameObject("Hatch (closed)").AddComponent<Readable>();
            hatch.transform.SetParent(go.transform, false);
            hatch.transform.localPosition = new Vector3(0, height - 0.05f, 0.3f);
            hatch.gameObject.AddComponent<BoxCollider>().size = new Vector3(0.8f, 0.1f, 0.8f);
            hatch.verb = "Try"; hatch.noun = "the panel";
            hatch.title = "The panel"; hatch.body = "Shut fast. The Nautilus is under way below the surface; it will open when we rise to renew the air.";
        }

        static void FurnishAronnax(Transform room)
        {
            if (!Art)
            {
                // greybox matching the Blender room: bed to port against the bow partition, writing table, dressing-table, wardrobe
                Box("Bed", room, new Vector3(-1.78f, 0.35f, 27.0f), new Vector3(2.75f, 0.7f, 0.9f), "Linen");
                Box("Writing table", room, new Vector3(-1.25f, 0.38f, 25.4f), new Vector3(1.3f, 0.77f, 0.7f), "Ebony");
                Box("Dressing-table", room, new Vector3(1.35f, 0.4f, 25.33f), new Vector3(0.9f, 0.8f, 0.55f), "Ebony");
                Box("Wardrobe", room, new Vector3(1.2f, 1.0f, 27.17f), new Vector3(1.2f, 2.0f, 0.55f), "Ebony");
            }
            var note = Box("Captain Nemo's note", room, new Vector3(-1.1f, 0.785f, 25.35f), new Vector3(0.21f, 0.01f, 0.15f), "Linen", 1f, true, null, false);
            note.layer = ProjectSetup.InteractableLayer;
            var r = note.AddComponent<Readable>();
            s_Note = r;
            r.noun = "the note";
            r.title = "A note of invitation";
            r.body = "Captain Nemo invites Professor Aronnax to a hunting-party, which will take place to-morrow morning in the forests of the island of Crespo. He hopes that nothing will prevent the Professor from being present, and he will with pleasure see him joined by his companions.";
            r.signature = "Captain Nemo, Commander of the Nautilus";
        }

        static void FurnishNemo(Transform room)
        {
            if (!Art)
            {
                Box("Iron bedstead", room, new Vector3(-2.7f, 0.3f, 23.6f), new Vector3(0.9f, 0.6f, 2.0f), "Iron");
                Box("Table", room, new Vector3(2.75f, 0.38f, 22.5f), new Vector3(0.8f, 0.76f, 1.8f), "Oak");
                Box("Instrument board", room, new Vector3(3.18f, 1.85f, 22.5f), new Vector3(0.03f, 1.3f, 2.5f), "Oak", 1f, false);
            }
            // the instruments hang on the starboard wall (I.XI); working needles sit on the Blender dials
            // Blender dial centre (x = 22.5 - y_b, z), facing +Y_b  ->  Unity (x = 3.2 - 0.07, y = z, z = 22.5 - y_b), facing -X
            var dials = new (string name, float yb, float z, float r, float target)[]
            {
                ("Manometer (depth)", 0.2f, 1.75f, 0.2f, 1.2f), ("Electric clock (24 h)", 0.2f, 2.25f, 0.2f, 5f),
                ("Speed", -0.45f, 1.85f, 0.13f, 3f), ("Barometer", 0.85f, 1.85f, 0.14f, 6f),
            };
            foreach (var d in dials)
            {
                var pivot = new GameObject(d.name).transform;
                pivot.SetParent(room, false);
                pivot.localPosition = new Vector3(3.2f - 0.075f, d.z, 22.5f - d.yb);
                pivot.localRotation = Quaternion.Euler(0, -90, 0);              // local +Z points into the room (-X)
                var hand = new GameObject("hand").transform; hand.SetParent(pivot, false);
                Box("needle", hand, new Vector3(0, d.r * 0.32f, 0), new Vector3(0.012f, d.r * 0.95f, 0.006f), "IronPaint", 1f, false, null, false);
                var g = pivot.gameObject.AddComponent<Gauge>();
                g.needle = hand; g.axis = Vector3.forward; g.minValue = 0; g.maxValue = 10; g.target = d.target;
            }
        }

        static void FurnishSaloon(Transform room, float x0, float x1)
        {
            // organ at the forward end (plate im022), tridacna fountain in the middle, cases, divans
            if (!Art) {
            Box("Organ", room, new Vector3(0f, 1.8f, 19.4f), new Vector3(3.0f, 3.6f, 1.0f), "Ebony");
            Box("Organ pipes", room, new Vector3(0f, 3.0f, 18.95f), new Vector3(2.4f, 2.2f, 0.1f), "Brass", 1f, false);
            Cylinder("Tridacna fountain", room, new Vector3(0f, 0.45f, 15f), 0.8f, 0.9f, "Marble");
            Box("Specimen case (shells)", room, new Vector3(0f, 0.45f, 13f), new Vector3(1.6f, 0.9f, 0.9f), "Ebony");
            Box("Specimen case glass", room, new Vector3(0f, 0.95f, 13f), new Vector3(1.6f, 0.1f, 0.9f), "Glass", 1f, false);
            for (int i = 0; i < 4; i++)
            {
                float z = 11.2f + i * 2.4f;
                Box("Glass case " + i, room, new Vector3(i % 2 == 0 ? x0 + 0.45f : x1 - 0.45f, 0.6f, z), new Vector3(0.7f, 1.2f, 1.2f), "Ebony");
            }
            Box("Divan port", room, new Vector3(x0 + 0.55f, 0.25f, 15f), new Vector3(0.9f, 0.5f, 3.6f), "Leather");
            Box("Divan starboard", room, new Vector3(x1 - 0.55f, 0.25f, 15f), new Vector3(0.9f, 0.5f, 3.6f), "Leather");
            }

            // the crystal windows and their iron panels, worked by a lever (Iron Lung style)
            var panels = new GameObject("Window panels").AddComponent<SlidingPanels>();
            panels.transform.SetParent(room, false);
            var list = new List<Transform>(); var offs = new List<Vector3>();
            foreach (float x in new[] { x0, x1 })
            {
                float sign = x < 0 ? -1f : 1f;
                Box("Crystal " + (sign < 0 ? "port" : "starboard"), room, new Vector3(x + sign * 0.02f, 2.0f, 15f), new Vector3(0.06f, 2.0f, 4.2f), "Glass", 1f, true);
                var p = Box("Iron panel " + (sign < 0 ? "port" : "starboard"), panels.transform, new Vector3(x + sign * 0.14f, 2.0f, 15f), new Vector3(0.08f, 2.1f, 4.3f), "IronPaint", 1.6f, false, null, false);
                list.Add(p.transform); offs.Add(new Vector3(0, 2.2f, 0));
            }
            panels.panels = list.ToArray();
            panels.offsets = offs.ToArray();
            SeaOutside(room, panels);

            // on the brass controls plate of the aft wall, starboard of the library door
            var leverRoot = Box("Panel lever boss", room, new Vector3(1.25f, 1.27f, 10.06f), new Vector3(0.08f, 0.08f, 0.06f), "Brass", 1f, false);
            var pivot = new GameObject("Lever pivot").transform;
            pivot.SetParent(leverRoot.transform, false);
            pivot.localPosition = new Vector3(0, 0f, 0.03f);
            Box("Lever handle", pivot, new Vector3(0, 0.12f, 0.02f), new Vector3(0.035f, 0.26f, 0.035f), "Brass", 1f, true, null, false);
            pivot.gameObject.layer = ProjectSetup.InteractableLayer;
            var lever = pivot.gameObject.AddComponent<Lever>();
            lever.pivot = pivot; lever.verb = "Throw"; lever.noun = "the panel lever"; lever.notches = 2; lever.minAngle = -30; lever.maxAngle = 30;
            UnityEventTools.AddPersistentListener(lever.onValueChanged, panels.SetOpen);
        }

        /// <summary>
        /// The live view through the crystal windows (I.XIII): a backdrop shell of open water round the ship and
        /// schools of fish and medusae (SeaWindowView), all in the Verne/SeaLit water model.
        /// </summary>
        static void SeaOutside(Transform room, SlidingPanels panels)
        {
            var sea = Shader.Find("Verne/SeaLit");
            if (sea == null) { Notes.Add("Verne/SeaLit shader missing: the saloon windows show the flat sea glow."); FallbackSeaGlow(room); return; }
            Material SeaMat(string name, Color c, Color emission, float sheen, float wiggle, float backdrop, float pulse)
            {
                string path = VerneBootstrap.Generated + "/Materials/M_Sea_" + name + ".mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (m == null) { m = new Material(sea); AssetDatabase.CreateAsset(m, path); }
                m.shader = sea;
                m.SetColor("_BaseColor", c); m.SetColor("_Emission", emission); m.SetFloat("_Sheen", sheen);
                m.SetFloat("_Wiggle", wiggle); m.SetFloat("_WiggleSpeed", 1.6f); m.SetFloat("_Backdrop", backdrop); m.SetFloat("_Pulse", pulse);
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
                return m;
            }
            var shell = new GameObject("Sea beyond (backdrop shell)");
            shell.transform.SetParent(room, false);
            shell.transform.localPosition = new Vector3(0f, 2f, 15f);
            shell.AddComponent<MeshFilter>().sharedMesh = InvertedSphere(48f);
            var mr = shell.AddComponent<MeshRenderer>();
            mr.sharedMaterial = SeaMat("Backdrop", Color.black, Color.black, 0f, 0f, 1f, 0f);
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; mr.receiveShadows = false;

            var view = room.parent.gameObject.AddComponent<SeaWindowView>();
            view.panels = panels;
            view.fishMaterial = SeaMat("Fish", new Color(0.32f, 0.36f, 0.4f), Color.black, 0.35f, 0.06f, 0f, 0f);
            view.silverMaterial = SeaMat("Silver", new Color(0.62f, 0.7f, 0.74f), Color.black, 1f, 0.05f, 0f, 0f);
            view.goldMaterial = SeaMat("Gold", new Color(0.95f, 0.28f, 0.06f), Color.black, 0.6f, 0.05f, 0f, 0f);
            view.medusaMaterial = SeaMat("Medusa", new Color(0.75f, 0.7f, 0.85f), new Color(0.12f, 0.22f, 0.4f), 0.4f, 0f, 0f, 1.7f);
        }

        static Mesh InvertedSphere(float radius)
        {
            string path = VerneBootstrap.Generated + "/Meshes/sea_shell.asset";
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (existing != null) return existing;
            const int lat = 12, lon = 24;
            var v = new List<Vector3>(); var t = new List<int>();
            for (int i = 0; i <= lat; i++)
                for (int j = 0; j <= lon; j++)
                {
                    float th = Mathf.PI * i / lat, ph = 2f * Mathf.PI * j / lon;
                    v.Add(new Vector3(Mathf.Sin(th) * Mathf.Cos(ph), Mathf.Cos(th), Mathf.Sin(th) * Mathf.Sin(ph)) * radius);
                }
            for (int i = 0; i < lat; i++)
                for (int j = 0; j < lon; j++)
                {
                    int a = i * (lon + 1) + j, b = a + 1, c = a + lon + 1, d = c + 1;
                    t.AddRange(new[] { a, c, b, b, c, d });   // wound to face inward (cross(e1, e2) points to the centre)
                }
            var m = new Mesh { name = "sea_shell" };
            m.SetVertices(v); m.SetTriangles(t, 0); m.RecalculateNormals(); m.RecalculateBounds();
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static void FallbackSeaGlow(Transform room)
        {
            foreach (float sign in new[] { -1f, 1f })
                Box("Sea beyond " + (sign < 0 ? "port" : "starboard"), room, new Vector3(sign * 6.7f, 2.0f, 15f), new Vector3(0.1f, 8f, 14f), "LampWhite", 1f, false, null, false)
                    .GetComponent<MeshRenderer>().sharedMaterial = SeaGlowMaterial();
        }

        static Material s_SeaGlow;
        static Material SeaGlowMaterial()
        {
            if (s_SeaGlow != null) return s_SeaGlow;
            string path = VerneBootstrap.Generated + "/Materials/M_SeaGlow.mat";
            s_SeaGlow = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (s_SeaGlow == null)
            {
                s_SeaGlow = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
                AssetDatabase.CreateAsset(s_SeaGlow, path);
            }
            s_SeaGlow.SetColor("_BaseColor", new Color(0.05f, 0.28f, 0.32f));
            return s_SeaGlow;
        }

        static void FurnishLibrary(Transform room, float x0, float x1)
        {
            // ebony cases inlaid with brass following the walls, divans below, the great table
            if (!Art) {
            Box("Shelves port", room, new Vector3(x0 + 0.25f, 1.6f, 7.5f), new Vector3(0.45f, 3.0f, 4.6f), "Ebony");
            Box("Shelves starboard", room, new Vector3(x1 - 0.25f, 1.6f, 7.5f), new Vector3(0.45f, 3.0f, 4.6f), "Ebony");
            Box("Divan port", room, new Vector3(x0 + 0.85f, 0.25f, 7.5f), new Vector3(0.7f, 0.5f, 4.2f), "Leather");
            Box("Divan starboard", room, new Vector3(x1 - 0.85f, 0.25f, 7.5f), new Vector3(0.7f, 0.5f, 4.2f), "Leather");
            Box("Great table", room, new Vector3(0, 0.38f, 7.5f), new Vector3(1.6f, 0.76f, 2.4f), "Oak");
            }
            var book = Box("An open volume", room, new Vector3(0.2f, 0.8f, 7.2f), new Vector3(0.3f, 0.04f, 0.22f), "Leather", 1f, true, null, false);
            book.layer = ProjectSetup.InteractableLayer;
            var r = book.AddComponent<Readable>();
            r.noun = "the volume";
            r.title = "Twelve thousand volumes";
            r.body = "“These are the only ties which bind me to the earth. But I had done with the world on the day when my Nautilus plunged for the first time beneath the waters.”";
            r.signature = "Captain Nemo, Part I, Chapter X";
        }

        static void FurnishDining(Transform room)
        {
            if (Art) return;
            // sideboards at both extremities, either side of each door (never across a doorway)
            foreach (float z in new[] { 0.3f, 4.7f })
                foreach (float x in new[] { -2.05f, 2.05f })
                    Box("Sideboard", room, new Vector3(x, 1.1f, z), new Vector3(1.9f, 2.2f, 0.5f), "Oak");
            Box("Table", room, new Vector3(0, 0.38f, 2.5f), new Vector3(1.2f, 0.76f, 2.0f), "Linen");
        }

        static void BuildFloodingCell(Transform ship, Transform robing, float cx, float z0, float z1)
        {
            float x0 = cx, x1 = cx + 3.2f, h = 2.3f;
            var cell = new GameObject("Flooding cell").transform;
            cell.SetParent(ship, false);
            Slabs("Flooding cell", cell, x0, x1, z0, z1, 0f, h, "Iron", "Iron", "iron");
            Wall("Cell fore (inner door)", ship, new Vector2(x0, z1), new Vector2(x1, z1), 0, h, "Iron", new Opening(1.0f, 0.9f, 2.0f));
            Wall("Cell aft", ship, new Vector2(x0, z0), new Vector2(x1, z0), 0, h, "Iron");
            Wall("Cell starboard", ship, new Vector2(x1, z0), new Vector2(x1, z1), 0, h, "Iron");
            Wall("Cell port (outer door, in the hull)", ship, new Vector2(x0, z0), new Vector2(x0, z1), 0, h, "Iron", new Opening(1.25f, 0.9f, 2.0f));
            // where the corridor would continue: closed off, this is the sea side
            Wall("Robing room aft, beside the cell", ship, new Vector2(x1, z1), new Vector2(3.2f, z1), 0, 2.4f, "IronPaint");
            Wall("Sea-side port", ship, new Vector2(-3.2f, z0), new Vector2(-3.2f, z1), 0, h, "Iron");
            Box("Sea-side sill", ship, new Vector3(-2.6f, -0.1f, (z0 + z1) * 0.5f), new Vector3(1.2f, 0.2f, z1 - z0), "Iron", 1.6f, true, "iron");
            Box("Sea-side roof", ship, new Vector3(-2.6f, h + 0.1f, (z0 + z1) * 0.5f), new Vector3(1.2f, 0.2f, z1 - z0), "Iron");
            Wall("Sea-side aft", ship, new Vector2(-3.2f, z0), new Vector2(cx, z0), 0, h, "Iron");

            var inner = HingedDoor(cell, "Inner door (stopper-plates)", new Vector3(x0 + 0.55f, 0, z1), 90f, 0.9f, 2.0f, "Iron");
            inner.openAngle = 100f;
            // the stopper-plates: a hand-wheel on the cell face of the door drives the dogs home (Iron Lung: you seal yourself in)
            var dogWheel = Cylinder("Stopper-plate wheel", inner.transform, new Vector3(0.08f, 1.1f, 0.45f), 0.17f, 0.04f, "Brass", true);
            dogWheel.transform.localRotation = Quaternion.Euler(0, 0, 90);
            dogWheel.layer = ProjectSetup.InteractableLayer;
            var dogs = dogWheel.AddComponent<Valve>();
            dogs.noun = "the stopper-plates"; dogs.axis = Vector3.up; dogs.turns = 1.5f; dogs.turnRate = 0.6f;
            for (int k = 0; k < 4; k++)   // the four dogs at the leaf's edges
            {
                float yy = k < 2 ? 0.35f + k * 1.3f : 1.0f;
                float zz = k < 2 ? 0.86f : (k == 2 ? 0.86f : 0.04f);
                Box("Dog " + k, inner.transform, new Vector3(0.06f, yy, zz), new Vector3(0.05f, 0.08f, 0.1f), "Brass", 1f, false, null, false);
            }
            var outer = HingedDoor(cell, "Outer door (hull)", new Vector3(x0, 0, z0 + 0.8f), 0f, 0.9f, 2.0f, "Iron");

            // the tap and the gauge on the starboard wall, the pump knob beside them
            var tapBody = Box("Tap housing", cell, new Vector3(x1 - 0.15f, 1.2f, (z0 + z1) * 0.5f), new Vector3(0.2f, 0.3f, 0.3f), "Brass");
            var wheel = Cylinder("Tap wheel", tapBody.transform, new Vector3(-0.13f, 0, 0), 0.16f, 0.04f, "Brass", true);
            wheel.transform.localRotation = Quaternion.Euler(0, 0, 90);
            wheel.layer = ProjectSetup.InteractableLayer;
            var valve = wheel.AddComponent<Valve>();
            valve.verb = "Turn"; valve.noun = "the sea tap"; valve.axis = Vector3.up; valve.turns = 2.5f;

            var gaugeGo = Cylinder("Pressure gauge", cell, new Vector3(x1 - 0.1f, 1.75f, (z0 + z1) * 0.5f), 0.14f, 0.04f, "Brass", false);
            gaugeGo.transform.localRotation = Quaternion.Euler(0, 0, 90);
            var gp = new GameObject("pivot").transform; gp.SetParent(gaugeGo.transform, false); gp.localPosition = new Vector3(0, -1.05f, 0);
            Box("needle", gp, new Vector3(0, 0, 0.3f), new Vector3(0.05f, 0.05f, 0.6f), "IronPaint", 1f, false, null, false);
            var gauge = gaugeGo.AddComponent<Gauge>();
            gauge.needle = gp; gauge.axis = Vector3.up; gauge.minValue = 0; gauge.maxValue = 4; gauge.target = 1;

            var knobBody = Box("Pump knob", cell, new Vector3(x1 - 0.1f, 1.2f, z1 - 0.35f), new Vector3(0.08f, 0.08f, 0.08f), "Brass", 1f, true, null, false);
            knobBody.layer = ProjectSetup.InteractableLayer;
            var knob = knobBody.AddComponent<PushButton>();
            knob.verb = "Press"; knob.noun = "the pump knob";

            var water = Box("Water surface", cell, new Vector3((x0 + x1) * 0.5f, 0, (z0 + z1) * 0.5f), new Vector3(x1 - x0 - 0.05f, 0.01f, z1 - z0 - 0.05f), "Glass", 1f, false, null, false);

            var fc = cell.gameObject.AddComponent<FloodingCell>();
            fc.innerDoor = inner; fc.dogs = dogs; fc.outerDoor = outer; s_Cell = fc; fc.floodTap = valve; fc.pumpKnob = knob; fc.pressureGauge = gauge;
            fc.waterSurface = water.transform; fc.floorY = 0f; fc.ceilingY = h; fc.outsideDepth = 9f;
            fc.volume = new Bounds(new Vector3((x0 + x1) * 0.5f, h * 0.5f, (z0 + z1) * 0.5f), new Vector3(x1 - x0, h, z1 - z0));

            var exit = new GameObject("Step onto the sea floor");
            exit.transform.SetParent(ship, false);
            exit.transform.localPosition = new Vector3(-2.7f, 1.0f, (z0 + z1) * 0.5f);
            var bc = exit.AddComponent<BoxCollider>(); bc.isTrigger = true; bc.size = new Vector3(0.6f, 2f, 1.6f);
            var se = exit.AddComponent<SceneExit>(); se.scene = SceneFlow.Mission1; se.requiresFlooded = fc;
            s_SeaDoor = se;

            // the dresses hang on the robing-room partitions; the visitor's own kit waits on the bench (Blender kit_* objects)
            GameObject suits;
            if (s_AftArt != null)
            {
                suits = Box("The bench where the visitors are dressed", robing, new Vector3(1.33f, 0.9f, -14.72f), new Vector3(2.95f, 1.8f, 0.5f), "Greybox", 1f, true, null, false);
                suits.GetComponent<MeshRenderer>().enabled = false;
            }
            else suits = Box("A dozen diving apparatuses", robing, new Vector3(3.0f, 1.2f, -13.75f), new Vector3(0.3f, 2.0f, 2.2f), "Leather");
            suits.layer = ProjectSetup.InteractableLayer;
            var station = suits.AddComponent<SuitStation>();
            station.reach = 2.6f;
            if (s_AftArt != null)
            {
                GameObject K(string n) { var t = Markers.Find(s_AftArt, n); if (t == null) Notes.Add("Kit object missing: " + n); return t != null ? t.gameObject : null; }
                station.kitDress = K("kit_dress"); station.kitReservoir = K("kit_reservoir"); station.kitLamp = K("kit_lamp");
                station.kitGun = K("kit_gun"); station.kitStick = K("kit_stick"); station.kitHelmet = K("kit_helmet");
            }
            PointLight("Cell lamp", cell, new Vector3((x0 + x1) * 0.5f, h - 0.2f, (z0 + z1) * 0.5f), new Color(1f, 0.92f, 0.8f), 1.2f, 4f);
        }

        // ------------------------------------------------------------------ sea floor
        static Mesh SeabedMesh(string key, float size, float step, float amp, float freq, int seed, System.Func<float, float, float> extra = null)
        {
            string path = VerneBootstrap.Generated + "/Meshes/seabed_" + key + ".asset";
            var old = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (old != null) AssetDatabase.DeleteAsset(path);
            int n = Mathf.RoundToInt(size / step) + 1;
            var v = new Vector3[n * n]; var uv = new Vector2[n * n];
            float ox = seed * 17.3f, oz = seed * 9.1f;
            for (int j = 0; j < n; j++)
                for (int i = 0; i < n; i++)
                {
                    float x = -size * 0.5f + i * step, z = -size * 0.5f + j * step;
                    float y = (Mathf.PerlinNoise(ox + x * freq, oz + z * freq) - 0.5f) * amp
                            + (Mathf.PerlinNoise(ox + x * freq * 4f, oz + z * freq * 4f) - 0.5f) * amp * 0.2f;
                    if (extra != null) y += extra(x, z);
                    v[j * n + i] = new Vector3(x, y, z);
                    uv[j * n + i] = new Vector2(x / 3f, z / 3f);
                }
            var t = new int[(n - 1) * (n - 1) * 6];
            int k = 0;
            for (int j = 0; j < n - 1; j++)
                for (int i = 0; i < n - 1; i++)
                {
                    int a = j * n + i, b = a + 1, c = a + n, d = c + 1;
                    t[k++] = a; t[k++] = c; t[k++] = b; t[k++] = b; t[k++] = c; t[k++] = d;
                }
            var m = new Mesh { name = "seabed_" + key, indexFormat = n * n > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
            m.vertices = v; m.uv = uv; m.triangles = t;
            m.RecalculateNormals(); m.RecalculateTangents(); m.RecalculateBounds();
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static GameObject Seabed(Transform parent, float size, float step, float amp, float freq, string mat, int seed, System.Func<float, float, float> extra = null, string key = null)
        {
            var go = new GameObject("Sea floor");
            go.transform.SetParent(parent, false);
            var mesh = SeabedMesh(key ?? (mat + seed), size, step, amp, freq, seed, extra);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            go.AddComponent<MeshRenderer>().sharedMaterial = Materials.Get(mat);
            go.AddComponent<MeshCollider>().sharedMesh = mesh;
            go.AddComponent<Surface>().kind = mat == "Sand" ? "sand" : "rock";
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI);
            return go;
        }

        static float GroundAt(Vector3 p)
        {
            Physics.SyncTransforms();
            return Physics.Raycast(new Vector3(p.x, 200f, p.z), Vector3.down, out var hit, 400f) ? hit.point.y : 0f;
        }

        static void Rocks(Transform parent, int count, float radius, int seed, string mat, float scale = 1f)
        {
            var rnd = new System.Random(seed);
            var root = new GameObject("Rocks").transform; root.SetParent(parent, false);
            for (int i = 0; i < count; i++)
            {
                float a = (float)rnd.NextDouble() * Mathf.PI * 2f, r = Mathf.Sqrt((float)rnd.NextDouble()) * radius;
                var p = new Vector3(Mathf.Cos(a) * r, 0, Mathf.Sin(a) * r);
                if (p.magnitude < 4f) continue;
                var s = new Vector3(0.6f + (float)rnd.NextDouble() * 2.2f, 0.4f + (float)rnd.NextDouble() * 1.6f, 0.6f + (float)rnd.NextDouble() * 2.2f) * scale;
                s = new Vector3(Mathf.Round(s.x * 2f) / 2f, Mathf.Round(s.y * 2f) / 2f, Mathf.Round(s.z * 2f) / 2f); // shared meshes
                var go = Box("Rock " + i, root, p, s, mat, 1.2f, true, "rock");
                go.transform.position = new Vector3(p.x, GroundAt(p) + s.y * 0.3f, p.z);
                go.transform.rotation = Quaternion.Euler((float)rnd.NextDouble() * 20f, (float)rnd.NextDouble() * 360f, (float)rnd.NextDouble() * 20f);
            }
        }

        /// <summary>The book's "region of perpendicularity": rigid vertical stems (I.XVI).</summary>
        static void KelpStand(Transform parent, Vector3 centre, int count, float radius, int seed, string mat = "Greybox", float hMin = 2.5f, float hMax = 5f)
        {
            var rnd = new System.Random(seed);
            var root = new GameObject("Vertical forest").transform; root.SetParent(parent, false);
            for (int i = 0; i < count; i++)
            {
                float a = (float)rnd.NextDouble() * Mathf.PI * 2f, r = Mathf.Sqrt((float)rnd.NextDouble()) * radius;
                var p = centre + new Vector3(Mathf.Cos(a) * r, 0, Mathf.Sin(a) * r);
                float h = Mathf.Round(Mathf.Lerp(hMin, hMax, (float)rnd.NextDouble()) * 4f) / 4f; // quantised so meshes are shared
                var go = Box("Stem " + i, root, p, new Vector3(0.12f, h, 0.12f), mat, 1f, true, "weed");
                go.transform.position = new Vector3(p.x, GroundAt(p) + h * 0.5f, p.z);
            }
        }

        // ------------------------------------------------------------------ Mission I
        public static void Mission1()
        {
            var s = NewScene("Mission1");
            // shallows at ~9 m: bright, green-blue far field (M3 replaces fog with the physical water model)
            Ambient(new Color(0.16f, 0.34f, 0.36f), new Color(0.07f, 0.17f, 0.19f), new Color(0.03f, 0.06f, 0.07f));
            Fog(true, new Color(0.10f, 0.33f, 0.36f), 0.022f);
            Sun("Sun (refracted)", new Vector3(58, 30, 0), new Color(0.9f, 0.97f, 0.92f), 1.8f);
            var root = new GameObject("Crespo").transform;
            // the route runs north (+Z): sand plain → weed prairie → forest → coral gallery → glade
            Seabed(root, 240f, 2f, 3.5f, 0.025f, "Sand", 21, (x, z) => -Mathf.Clamp01((z - 40f) / 160f) * 18f);
            Rocks(root, 60, 110f, 22, "Rock");
            KelpStand(root, new Vector3(0, 0, 70), 140, 26f, 23, "Greybox", 3f, 4.6f);
            var glade = new GameObject("Coral cemetery (placeholder)").transform; glade.SetParent(root, false);
            var gp = new Vector3(0, 0, 110);
            Box("Pedestal of rocks", glade, new Vector3(gp.x, GroundAt(gp) + 0.4f, gp.z), new Vector3(1.2f, 0.8f, 1.2f), "Rock", 1.2f, true, "rock");
            Box("Coral cross upright", glade, new Vector3(gp.x, GroundAt(gp) + 1.8f, gp.z), new Vector3(0.22f, 2.0f, 0.22f), "CoralRed");
            Box("Coral cross arms", glade, new Vector3(gp.x, GroundAt(gp) + 2.2f, gp.z), new Vector3(1.3f, 0.2f, 0.22f), "CoralRed");
            NautilusAtTheDoor(root, SceneFlow.Nautilus);
            var sp = new Vector3(0, 0, 0);
            Spawn(new Vector3(0, GroundAt(sp) + 0.1f, 0), 0f, MoveMode.Water, 200f);
            GlobalVolume("Mission1");
            Save(s, "Mission1");
        }

        // ------------------------------------------------------------------ Mission II
        public static void Mission2()
        {
            var s = NewScene("Mission2");
            // midnight at 150 fathoms; the only light is the volcano's red glow, two miles off
            Ambient(new Color(0.02f, 0.02f, 0.03f), new Color(0.015f, 0.01f, 0.012f), new Color(0.005f, 0.004f, 0.004f));
            Fog(true, new Color(0.035f, 0.015f, 0.015f), 0.03f);
            var root = new GameObject("Atlantis approach").transform;
            Seabed(root, 240f, 2f, 5f, 0.03f, "Rock2", 31, (x, z) => Mathf.Max(0f, 1f - Mathf.Abs(z - 120f) / 70f) * 60f * Mathf.Max(0f, 1f - Mathf.Abs(x) / 90f));
            Rocks(root, 80, 110f, 32, "Basalt", 1.4f);
            // petrified copse: black stems, the "paper cuttings" (II.IX)
            KelpStand(root, new Vector3(0, 0, 70), 90, 22f, 33, "Basalt", 3f, 9f);
            var glow = new GameObject("Volcano glow (beyond the summit)");
            glow.transform.SetParent(root, false);
            glow.transform.position = new Vector3(0, 70, 170);
            var l = glow.AddComponent<Light>();
            l.type = LightType.Point; l.color = new Color(1f, 0.38f, 0.16f); l.intensity = 30f; l.range = 220f; l.shadows = LightShadows.None;
            NautilusAtTheDoor(root, SceneFlow.Nautilus);
            var sp = new Vector3(0, 0, 0);
            Spawn(new Vector3(0, GroundAt(sp) + 0.1f, 0), 0f, MoveMode.Water, 200f);
            GlobalVolume("Mission2");
            Save(s, "Mission2");
        }

        /// <summary>
        /// The Nautilus lying on the bottom behind the spawn point, its port side (with the flooding-cell
        /// door and the iron rungs below it) facing the player. Climbing the rungs and entering the door
        /// returns aboard.
        /// </summary>
        static void NautilusAtTheDoor(Transform root, string returnScene)
        {
            var doorXZ = new Vector3(0f, 0f, -2.6f);
            float g = GroundAt(new Vector3(0f, 0f, -5f));
            var ship = NautilusExterior.Place(root, doorXZ, Vector3.right, g);
            if (ship == null) return;
            Physics.SyncTransforms();
            float deck = ship.transform.position.y;
            var rungs = new GameObject("Iron rungs below the door");
            rungs.transform.SetParent(root, false);
            rungs.transform.position = new Vector3(0f, GroundAt(new Vector3(0, 0, -2.3f)), -2.3f);
            rungs.transform.rotation = Quaternion.LookRotation(Vector3.forward, Vector3.up);
            var rbc = rungs.AddComponent<BoxCollider>(); rbc.isTrigger = true;
            float climb = Mathf.Max(0.5f, deck - rungs.transform.position.y + 0.3f);
            rbc.size = new Vector3(1.0f, climb + 0.6f, 1.0f); rbc.center = new Vector3(0f, climb * 0.5f, 0.3f);
            var lad = rungs.AddComponent<Verne.Ladder>(); lad.length = climb; lad.climbSpeed = 0.7f;
            var ret = new GameObject("Return aboard (flooding-cell door)");
            ret.transform.SetParent(root, false);
            ret.transform.position = new Vector3(0f, deck + 1.0f, -2.75f);
            var bc = ret.AddComponent<BoxCollider>(); bc.isTrigger = true; bc.size = new Vector3(1.2f, 2.0f, 0.8f);
            ret.AddComponent<SceneExit>().scene = returnScene;
            Notes.Add($"Nautilus placed on the bottom: deck {deck:0.0} m, door above the rungs at z = -2.6.");
        }

        // ------------------------------------------------------------------ build settings and validation
        public static void BuildSettings()
        {
            var scenes = new[] { "Title", "Nautilus", "Mission1", "Mission2" }
                .Select(n => new EditorBuildSettingsScene(ScenePath(n), true)).ToArray();
            EditorBuildSettings.scenes = scenes;
            Notes.Add("Build order: " + string.Join(", ", scenes.Select(x => System.IO.Path.GetFileNameWithoutExtension(x.path))));
        }

        public static void Validate()
        {
            int problems = 0;
            foreach (var n in new[] { "Title", "Nautilus", "Mission1", "Mission2" })
            {
                var sc = EditorSceneManager.OpenScene(ScenePath(n), OpenSceneMode.Single);
                int missing = 0, renderers = 0, colliders = 0, lights = 0; long tris = 0;
                foreach (var root in sc.GetRootGameObjects())
                {
                    foreach (var t in root.GetComponentsInChildren<Transform>(true))
                        missing += GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject);
                    foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
                    {
                        renderers++;
                        var mf = r.GetComponent<MeshFilter>();
                        if (mf == null || mf.sharedMesh == null) { problems++; Notes.Add($"{n}: {r.name} has no mesh"); continue; }
                        if (r.sharedMaterial == null) { problems++; Notes.Add($"{n}: {r.name} has no material"); }
                        tris += mf.sharedMesh.triangles.LongLength / 3;
                    }
                    colliders += root.GetComponentsInChildren<Collider>(true).Length;
                    lights += root.GetComponentsInChildren<Light>(true).Length;
                    foreach (var fc in root.GetComponentsInChildren<FloodingCell>(true))
                        if (fc.innerDoor == null || fc.outerDoor == null || fc.floodTap == null || fc.pressureGauge == null) { problems++; Notes.Add($"{n}: flooding cell has a missing reference"); }
                    foreach (var lv in root.GetComponentsInChildren<Lever>(true))
                        if (lv.onValueChanged.GetPersistentEventCount() == 0) Notes.Add($"{n}: lever '{lv.name}' drives nothing yet");
                }
                bool needsSpawn = n != "Title";
                bool hasSpawn = Object.FindObjectsByType<PlayerSpawn>(FindObjectsSortMode.None).Length > 0;
                if (needsSpawn && !hasSpawn) { problems++; Notes.Add($"{n}: no PlayerSpawn"); }
                if (missing > 0) problems++;
                Notes.Add($"{n}: {renderers} renderers, {tris:N0} triangles, {colliders} colliders, {lights} lights, {missing} missing scripts");
            }
            if (problems > 0) throw new System.Exception($"{problems} problem(s) found; see the notes above.");
        }
    }
}
