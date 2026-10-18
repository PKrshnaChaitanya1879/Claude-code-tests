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

        /// <summary>The caustic web on the sun (cookie imported as a repeating light cookie).</summary>
        static void Caustics(Light sun, float size)
        {
            string path = VerneBootstrap.Root + "/Textures/caustics_cookie.png";
            var ti = AssetImporter.GetAtPath(path) as TextureImporter;
            if (ti == null) { Notes.Add("Caustics cookie missing."); return; }
            if (ti.textureType != TextureImporterType.Cookie || ti.wrapMode != TextureWrapMode.Repeat)
            {
                ti.textureType = TextureImporterType.Cookie; ti.wrapMode = TextureWrapMode.Repeat; ti.sRGBTexture = false; ti.mipmapEnabled = true;
                ti.SaveAndReimport();
            }
            var c = sun.gameObject.AddComponent<CausticCookie>();
            c.cookie = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            c.size = size;
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
            RenderSettings.customReflectionTexture = AmbientCube(sky, equator, ground);   // brass and iron reflect the room's own light, not black
        }

        /// <summary>A tiny reflection cubemap in the scene's ambient colours (sky above, equator around, ground below), saved as an asset.</summary>
        static Cubemap AmbientCube(Color sky, Color equator, Color ground)
        {
            const int N = 16;
            var cube = new Cubemap(N, TextureFormat.RGBA32, false);
            var faces = new[] { CubemapFace.PositiveX, CubemapFace.NegativeX, CubemapFace.PositiveY, CubemapFace.NegativeY, CubemapFace.PositiveZ, CubemapFace.NegativeZ };
            foreach (var f in faces)
            {
                var px = new Color[N * N];
                for (int y = 0; y < N; y++)
                    for (int x = 0; x < N; x++)
                    {
                        float v = 1f - (y + 0.5f) / N;    // 1 at the top row of a side face
                        Color c = f == CubemapFace.PositiveY ? sky : f == CubemapFace.NegativeY ? ground
                                : (v > 0.5f ? Color.Lerp(equator, sky, (v - 0.5f) * 2f) : Color.Lerp(ground, equator, v * 2f));
                        c.a = 1f; px[y * N + x] = c;
                    }
                cube.SetPixels(px, f);
            }
            cube.Apply(false);
            string path = VerneBootstrap.Generated + "/Rendering/AmbientReflection_" + UnityEngine.SceneManagement.SceneManager.GetActiveScene().name + ".cubemap";
            if (AssetDatabase.LoadAssetAtPath<Cubemap>(path) != null) AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(cube, path);
            return cube;
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
            Caustics(Sun("Sun (refracted)", new Vector3(62, 25, 0), new Color(0.75f, 0.92f, 0.95f), 1.4f), 9f);
            var root = new GameObject("Seabed").transform;
            Seabed(root, 120f, 2f, 3.0f, 0.03f, "Sand", 7);
            Rocks(root, 26, 50f, 11, "Rock");
            KelpStand(root, new Vector3(-6, 0, 24), 18, 7f, 13);
            var hero = AssetDatabase.LoadAssetAtPath<GameObject>(NautilusExterior.PrefabPath);
            Light lantern = null;
            if (hero != null)
            {
                var n = (GameObject)PrefabUtility.InstantiatePrefab(hero, root);
                n.transform.SetPositionAndRotation(new Vector3(14f, 6.5f, 46f), Quaternion.Euler(0f, -72f, 0f));
                lantern = n.GetComponentsInChildren<Light>(true).FirstOrDefault(x => x.type == LightType.Spot);   // its beam in the water
            }
            var cam = PreviewCamera(new Vector3(0, 2.2f, -4), new Vector3(-8, 14, 0), new Color(0.05f, 0.16f, 0.19f));
            Water("Title", lantern);
            // life round the resting ship: a school passing through the shafts, medusae drifting above
            var life = new GameObject("Life").transform; life.SetParent(root, false);
            var ts = new GameObject("A school").AddComponent<FishSchool>(); ts.transform.SetParent(life, false);
            ts.material = LitMat("Fish_Silver", new Color(0.72f, 0.78f, 0.82f), 0.55f, 0.8f); ts.count = 40; ts.size = 0.22f; ts.speed = 1.1f; ts.spread = 3f;
            ts.waypoints = new[] { new Vector3(-6, 5, 18), new Vector3(8, 7, 30), new Vector3(2, 9, 48), new Vector3(-9, 6, 34) };
            var tm = new GameObject("Medusae").AddComponent<FishSchool>(); tm.transform.SetParent(life, false);
            tm.kind = FishSchool.Kind.Medusa; tm.material = LitMat("Medusa", new Color(0.95f, 0.62f, 0.72f), 0f, 0.85f, new Color(0.08f, 0.14f, 0.35f));
            tm.count = 6; tm.size = 0.7f; tm.speed = 0.2f; tm.spread = 8f; tm.waypoints = new[] { new Vector3(-3, 10, 22), new Vector3(4, 12, 32) };
            var t = new GameObject("Title Screen").AddComponent<TitleScreen>();
            t.driftCamera = cam.transform;
            GlobalVolume("Title");
            Save(s, "Title");
        }

        // ------------------------------------------------------------------ Nautilus
        public static void Nautilus()
        {
            var s = NewScene("Nautilus");
            Greybox.Doorways.Clear(); Greybox.Structure.Clear();
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

            // the passage beside the cell and the engine-room, 65 ft long (I.XI, plate im024)
            Room(ship, "Passage to the engine-room", 1.2f, X1, -17.5f, -15f, 2.3f, null, "Iron", "Ceiling", "iron");
            Wall("Passage starboard", ship, new Vector2(X1, -17.5f), new Vector2(X1, -15f), 0, 2.3f, "Iron");
            var engine = Room(ship, "Engine-room", X0, X1, -37.5f, -17.5f, 4.4f, null, "Iron", "Ceiling", "iron");
            Wall("Engine-room fore", ship, new Vector2(1.2f, -17.5f), new Vector2(X1, -17.5f), 0, 4.4f, "Iron", new Opening(1.475f, 0.75f, 2.0f));
            Wall("Engine-room fore, above the cell", ship, new Vector2(X0, -17.5f), new Vector2(1.2f, -17.5f), 2.3f, 2.1f, "Iron");
            SideWalls(ship, X0, X1, -37.5f, -17.5f, 4.4f, "Iron");
            Wall("Engine-room aft (the screw's stuffing box)", ship, new Vector2(X0, -37.5f), new Vector2(X1, -37.5f), 0, 4.4f, "Iron");
            foreach (float z in new[] { -21f, -28f, -34f })
                PointLight("Engine-room light", engine, new Vector3(0f, 3.8f, z), new Color(1f, 0.94f, 0.84f), 1.6f, 9f);
            var engDoor = HingedDoor(engine, "Engine-room door", new Vector3(2.3f, 0, -15f), 90f, 0.75f, 2.0f, "Iron");
            engDoor.openAngle = 100f;

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
            if (s_AftArt != null) { HideGreyboxWhereArt(ship, -37.6f, -0.01f); MachineryTurns(s_AftArt); }
            else Notes.Add("Aft block FBX missing: the aft rooms stay greybox.");
            var chapter = ship.gameObject.AddComponent<ChapterAboard>();
            chapter.note = s_Note; chapter.cell = s_Cell; chapter.seaDoor = s_SeaDoor;
            BookPlaques(ship);
            PaintingPlaques(ship);
            Ladder(hall, new Vector3(2.4f, 0, -1.6f), 3.2f);

            Notes.Add(Greybox.ClearDoorways());
            Spawn(new Vector3(0.8f, 0.05f, 26.2f), 180f, MoveMode.Air, 120f);
            GlobalVolume("Nautilus");
            Save(s, "Nautilus");
        }

        static bool Art;

        /// <summary>An invisible, readable volume over a thing the book describes: look at it, read Verne's own words.</summary>
        static Readable Plaque(Transform parent, string name, Vector3 centre, Vector3 size, string verb, string noun, string title, string body, string cite)
        {
            var go = Box(name, parent, centre, size, "Greybox", 1f, true, null, false);
            go.GetComponent<MeshRenderer>().enabled = false;
            go.GetComponent<BoxCollider>().isTrigger = true;   // never blocks the player; the interactor still finds it
            go.layer = ProjectSetup.InteractableLayer;
            var r = go.AddComponent<Readable>();
            r.verb = verb; r.noun = noun; r.title = title; r.body = body; r.signature = cite;
            return r;
        }


        static readonly Dictionary<string, (string artist, string title)> k_Paintings = new Dictionary<string, (string, string)>
        {
            { "437373", ("Raphael", "Giuliano de' Medici (1479–1516), Duke of Nemours") },
            { "435992", ("Correggio (Antonio Allegri)", "Saints Peter, Martha, Mary Magdalen, and Leonard") },
            { "437827", ("Titian", "Venus and the Lute Player") },
            { "437828", ("Titian", "Alfonso d'Este (1486–1534), Duke of Ferrara") },
            { "437889", ("Paolo Veronese (Paolo Caliari)", "Alessandro Vittoria (1525–1608)") },
            { "437890", ("Paolo Veronese (Paolo Caliari)", "Boy with a Greyhound") },
            { "437172", ("Bartolomé Estebán Murillo", "The Crucifixion") },
            { "437173", ("Bartolomé Estebán Murillo", "Don Andrés de Andrade y la Cal") },
            { "437872", ("Velázquez", "Mariana of Austria (1634–1696), Queen of Spain") },
            { "437875", ("Velázquez", "Portrait of a Man") },
            { "437776", ("David Teniers the Younger", "The Good Samaritan") },
            { "437777", ("David Teniers the Younger", "Guardroom with the Deliverance of Saint Peter") },
            { "437070", ("Gabriël Metsu", "A Musical Party") },
            { "437071", ("Gabriël Metsu", "The Visit to the Nursery") },
            { "437339", ("Pierre Paul Prud'hon", "Andromache and Astyanax") },
            { "437340", ("Pierre Paul Prud'hon", "Charles Maurice de Talleyrand Périgord (1754–1838), Prince de Talleyrand") },
            { "437886", ("Joseph Vernet", "Harbor Scene with a Grotto and Fishermen Hauling in Nets") },
            { "437846", ("Constant Troyon", "Going to Market") },
            { "437847", ("Constant Troyon", "Road in the Woods") },
            { "437049", ("Ernest Meissonier", "The Card Players") },
            { "437050", ("Ernest Meissonier", "Soldier Playing the Theorbo") }
        };

        /// <summary>
        /// Each canvas in the saloon becomes readable: look at it and the picture fills the left of the screen,
        /// the painter, the title and Aronnax's words beside it (GUM: "see the painting next to our message").
        /// Works on the Blender art, where every canvas is its own sub-mesh with an M_Paint_&lt;id&gt; material.
        /// </summary>
        static void PaintingPlaques(Transform ship)
        {
            int n = 0;
            foreach (var mr in ship.GetComponentsInChildren<MeshRenderer>(true))
            {
                var mf = mr.GetComponent<MeshFilter>(); if (mf == null || mf.sharedMesh == null) continue;
                var mats = mr.sharedMaterials; var mesh = mf.sharedMesh;
                for (int i = 0; i < mats.Length && i < mesh.subMeshCount; i++)
                {
                    var m = mats[i]; if (m == null || !m.name.StartsWith("M_Paint_")) continue;
                    string id = m.name.Substring("M_Paint_".Length);
                    var lb = mesh.GetSubMesh(i).bounds;
                    var wc = mr.transform.TransformPoint(lb.center);
                    var ws = Vector3.Scale(lb.size, mr.transform.lossyScale);
                    ws = mr.transform.rotation * ws; ws = new Vector3(Mathf.Abs(ws.x), Mathf.Abs(ws.y), Mathf.Abs(ws.z));
                    ws = Vector3.Max(ws + Vector3.one * 0.08f, new Vector3(0.25f, 0.25f, 0.25f));
                    k_Paintings.TryGetValue(id, out var info);
                    var r = Plaque(ship, "Painting " + id, ship.InverseTransformPoint(wc), ws, "Look at", "the painting",
                        string.IsNullOrEmpty(info.artist) ? "A canvas" : info.artist,
                        (string.IsNullOrEmpty(info.title) ? "" : info.title + "\n\n") +
                        "\u201cSome thirty pictures by great masters, uniformly framed, separated by bright drapery, ornamented the walls, which were hung with tapestry of severe design.\u201d",
                        "Twenty Thousand Leagues, I.XI");
                    r.image = m.GetTexture("_BaseMap");
                    n++;
                }
            }
            Notes.Add($"Paintings: {n} canvases readable, each shown large beside its words.");
        }

        /// <summary>Everything aboard that Aronnax examines in Part I, ch. IX–XI, with the book's words (Mercier translation).</summary>
        static void BookPlaques(Transform ship)
        {
            Plaque(ship, "Plaque: Nemo's instruments", new Vector3(3.05f, 1.85f, 22.5f), new Vector3(0.12f, 1.3f, 2.5f), "Examine", "the instruments",
                "The instruments of the Nautilus",
                "“Here are the contrivances required for the navigation of the Nautilus. Some are known to you, such as the thermometer, which gives the internal temperature of the Nautilus; the barometer, which indicates the weight of the air and foretells the changes of the weather; the hygrometer, which marks the dryness of the atmosphere; the storm-glass, the contents of which, by decomposing, announce the approach of tempests; the compass, which guides my course; the sextant, which shows the latitude by the altitude of the sun; chronometers, by which I calculate the longitude.”\n\n“This dial with the movable needle is a manometer, is it not?”\n“It is actually a manometer. But by communication with the water, whose external pressure it indicates, it gives our depth at the same time.”",
                "Part I, Chapter XI");
            Plaque(ship, "Plaque: the pearls", new Vector3(-2.65f, 1.1f, 18.05f), new Vector3(0.62f, 0.45f, 1.12f), "Examine", "the pearls",
                "Chaplets of pearls",
                "Apart, in separate compartments, were spread out chaplets of pearls of the greatest beauty, which reflected the electric light in little sparks of fire; pink pearls, torn from the pinna-marina of the Red Sea; green pearls of the haliotyde iris; yellow, blue and black pearls, the curious productions of the divers molluscs of every ocean. Some of these pearls were larger than a pigeon’s egg.",
                "Part I, Chapter XI");
            Plaque(ship, "Plaque: the shells", new Vector3(2.65f, 1.1f, 18.05f), new Vector3(0.62f, 0.45f, 1.12f), "Examine", "the shells",
                "The collection",
                "A somewhat nervous conchyliologist would certainly have fainted before other more numerous cases, in which were classified the specimens of molluscs. Amongst these specimens I will quote from memory only the elegant royal hammer-fish of the Indian Ocean, whose regular white spots stood out brightly on a red and brown ground, an imperial spondyle, bright-coloured, bristling with spines; fragile white bivalve shells, which a breath might shatter like a soap-bubble.",
                "Part I, Chapter XI");
            Plaque(ship, "Plaque: the brazier", new Vector3(-1.4f, 1.0f, 8.9f), new Vector3(0.4f, 0.35f, 0.4f), "Take", "a cigar",
                "A cigar of sea-weed",
                "“Accept this cigar, M. Aronnax; and, though it does not come from Havannah, you will be pleased with it, if you are a connoisseur.”\n\nI took the cigar which was offered me; its shape recalled the London ones, but it seemed to be made of leaves of gold. I lighted it at a little brazier, which was supported upon an elegant bronze stem.",
                "Part I, Chapter X");
            Plaque(ship, "Plaque: the dinner service", new Vector3(0f, 0.85f, 2.5f), new Vector3(1.2f, 0.2f, 2.0f), "Look at", "the dinner service",
                "MOBILIS IN MOBILI · N.",
                "As to the dinner service, it was elegant, and in perfect taste. Each utensil, spoon, fork, knife, plate, had a letter engraved on it, with a motto above it: MOBILIS IN MOBILI, and the letter N.",
                "Part I, Chapter IX");
            Plaque(ship, "Plaque: the distilling apparatus", new Vector3(2.75f, 0.9f, -4.45f), new Vector3(0.7f, 1.2f, 0.7f), "Examine", "the still",
                "The kitchen",
                "Then a door opened into a kitchen nine feet long, situated between the large storerooms. There electricity, better than gas itself, did all the cooking. The streams under the furnaces gave out to the sponges of platina a heat which was regularly kept up and distributed. They also heated a distilling apparatus, which, by evaporation, furnished excellent drinkable water.",
                "Part I, Chapter XI");
            Plaque(ship, "Plaque: the bath", new Vector3(2.8f, 0.7f, -7.75f), new Vector3(0.8f, 0.4f, 1.3f), "Look at", "the taps",
                "The bath-room",
                "Near this kitchen was a bathroom comfortably furnished, with hot and cold water taps.",
                "Part I, Chapter XI");
            Plaque(ship, "Plaque: Ned's harpoon", new Vector3(-0.4f, 1.9f, -2.12f), new Vector3(2.6f, 0.2f, 0.12f), "Look at", "the harpoon",
                "The prince of harpooners",
                "Ned Land was a Canadian, with an uncommon quickness of hand, and who knew no equal in his dangerous occupation. Skill, coolness, audacity, and cunning he possessed in a superior degree, and it must be a cunning whale or a singularly “cute” cachalot to escape the stroke of his harpoon.",
                "Part I, Chapter III");
            Plaque(ship, "Plaque: the air-guns", new Vector3(-1.4f, 1.9f, -12.7f), new Vector3(1.1f, 0.8f, 0.35f), "Examine", "the air-guns",
                "The air-gun",
                "One of the Nautilus men gave me a simple gun, the butt end of which, made of steel, hollow in the centre, was rather large. It served as a reservoir for compressed air, which a valve, worked by a spring, allowed to escape into a metal tube. A box of projectiles contained about twenty of these electric balls. As soon as one shot was fired, another was ready.",
                "Part I, Chapter XV");
            Plaque(ship, "Plaque: Bunsen's piles", new Vector3(1.85f, 1.3f, -19.6f), new Vector3(0.25f, 0.6f, 0.6f), "Examine", "the piles",
                "The engine-room",
                "This engine-room, clearly lighted, did not measure less than sixty-five feet in length. It was divided into two parts; the first contained the materials for producing electricity, and the second the machinery that connected it with the screw.\n\n“You see,” said the Captain, “I use Bunsen’s contrivances, not Ruhmkorff’s. Bunsen’s are fewer in number, but strong and large, which experience proves to be the best. The electricity produced passes forward, where it works, by electro-magnets of great size, on a system of levers and cog-wheels that transmit the movement to the axle of the screw.”",
                "Part I, Chapter XI");

            // Nemo's organ: sit and play (Bach, public domain)
            var organ = Box("Organ keys", ship, new Vector3(0.2f, 0.85f, 19.15f), new Vector3(2.0f, 0.3f, 0.5f), "Greybox", 1f, true, null, false);
            organ.GetComponent<MeshRenderer>().enabled = false;
            organ.GetComponent<BoxCollider>().isTrigger = true;
            organ.layer = ProjectSetup.InteractableLayer;
            organ.AddComponent<Organ>();

            // the luminous ceiling's switch on the controls plate, beside the panel lever (I.XIV: the ceiling goes dark, then the panels slide)
            var saloon = ship.Find("Saloon");
            if (saloon != null)
            {
                var rl = saloon.gameObject.AddComponent<RoomLights>();
                var lights = new List<Light>(); var glow = new List<Renderer>();
                foreach (var l in saloon.GetComponentsInChildren<Light>(true)) lights.Add(l);
                foreach (var r in ship.GetComponentsInChildren<Renderer>(true))
                    if (r.name.StartsWith("saloon_ceiling_light") || r.name == "Saloon ceiling") glow.Add(r);
                rl.lights = lights.ToArray(); rl.glowing = glow.ToArray();
                var sw = Box("Ceiling switch", saloon, new Vector3(1.62f, 1.27f, 10.06f), new Vector3(0.07f, 0.07f, 0.05f), "Brass", 1f, true, null, false);
                sw.layer = ProjectSetup.InteractableLayer;
                var pb = sw.AddComponent<PushButton>();
                pb.verb = "Press"; pb.noun = "the ceiling switch";
                UnityEventTools.AddPersistentListener(pb.onUsed, rl.Toggle);
            }
        }
        static Transform s_AftArt;

        /// <summary>The axle of the screw, the great wheel and the cog turn ("about a hundred and twenty revolutions", slowed for the eye).</summary>
        static void MachineryTurns(Transform art)
        {
            foreach (var (n, rpm) in new[] { ("rot_shaft", 30f), ("rot_great_wheel", 30f), ("rot_cog", -30f * 1.62f / 0.66f) })
            {
                var t = Markers.Find(art, n);
                if (t == null) { Notes.Add("Engine part missing: " + n); continue; }
                var r = t.gameObject.AddComponent<Rotator>();
                r.axis = Vector3.forward;   // the ship's fore-and-aft axis (the ship sits unrotated at the origin)
                r.rpm = rpm;
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, 0);
            }
        }
        static Readable s_Note;
        static FloodingCell s_Cell;
        static SceneExit s_SeaDoor;

        /// <summary>The greybox boxes stay as exact, invisible colliders where the Blender rooms are shown.</summary>
        static void HideGreyboxWhereArt(Transform ship, float z0, float z1)
        {
            int n = 0, nc = 0;
            foreach (var r in ship.GetComponentsInChildren<MeshRenderer>(true))
            {
                if (r.GetComponentInParent<NautilusArtMarker>() != null) continue;
                if (r.GetComponentInParent<Interactable>() != null || r.GetComponentInParent<Gauge>() != null) continue;
                string nm = r.name;
                if (nm.StartsWith("Crystal") || nm.StartsWith("Iron panel") || nm.StartsWith("Sea beyond") || nm.Contains("Lever") || nm == "needle" || nm == "Water surface") continue;
                float z = r.bounds.center.z;
                if (z < z0 - 0.1f || z > z1) continue;
                r.enabled = false; n++;
                // GUM: "not able to cross the room". Hidden greybox FURNITURE kept its collider where the Blender
                // furniture (with its own colliders) stands elsewhere: invisible walls. Only structure keeps its collider.
                if (!Greybox.IsStructure(r.transform)) foreach (var c in r.GetComponents<Collider>()) if (!c.isTrigger) { c.enabled = false; nc++; }
            }
            Notes.Add($"{n} greybox pieces hidden; {nc} invisible furniture colliders removed (walls, floors and ceilings keep theirs).");
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
            var instruments = room.gameObject.AddComponent<NautilusInstruments>();
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
                if (d.name.StartsWith("Manometer")) instruments.manometer = g;
                else if (d.name.StartsWith("Electric clock")) instruments.clock = g;
                else if (d.name.StartsWith("Speed")) instruments.speed = g;
                else if (d.name.StartsWith("Barometer")) instruments.barometer = g;
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
            shell.transform.localScale = Vector3.one * 1.45f;   // radius ≈ 70 m: well clear of the engine-room aft (the mesh asset is cached at 48 m)
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

        /// <summary>The M3 water for a scene: its colour script (see Source/INSIDE_NOTES.md).</summary>
        static Material LitMat(string name, Color c, float metal, float smooth, Color emission = default)
        {
            string path = VerneBootstrap.Generated + "/Materials/M_" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            if (m == null) { m = new Material(lit); AssetDatabase.CreateAsset(m, path); }
            m.shader = lit;
            m.SetColor("_BaseColor", c); m.SetFloat("_Metallic", metal); m.SetFloat("_Smoothness", smooth);
            if (emission.maxColorComponent > 0f) { m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", emission); }
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            return m;
        }

        /// <summary>M4 fauna, first pass: the schools of I.XVI, the medusae "of opal or rose-pink, escalloped with a band of blue",
        /// and two tintoreas passing in the dark of the gallery.</summary>
        static void CrespoFauna(Transform root)
        {
            var fauna = new GameObject("Fauna of Crespo").transform; fauna.SetParent(root, false);
            Vector3 W(float x, float h, float z) => new Vector3(x, GroundAt(new Vector3(x, 0, z)) + h, z);
            FishSchool School(string name, FishSchool.Kind kind, Material m, int n, float size, float speed, float spread, params Vector3[] wps)
            {
                var go = new GameObject(name); go.transform.SetParent(fauna, false); go.transform.position = wps[0];
                var f = go.AddComponent<FishSchool>();
                f.kind = kind; f.material = m; f.count = n; f.size = size; f.speed = speed; f.spread = spread; f.waypoints = wps;
                return f;
            }
            var silver = LitMat("Fish_Silver", new Color(0.72f, 0.78f, 0.82f), 0.55f, 0.8f);
            var gold = LitMat("Fish_Gold", new Color(0.95f, 0.72f, 0.12f), 0.2f, 0.6f);
            var blue = LitMat("Fish_Blue", new Color(0.18f, 0.32f, 0.78f), 0.3f, 0.7f);
            var red = LitMat("Fish_Red", new Color(0.88f, 0.22f, 0.1f), 0.1f, 0.6f);
            var shark = LitMat("Fish_Tintorea", new Color(0.22f, 0.24f, 0.27f), 0.1f, 0.4f);
            var medusa = LitMat("Medusa", new Color(0.95f, 0.62f, 0.72f), 0f, 0.85f, new Color(0.08f, 0.14f, 0.35f));
            School("Little fishes (plain)", FishSchool.Kind.Fish, silver, 36, 0.2f, 1.4f, 2.6f, W(-8, 2, 10), W(8, 3, 18), W(5, 2.2f, 30), W(-6, 3, 24));
            School("Fish-flies (prairie)", FishSchool.Kind.Fish, blue, 24, 0.16f, 2.2f, 1.8f, W(-3, 1.2f, 32), W(6, 1.5f, 40), W(-5, 1.2f, 46), W(2, 1.8f, 36));
            School("Lepisacanthi (forest)", FishSchool.Kind.Fish, gold, 18, 0.26f, 1.0f, 2.0f, W(0, 2.5f, 50), W(9, 3, 62), W(-8, 3.5f, 74), W(3, 2.5f, 88));
            School("Red fish (gallery)", FishSchool.Kind.Fish, red, 16, 0.22f, 0.9f, 1.6f, W(-3, 1.4f, 96), W(4, 1.6f, 100), W(-2, 1.2f, 104), W(5, 1.8f, 98));
            School("Medusae", FishSchool.Kind.Medusa, medusa, 9, 0.7f, 0.25f, 9f, W(0, 5.5f, 12), W(6, 6f, 26), W(-5, 5f, 40));
            // "porphitae ... with their collarettes of blue tentacles" and the physalides, floating just under the surface (I.XV):
            // seen looking up, dark discs against Snell's window
            var porpita = LitMat("Porpita", new Color(0.12f, 0.32f, 0.85f), 0f, 0.7f, new Color(0.02f, 0.10f, 0.45f));
            var physalia = LitMat("Physalia", new Color(0.55f, 0.45f, 0.95f), 0f, 0.9f, new Color(0.10f, 0.06f, 0.35f));
            float top = 9f - 0.6f;   // just under Mission I's surface (VerneWater surfaceY = 9)
            School("Porphitae (at the surface)", FishSchool.Kind.Floater, porpita, 14, 0.22f, 0.12f, 10f, new Vector3(-4, top, 8), new Vector3(6, top, 20), new Vector3(-6, top, 34));
            School("Physalides (at the surface)", FishSchool.Kind.Floater, physalia, 6, 0.45f, 0.1f, 12f, new Vector3(5, top, 14), new Vector3(-7, top, 28), new Vector3(4, top, 42));
            School("Tintoreas (sharks in the dark)", FishSchool.Kind.BigFish, shark, 2, 2.4f, 1.6f, 6f, W(-18, 2.5f, 82), W(16, 3.5f, 96), W(-14, 3f, 112), W(12, 2.5f, 74));
        }

        static Material SnowMaterial()
        {
            string path = VerneBootstrap.Generated + "/Materials/M_MarineSnow.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            var sh = Shader.Find("Universal Render Pipeline/Particles/Unlit");
            if (sh == null) return null;
            if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, path); }
            m.shader = sh;
            m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(VerneBootstrap.Root + "/Textures/snow_dot.png"));
            m.SetColor("_BaseColor", Color.white);
            m.SetFloat("_Surface", 1f); m.SetFloat("_Blend", 2f);   // transparent, additive
            m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.One); m.SetFloat("_ZWrite", 0f);
            m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.renderQueue = (int)RenderQueue.Transparent;
            m.SetOverrideTag("RenderType", "Transparent");
            EditorUtility.SetDirty(m);
            return m;
        }

        static VerneWater Water(string preset, params Light[] hero)
        {
            var w = new GameObject("Water (" + preset + ")").AddComponent<VerneWater>();
            var snow = new GameObject("Marine snow").AddComponent<MarineSnow>();
            snow.transform.SetParent(w.transform, false);
            snow.material = SnowMaterial();
            if (snow.material == null) { Object.DestroyImmediate(snow.gameObject); Notes.Add("Particles/Unlit shader missing: no marine snow."); }
            switch (preset)
            {
                case "Title":       // the Nautilus resting in blue twilight, sun shafts through the swell
                    w.surfaceY = 24f; w.extinction = new Color(0.2f, 0.07f, 0.065f); w.scatterAlbedo = new Color(0.25f, 0.42f, 0.52f);   // cold, from the browser build
                    w.kd = new Color(0.14f, 0.05f, 0.045f); w.surfaceAmbient = new Color(0.05f, 0.09f, 0.1f); w.sunShafts = 2.2f; w.forwardScatter = 0.65f; w.maxDistance = 60f; break;
                case "Mission1":    // Crespo: five fathoms, clear and vibrant near the surface, darker down the slope
                    // tuned with Source/tools/preview_water_mock.py (Source/previews/m3_water_mock_Mission1.png): grey-green luminous fog,
                    // stems as silhouettes, red kept at five fathoms (Kd red 0.12) so the sand stays warm where the sun lands
                    w.surfaceY = 9f; w.extinction = new Color(0.106f, 0.067f, 0.061f); w.scatterAlbedo = new Color(0.25f, 0.46f, 0.57f);   // the browser build's σa+σs, σs/σt (GUM: "INSIDE, not Subnautica")
                    w.kd = new Color(0.12f, 0.045f, 0.04f); w.surfaceAmbient = new Color(0.06f, 0.11f, 0.12f); w.sunShafts = 2.5f; w.forwardScatter = 0.65f; w.maxDistance = 50f; break;
                case "Mission2":    // 150 fathoms at midnight: no daylight; the volcano's red glow is the only light (art-directed so red carries)
                    w.surfaceY = 274f; w.extinction = new Color(0.012f, 0.014f, 0.016f); w.scatterAlbedo = new Color(0.28f, 0.35f, 0.40f);   // cold scatter: warm albedo made the whole night an orange-brown haze
                    w.kd = new Color(0.3f, 0.07f, 0.05f); w.surfaceAmbient = Color.black; w.sunShafts = 0f; w.maxDistance = 90f; w.heroGain = 1500f; w.forwardScatter = 0.45f; break;   // the city 100-200 m off must still read from the summit
            }
            foreach (var l in hero) if (l != null) w.heroLights.Add(l);
            if (w.sunShafts > 0f)
            {
                // fallback shafts: only drawn while the ray-marched pass is not (unsupported GPU or feature off)
                var sh = Shader.Find("Verne/ShaftCard");
                if (sh != null)
                {
                    string path = VerneBootstrap.Generated + "/Materials/M_ShaftCard_" + preset + ".mat";
                    var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                    if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, path); }
                    m.shader = sh;
                    var c = w.surfaceAmbient * 6f; c.a = 1f;
                    m.SetColor("_Color", c); m.SetFloat("_Intensity", 0.3f); m.enableInstancing = true;
                    EditorUtility.SetDirty(m);
                    var cards = new GameObject("Shaft cards (fallback)").AddComponent<ShaftCards>();
                    cards.transform.SetParent(w.transform, false);
                    cards.material = m;
                }
                else Notes.Add("Verne/ShaftCard shader missing: no fallback shafts.");
            }
            return w;
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
            Wall("Robing room aft, beside the cell", ship, new Vector2(x1, z1), new Vector2(3.2f, z1), 0, 2.4f, "IronPaint", new Opening(1.475f, 0.75f, 2.0f));
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
                suits = Box("The bench where the visitors are dressed", robing, new Vector3(1.0f, 0.9f, -14.72f), new Vector3(2.3f, 1.8f, 0.5f), "Greybox", 1f, true, null, false);
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
        static Mesh SeabedMesh(string key, float size, float step, float amp, float freq, int seed, System.Func<float, float, float> extra = null, float centreZ = 0f)
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
                    float x = -size * 0.5f + i * step, z = centreZ - size * 0.5f + j * step;
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

        static GameObject Seabed(Transform parent, float size, float step, float amp, float freq, string mat, int seed, System.Func<float, float, float> extra = null, string key = null, float centreZ = 0f)
        {
            var go = new GameObject("Sea floor");
            go.transform.SetParent(parent, false);
            var mesh = SeabedMesh(key ?? (mat + seed), size, step, amp, freq, seed, extra, centreZ);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            go.AddComponent<MeshRenderer>().sharedMaterial = Materials.Get(mat);
            go.AddComponent<MeshCollider>().sharedMesh = mesh;
            go.AddComponent<Surface>().kind = mat == "Sand" ? "sand" : "rock";
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI);
            return go;
        }

        /// <summary>The sea floor's height under p: only the "Sea floor" mesh counts (never a rock, a prop or a vault roof).</summary>
        static float GroundAt(Vector3 p)
        {
            Physics.SyncTransforms();
            var hits = Physics.RaycastAll(new Vector3(p.x, 400f, p.z), Vector3.down, 800f, ~0, QueryTriggerInteraction.Ignore);
            float best = float.NegativeInfinity, any = float.NegativeInfinity;
            foreach (var h in hits)
            {
                any = Mathf.Max(any, h.point.y);
                if (h.collider != null && h.collider.name == "Sea floor") best = Mathf.Max(best, h.point.y);
            }
            if (!float.IsNegativeInfinity(best)) return best;
            return float.IsNegativeInfinity(any) ? 0f : any;
        }

        static Material s_AoMat;
        /// <summary>
        /// Hand-placed contact shadow / AO under a thing, as Playdead did ("no global illumination or even automated AO"):
        /// a URP decal projecting a soft dark blob straight down.
        /// </summary>
        /// <summary>(M4) A NavMesh over the scene's colliders (sea floor, rocks, stems, the hull), saved as an asset with the scene.</summary>
        static void BakeNavMesh(GameObject host, string key)
        {
            Physics.SyncTransforms();
            var surf = host.AddComponent<Unity.AI.Navigation.NavMeshSurface>();
            surf.collectObjects = Unity.AI.Navigation.CollectObjects.All;
            surf.useGeometry = UnityEngine.AI.NavMeshCollectGeometry.PhysicsColliders;
            surf.layerMask = ~((1 << 2) | (1 << ProjectSetup.InteractableLayer));
            surf.minRegionArea = 4f;
            surf.overrideVoxelSize = true; surf.voxelSize = 0.3f;       // coarse enough to bake in seconds on a laptop, fine enough for 0.5 m agents
            surf.BuildNavMesh();
            if (surf.navMeshData == null) { Notes.Add("NavMesh bake failed for " + key + ": divers walk straight legs."); return; }
            string path = VerneBootstrap.Generated + "/NavMesh_" + key + ".asset";
            if (AssetDatabase.LoadAssetAtPath<UnityEngine.AI.NavMeshData>(path) != null) AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(surf.navMeshData, path);
            var tri = UnityEngine.AI.NavMesh.CalculateTriangulation();
            Notes.Add($"NavMesh {key}: {tri.indices.Length / 3} triangles.");
        }

        static Material AoMaterial()
        {
            if (s_AoMat == null)
            {
                var sh = AssetDatabase.LoadAssetAtPath<Shader>("Packages/com.unity.render-pipelines.universal/Shaders/Decal.shadergraph");
                if (sh == null) return null;
                string path = VerneBootstrap.Generated + "/Materials/M_DecalAO.mat";
                s_AoMat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (s_AoMat == null) { s_AoMat = new Material(sh); AssetDatabase.CreateAsset(s_AoMat, path); }
                s_AoMat.SetTexture("Base_Map", AssetDatabase.LoadAssetAtPath<Texture2D>(VerneBootstrap.Root + "/Textures/ao_blob.png"));
                s_AoMat.enableInstancing = true;
                EditorUtility.SetDirty(s_AoMat);
            }
            return s_AoMat;
        }

        /// <summary>INSIDE's torch shadows: a decal at every diver's feet (and the visitor's) that swings away from the lamps.</summary>
        static void LampShadows()
        {
            var m = AoMaterial();
            if (m == null) { Notes.Add("Decal shader missing: no lamp shadows."); return; }
            int n = 0;
            foreach (var d in Object.FindObjectsByType<DiverPuppet>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            { var ls = d.gameObject.AddComponent<LampShadow>(); ls.material = m; n++; }
            foreach (var sp in Object.FindObjectsByType<PlayerSpawn>(FindObjectsInactive.Include, FindObjectsSortMode.None)) { sp.shadowMaterial = m; n++; }
            Notes.Add($"Lamp-following contact shadows on {n} bodies.");
        }

        static void AoBlob(Transform parent, Vector3 worldPos, float w, float l, float yaw = 0f, float depth = 2f)
        {
            if (AoMaterial() == null) return;
            var go = new GameObject("AO decal");
            go.transform.SetParent(parent, false);
            go.transform.position = worldPos;   // centred on the ground: reaches above and below it
            go.transform.rotation = Quaternion.Euler(90f, yaw, 0f);     // projects along its +Z: straight down
            var d = go.AddComponent<DecalProjector>();
            d.material = s_AoMat;
            d.size = new Vector3(w, l, depth);
            d.pivot = Vector3.zero;
            d.fadeFactor = 1f;
            d.drawDistance = 60f;
        }

        static void Rocks(Transform parent, int count, float radius, int seed, string mat, float scale = 1f, System.Func<Vector3, bool> skip = null)
        {
            var rnd = new System.Random(seed);
            var root = new GameObject("Rocks").transform; root.SetParent(parent, false);
            for (int i = 0; i < count; i++)
            {
                float a = (float)rnd.NextDouble() * Mathf.PI * 2f, r = Mathf.Sqrt((float)rnd.NextDouble()) * radius;
                var p = new Vector3(Mathf.Cos(a) * r, 0, Mathf.Sin(a) * r);
                if (p.magnitude < 4f || (skip != null && skip(p))) continue;
                var s = new Vector3(0.6f + (float)rnd.NextDouble() * 2.2f, 0.4f + (float)rnd.NextDouble() * 1.6f, 0.6f + (float)rnd.NextDouble() * 2.2f) * scale;
                s = new Vector3(Mathf.Round(s.x * 2f) / 2f, Mathf.Round(s.y * 2f) / 2f, Mathf.Round(s.z * 2f) / 2f); // shared meshes
                var art = RockArt(root, rnd, mat == "Rock" ? null : mat, scale);
                if (art != null)
                {
                    // the Blender rock (Source/blender/seabed_rocks.py): base already sunk below 0, so it sits on the sand
                    float yaw = (float)rnd.NextDouble() * 360f;
                    art.transform.position = new Vector3(p.x, GroundAt(p), p.z);
                    art.transform.rotation = Quaternion.Euler(0f, yaw, 0f) * art.transform.rotation;
                    var b = art.GetComponent<MeshRenderer>().bounds;
                    AoBlob(root, new Vector3(p.x, GroundAt(p), p.z), b.size.x * 1.35f, b.size.z * 1.35f, 0f);
                    continue;
                }
                var go = Box("Rock " + i, root, p, s, mat, 1.2f, true, "rock");
                go.transform.position = new Vector3(p.x, GroundAt(p) + s.y * 0.3f, p.z);
                go.transform.rotation = Quaternion.Euler((float)rnd.NextDouble() * 20f, (float)rnd.NextDouble() * 360f, (float)rnd.NextDouble() * 20f);
                AoBlob(root, new Vector3(p.x, GroundAt(p), p.z), s.x * 1.7f, s.z * 1.7f, go.transform.eulerAngles.y);
            }
        }

        static readonly string[] s_RockNames = { "rock_boulder_a", "rock_boulder_b", "rock_boulder_c", "rock_slab_a", "rock_slab_b", "rock_outcrop_a", "rock_outcrop_b", "rock_pebbles" };
        static readonly float[] s_RockWeights = { 3, 3, 3, 2, 2, 1.2f, 1, 2 };

        /// <summary>One faceted Blender rock (Models/Seabed/Seabed_Rocks.fbx), or null if the FBX is missing (then the greybox box).
        /// <paramref name="overrideMat"/> repaints it (basalt for Atlantis); else it keeps its encrusted Blender materials.</summary>
        static GameObject RockArt(Transform parent, System.Random rnd, string overrideMat, float scale)
        {
            var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(VerneBootstrap.Root + "/Models/Seabed/Seabed_Rocks.fbx");
            if (fbx == null) return null;
            float total = 0f; foreach (var w in s_RockWeights) total += w;
            float pick = (float)rnd.NextDouble() * total; int k = 0;
            for (; k < s_RockWeights.Length - 1; k++) { pick -= s_RockWeights[k]; if (pick <= 0f) break; }
            Transform src = null;
            foreach (var t in fbx.GetComponentsInChildren<Transform>(true)) if (t.name == s_RockNames[k]) { src = t; break; }
            if (src == null || src.GetComponent<MeshFilter>() == null) return null;
            var go = Object.Instantiate(src.gameObject, parent);
            go.name = s_RockNames[k];
            go.transform.localScale = Vector3.one * scale * (0.7f + (float)rnd.NextDouble() * 0.9f);
            go.transform.rotation = src.rotation;
            var mr = go.GetComponent<MeshRenderer>();
            if (overrideMat != null)
            {
                var m = Materials.Get(overrideMat);
                var arr = mr.sharedMaterials; for (int i = 0; i < arr.Length; i++) arr[i] = m; mr.sharedMaterials = arr;
            }
            var mc = go.AddComponent<MeshCollider>();
            mc.sharedMesh = go.GetComponent<MeshFilter>().sharedMesh;   // 80–320 triangles: cheap and exact, so nothing walks into it
            go.AddComponent<Surface>().kind = "rock";
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OccluderStatic);
            return go;
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
            Ambient(new Color(0.07f, 0.15f, 0.17f), new Color(0.03f, 0.07f, 0.08f), new Color(0.01f, 0.02f, 0.025f));
            Fog(true, new Color(0.03f, 0.09f, 0.10f), 0.03f);
            var sun = Sun("Sun (refracted)", new Vector3(58, 200, 0), new Color(0.9f, 0.97f, 0.92f), 1.8f);   // from ahead along the route: shafts and silhouettes
            Caustics(sun, 7f);
            var root = new GameObject("Crespo").transform;
            // the route runs north (+Z): sand plain → weed prairie → forest → coral gallery → glade
            Seabed(root, 240f, 2f, 3.5f, 0.025f, "Sand", 21, (x, z) => -Mathf.Clamp01((z - 40f) / 160f) * 18f);
            Rocks(root, 60, 110f, 22, "Rock");
            // M4: the Blender flora along the route; the greybox stand and cross only if the FBX is missing
            if (!CrespoFlora.Place(root, GroundAt))
            {
                KelpStand(root, new Vector3(0, 0, 70), 140, 26f, 23, "Greybox", 3f, 4.6f);
                var glade = new GameObject("Coral cemetery (placeholder)").transform; glade.SetParent(root, false);
                var gp = new Vector3(0, 0, 110);
                Box("Pedestal of rocks", glade, new Vector3(gp.x, GroundAt(gp) + 0.4f, gp.z), new Vector3(1.2f, 0.8f, 1.2f), "Rock", 1.2f, true, "rock");
                Box("Coral cross upright", glade, new Vector3(gp.x, GroundAt(gp) + 1.8f, gp.z), new Vector3(0.22f, 2.0f, 0.22f), "CoralRed");
                Box("Coral cross arms", glade, new Vector3(gp.x, GroundAt(gp) + 2.2f, gp.z), new Vector3(1.3f, 0.2f, 0.22f), "CoralRed");
            }
            NautilusAtTheDoor(root, SceneFlow.Nautilus);
            CrespoFauna(root);
            // clearings for the burial's actors and the sea-spider, then the NavMesh, before any diver exists
            foreach (var c in new[] { new Vector3(0, 0, 102.6f), new Vector3(0, 0, 104f), new Vector3(-1.6f, 0, 105.4f), new Vector3(1.0f, 0, 104.7f) }) CrespoFlora.ClearAround(c, 1.8f);
            CrespoFlora.ClearAround(new Vector3(2.4f, 0, 62f), 1.5f);
            BakeNavMesh(root.gameObject, "Mission1");
            // Captain Nemo leads, a crewman follows him (I.XV); the lamps are lit where the coral gallery darkens
            Vector3 G(float x, float z) => new Vector3(x, GroundAt(new Vector3(x, 0, z)), z);
            var nemo = Divers.Build(root, "Captain Nemo (diver)", G(0.6f, 5f), 0f, true, false, true);
            if (nemo != null)
            {
                var guide = nemo.gameObject.AddComponent<DiverGuide>();
                guide.waypoints = new[] { G(0.3f, 14f), G(0f, 30f), G(0f, 46f), G(0.2f, 70f), G(0f, 95f), G(-1.6f, 101f), G(-1.6f, 105.4f) };
                guide.lamp = nemo.GetComponentInChildren<Light>(true); guide.lampOnAfterZ = 92f;
                if (guide.lamp != null) guide.lamp.gameObject.AddComponent<LampBounce>();
                guide.lampLine = "“The light from our lamps produced sometimes magical effects, following the rough outlines of the natural arches and pendants disposed like lustres.” (L: your lamp)";
                guide.arrivedLine = "“Captain Nemo had stopped. We occupied, in this place, the centre of a vast glade surrounded by the lofty foliage of the submarine forest.”";
                var crew = Divers.Build(root, "A crewman with a pickaxe (diver)", G(-1.4f, 3.5f), 0f, true, false, false, true);
                if (crew != null)
                {
                    var g2 = crew.gameObject.AddComponent<DiverGuide>();
                    g2.waypoints = new[] { G(-1.1f, 12f), G(-0.9f, 28f), G(-0.9f, 44f), G(-1.0f, 68f), G(-1.0f, 93f), G(1.6f, 101f), G(1.0f, 104.7f) };
                    g2.lamp = crew.GetComponentInChildren<Light>(true); g2.lampOnAfterZ = 91f; g2.pace = 0.72f;
                    if (g2.lamp != null) g2.lamp.gameObject.AddComponent<LampBounce>();
                }
                // the burial (I.XXIV): four bearers waiting in the glade with the body on their shoulders, the grave to be dug
                var grave = G(0f, 104f);
                // Ned Land and Conseil walk with the Professor (I.XXIII: "Conseil hastened to accept it, and this time the Canadian seemed
                // quite ready to follow us"); they kneel with the others at the grave
                var companions = new List<DiverPuppet>();
                var ned = Divers.Build(root, "Ned Land (diver)", G(-1.8f, -0.5f), 0f, true, false, false);
                if (ned != null)
                {
                    var f = ned.gameObject.AddComponent<DiverFollower>(); f.slot = new Vector2(-1.7f, -2.2f); f.pace = 0.85f;
                    f.firstLine = "Ned Land, for once, had come without grumbling: no harpoon, no complaint, only the copper helmet nodding at my side.";
                    companions.Add(ned);
                }
                var conseil = Divers.Build(root, "Conseil (diver)", G(1.6f, -0.8f), 0f, true, false, false);
                if (conseil != null) { var f = conseil.gameObject.AddComponent<DiverFollower>(); f.slot = new Vector2(1.5f, -1.6f); f.pace = 0.85f; companions.Add(conseil); }
                foreach (var cpn in companions) { var cl = cpn.GetComponentInChildren<Light>(true); if (cl != null) cl.enabled = false; }   // lamps stay dark: URP's per-object light budget
                var bearers = new List<DiverPuppet>();
                foreach (var (bx, bz) in new[] { (-0.42f, 102.0f), (0.42f, 102.0f), (-0.42f, 103.2f), (0.42f, 103.2f) })
                {
                    var b = Divers.Build(root, "A bearer (diver)", G(bx, bz), 0f, true, false, false);
                    if (b != null) { bearers.Add(b); var bl = b.GetComponentInChildren<Light>(true); if (bl != null) bl.enabled = bearers.Count % 2 == 1; }   // two lit lamps of four: stay inside URP's per-object light limit
                }
                var rite = new GameObject("The burial (I.XXIV)").AddComponent<BurialRite>();
                rite.transform.SetParent(root, false);
                rite.nemo = guide; rite.digger = crew; rite.bearers = bearers.ToArray(); rite.grave = grave;
                rite.shroud = Divers.Shroud(root, G(0f, 102.6f) + Vector3.up * 1.72f);
                rite.mound = CrespoFlora.Spawn("grave_mound", grave, 0f);
                rite.companions = companions.ToArray();
                // the bearers walk the whole way at the back of the party, the body on their shoulders (I.XXIV)
                var proc = new GameObject("The bearers' procession (I.XXIV)").AddComponent<Procession>();
                proc.transform.SetParent(root, false);
                proc.transform.position = G(2.6f, 1.2f);
                proc.bearers = bearers.ToArray(); proc.shroud = rite.shroud;
                proc.waypoints = new[] { G(0.6f, 12f), G(0.2f, 30f), G(0.2f, 46f), G(0.4f, 70f), G(0.2f, 95f), G(0f, 99.5f), G(0f, 102.6f) };
                rite.procession = proc;
                // the sea-spider by the forest path (I.XVI), knocked over when the Captain passes
                var spider = Creatures.Spawn(root, "sea_spider", G(2.4f, 62f), 200f, 1f, true);
                if (spider != null) spider.AddComponent<SeaSpider>().nemo = nemo.transform;
                AoBlob(root, grave, 1.1f, 2.0f);   // the dark of the fresh grave
            }
            else Notes.Add("Diver parts FBX missing: no divers in Mission I.");
            var sp = new Vector3(0, 0, 0);
            Spawn(new Vector3(0, GroundAt(sp) + 0.1f, 0), 0f, MoveMode.Water, 200f);
            LampShadows();
            RouteAudit.Run("Mission I", root, new[] { G(0.3f, 6f), G(0.3f, 14f), G(0f, 30f), G(0f, 46f), G(0.2f, 70f), G(0f, 95f), G(-1.6f, 101f), G(-1.6f, 105.4f) });
            Water("Mission1");
            GlobalVolume("Mission1");
            Save(s, "Mission1");
        }

        // ------------------------------------------------------------------ Mission II
        public static void Mission2()
        {
            var s = NewScene("Mission2");
            // midnight at 150 fathoms; the only light is the volcano's red glow, two miles off
            Ambient(new Color(0.02f, 0.02f, 0.03f), new Color(0.015f, 0.01f, 0.012f), new Color(0.005f, 0.004f, 0.004f));
            Fog(true, new Color(0.012f, 0.014f, 0.02f), 0.012f);   // fallback only; thin enough that the glow and the city still show from the summit
            var root = new GameObject("Atlantis approach").transform;
            // (M5, started in Part 3) the stony plain → the climb through the petrified copse → the crevice → the first platform →
            // the summit (z 150, 60 m up) → the far side falling sheer, twice the height, to the drowned city (II.IX)
            Seabed(root, 520f, 2f, 2f, 0.03f, "Rock2", 31, AtlantisKit.Height, "Mission2", 140f);
            Rocks(root, 90, 120f, 32, "Basalt", 1.4f, p => Mathf.Abs(p.x) < 4f && p.z > 0f && p.z < 160f);   // the way and the crevice's approach kept clear
            bool kit = AtlantisKit.Place(root, GroundAt);
            if (!kit) KelpStand(root, new Vector3(0, 0, 70), 90, 22f, 33, "Basalt", 3f, 9f);   // greybox copse if the FBX is missing
            var glow = new GameObject("Volcano glow (beyond the summit)");
            glow.transform.SetParent(root, false);
            glow.transform.position = AtlantisKit.CraterGlow;
            var l = glow.AddComponent<Light>();
            l.type = LightType.Point; l.color = new Color(1f, 0.38f, 0.16f); l.intensity = 30f; l.range = 400f; l.shadows = LightShadows.None;
            NautilusAtTheDoor(root, SceneFlow.Nautilus);
            var sp = new Vector3(0, 0, 0);
            // Captain Nemo with his iron-pointed stick, no lamps ("They will be useless"), leading toward the red glow
            Vector3 G2(float x, float z) => new Vector3(x, GroundAt(new Vector3(x, 0, z)), z);
            BakeNavMesh(root.gameObject, "Mission2");
            var nemo2 = Divers.Build(root, "Captain Nemo (diver)", G2(0.8f, 5f), 0f, false, true, false);
            if (nemo2 != null)
            {
                var guide = nemo2.gameObject.AddComponent<DiverGuide>();
                guide.waypoints = new[] { G2(0.5f, 20f), G2(0f, 45f), G2(0.5f, 70f), G2(0f, 93f), G2(0f, 111f), G2(0f, 118f), G2(0.4f, 128f), G2(-1.8f, 150.2f) };   // over the trunk by its NavMeshLink
                guide.waitDistance = 10f; guide.pace = 0.7f;
                guide.arrivedLine = "“We had now arrived on the first platform, where other surprises awaited me.”";
            }
            // "the eyes of giant crustacea crouched in their holes" (II.IX): first placement, M5 refines it
            var rndC = new System.Random(77);
            for (int i = 0; i < 8; i++)
            {
                float side = i % 2 == 0 ? -1f : 1f;
                var cp = new Vector3(side * (4f + (float)rndC.NextDouble() * 5f), 0, 106f + i * 3f);   // past the crevice, below the first platform
                Creatures.Spawn(root, i % 3 == 0 ? "lobster_giant" : "crab_giant", G2(cp.x, cp.z), side > 0 ? -90f + (float)rndC.NextDouble() * 40f : 90f - (float)rndC.NextDouble() * 40f, 0.9f + (float)rndC.NextDouble() * 0.5f);
            }
            Spawn(new Vector3(0, GroundAt(sp) + 0.1f, 0), 0f, MoveMode.Water, 400f);
            // "Captain Nemo's strong hand hauled me back": a fall into the crevice or off the far side puts the visitor back on the path
            // II.IX in Aronnax's words, as the way unfolds
            var lines = new GameObject("The way, in the book's words (II.IX)").AddComponent<RouteLines>();
            lines.transform.SetParent(root, false);
            lines.lines = new[]
            {
                new RouteLines.Line { z = 6f, seconds = 7f, text = "“I heard a kind of pattering above my head. The noise redoubling, sometimes producing a continual shower ... It was rain falling violently, and crisping the surface of the waves.”" },
                new RouteLines.Line { z = 22f, seconds = 7f, text = "“A reddish spot, a sort of large light shining brilliantly about two miles from the Nautilus ... it did light our way, vaguely.”" },
                new RouteLines.Line { z = 52f, seconds = 8f, text = "“A copse of dead trees, without leaves, without sap, trees petrified by the action of the water and here and there overtopped by gigantic pines.”" },
                new RouteLines.Line { z = 92f, seconds = 7f, text = "“Now I jumped a crevice ... now I ventured on the unsteady trunk of a tree thrown across from one abyss to the other.”" },
                new RouteLines.Line { z = 108f, seconds = 8f, text = "“Millions of luminous spots shone brightly in the midst of the darkness. They were the eyes of giant crustacea crouched in their holes.”" },
                new RouteLines.Line { z = 122f, seconds = 8f, text = "“Vast heaps of stone, amongst which might be traced the vague and shadowy forms of castles and temples, clothed with a world of blossoming zoophytes.”" },
                new RouteLines.Line { z = 141f, seconds = 8f, text = "“My eyes ranged far over a large space lit by a violent fulguration. In fact, the mountain was a volcano.”" },
                new RouteLines.Line { z = 147f, seconds = 9f, text = "“There, indeed, under my eyes, ruined, destroyed, lay a town—its roofs open to the sky, its temples fallen, its arches dislocated, its columns lying on the ground.”" },
            };
            var fall = new GameObject("Falls (Nemo's hand)").AddComponent<FallRescue>();
            fall.transform.SetParent(root, false);
            if (kit) AtlantisKit.Summit(root, nemo2 != null ? nemo2.GetComponent<DiverGuide>() : null);
            LampShadows();
            RouteAudit.Run("Mission II", root, new[] { G2(0.5f, 6f), G2(0.5f, 20f), G2(0f, 45f), G2(0.5f, 70f), G2(0f, 93f), G2(0f, 111f), G2(0f, 118f), G2(0.4f, 128f), G2(-1.8f, 150.2f) });
            Water("Mission2", l);
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
            AoBlob(root, new Vector3(0f, g, -6.6f), 64f, 10f, 0f, 4f);   // the hull's contact shadow on the sand
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
                    foreach (var fc in root.GetComponentsInChildren<FloodingCell>(true))
                        if (fc.dogs == null) Notes.Add($"{n}: the cell's stopper-plate wheel is missing");
                    foreach (var st in root.GetComponentsInChildren<SuitStation>(true))
                        if (st.kitDress == null || st.kitReservoir == null || st.kitHelmet == null) Notes.Add($"{n}: the robing-room kit is incomplete (greybox suit station?)");
                    foreach (var sw in root.GetComponentsInChildren<SeaWindowView>(true))
                        if (sw.fishMaterial == null || sw.panels == null) { problems++; Notes.Add($"{n}: the saloon window view has a missing reference"); }
                    foreach (var ca in root.GetComponentsInChildren<ChapterAboard>(true))
                        if (ca.note == null || ca.cell == null || ca.seaDoor == null) { problems++; Notes.Add($"{n}: ChapterAboard has a missing reference"); }
                    int rot = root.GetComponentsInChildren<Rotator>(true).Length;
                    if (rot > 0) Notes.Add($"{n}: {rot} turning machine parts");
                }
                if (n.StartsWith("Mission") || n == "Title")
                {
                    var w = Object.FindObjectsByType<VerneWater>(FindObjectsSortMode.None);
                    if (w.Length == 0) Notes.Add($"{n}: no VerneWater (built-in fog only)");
                    else Notes.Add($"{n}: water '{w[0].name}', {w[0].heroLights.Count} hero light(s), surface at {w[0].surfaceY:0} m");
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
