// The game: boot, title, the shared Nautilus sequence (note, wardrobe, dress, flooding cell),
// and the loop that ties the renderer, the body, the sound and the missions together.
import * as THREE from 'three';
import { Pipeline, QUALITY } from './pipeline.js';
import { UW, makeCausticTexture, depthAt } from './uw.js';
import { MarineSnow } from './particles.js';
import { Nautilus, b2t } from './nautilus.js';
import { Props } from './props.js';
import { World } from './collision.js';
import { Player, Input } from './player.js';
import { AudioEngine } from './audio.js';
import { UI } from './ui.js';
import { bus } from './bus.js';
import { Diver, DiverCrowd } from './npc.js';
import { MissionCoral } from './mission1.js';
import { MissionAtlantis } from './mission2.js';

const TMP = new THREE.Vector3();

export class Game {
  constructor() {
    this.mode = 'loading';
    this.t = 0;
    this.settings = { quality: 'medium', sens: 1, vol: 0.9, invert: false };
    try { Object.assign(this.settings, JSON.parse(localStorage.getItem('ttl-settings') || '{}')); } catch (e) {}
  }

  async boot() {
    const el = document.getElementById('game');
    const renderer = this.renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance', stencil: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setSize(el.clientWidth || innerWidth, el.clientHeight || innerHeight);
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    el.appendChild(renderer.domElement);
    this.pipe = new Pipeline(renderer);
    this.pipe.setQuality(QUALITY[this.settings.quality] || QUALITY.medium);
    this.resize();
    addEventListener('resize', () => this.resize());
    UW.uniforms.uCaustics.value = makeCausticTexture();

    this.ui = new UI();
    this.input = new Input(renderer.domElement);
    this.input.sensitivity = this.settings.sens; this.input.invertY = this.settings.invert;
    this.audio = new AudioEngine();
    this.camera = new THREE.PerspectiveCamera(72, innerWidth / innerHeight, 0.05, 520);
    this.ext = new THREE.Scene(); this.int = new THREE.Scene();
    this.snow = new MarineSnow(4200, 22);
    this.world = new World();
    this.player = new Player(this.camera, this.world, this.input);
    this.player.onStep = (s, k, ladder) => this.audio.step(s, k, this.player.medium === 'water');
    this.player.onLand = (s, k) => { if (k > 0.3) this.audio.step(s, 1, this.player.medium === 'water'); };

    // global exterior lights (fixed count so shaders never recompile)
    const sun = this.sun = new THREE.DirectionalLight(0xffffff, 1);
    sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
    const sc = sun.shadow.camera; sc.left = -45; sc.right = 45; sc.top = 45; sc.bottom = -45; sc.near = 1; sc.far = 160; sun.shadow.bias = -0.0006; sun.shadow.normalBias = 0.04;
    this.ext.add(sun, sun.target);
    const lamp = this.playerLamp = new THREE.SpotLight(0xeef3ff, 0, 0, 0.72, 0.55, 2);
    lamp.castShadow = true; lamp.userData.volumetric = 0.35; lamp.shadow.mapSize.set(512, 512); lamp.shadow.camera.near = 0.15; lamp.shadow.camera.far = 40; lamp.shadow.bias = -0.0008;
    this.ext.add(lamp, lamp.target);
    const nl = this.nemoLamp = new THREE.SpotLight(0xeef3ff, 0, 0, 0.75, 0.6, 2); nl.userData.volumetric = 0.45;
    this.ext.add(nl, nl.target);
    this.crewLights = [0, 1].map(() => { const p = new THREE.PointLight(0xe6eeff, 0, 0, 2); this.ext.add(p); return p; });
    this.volA = new THREE.SpotLight(0xff6a2a, 0, 0, 1.0, 0.7, 2); this.ext.add(this.volA, this.volA.target);
    this.volB = new THREE.SpotLight(0xff5a1e, 0, 0, 0.9, 0.5, 2); this.ext.add(this.volB, this.volB.target);
    this.volB.castShadow = true; this.volB.shadow.mapSize.set(1024, 1024); this.volB.shadow.camera.near = 2; this.volB.shadow.camera.far = 400; this.volB.shadow.bias = -0.0004;
    this.ext.add(this.camera);

    // assets
    this.ui.setLoading(0.05, 'Charging the Bunsen piles');
    let texTotal = 1, texDone = 0;
    THREE.DefaultLoadingManager.onProgress = (u, l, t) => { if (this.booted) return; texDone = l; texTotal = t; this.ui.setLoading(0.15 + 0.35 * (l / t), 'Lighting the luminous ceiling'); };
    this.nautilus = await new Nautilus().load('assets/nautilus.json');
    this.ui.setLoading(0.6, 'Filling the reservoirs with air');
    this.props = await new Props().load('assets/props.json');
    this.ui.setLoading(0.8, 'Opening the panels');
    this.int.add(this.nautilus.int); this.ext.add(this.nautilus.ext);
    this.intCrowd = new DiverCrowd(this.props, 3, false); this.int.add(this.intCrowd.group);
    this.crowd = new DiverCrowd(this.props, 18, true); this.ext.add(this.crowd.group);
    this.buildWardrobe();
    // what Aronnax carries: the iron-pointed stick in his gloved hand, the lamp hanging at his belt
    this.viewStick = new THREE.Group();
    const st = this.props.mesh('diver_stick', { shadow: false }); st.rotation.set(-0.22, 0, 0.08); st.position.set(0, -0.7, 0); this.viewStick.add(st);
    const fa = this.props.mesh('diver_forearm', { shadow: false }); fa.rotation.set(-1.45, 0.15, 0.25); fa.position.set(-0.02, 0.06, 0.34); this.viewStick.add(fa);
    this.viewStick.position.set(0.36, -0.5, -0.58); this.viewStick.visible = false;
    this.camera.add(this.viewStick);
    this.viewLamp = this.props.mesh('diver_lamp', { shadow: false }); this.viewLamp.visible = false; this.ext.add(this.viewLamp);
    this.bindUI();
    this.bindInteractions();
    await this.waitTextures();
    // title shows mission one's sea through the saloon window
    await this.loadMission(1, { title: true });
    this.booted = true;
    this.ui.setLoading(1);
    this.enterTitle();
    this.last = performance.now();
    renderer.setAnimationLoop(() => this.frame());
  }
  waitTextures() { return new Promise((res) => { const t = setTimeout(res, 9000); THREE.DefaultLoadingManager.onLoad = () => { clearTimeout(t); res(); }; if (THREE.Cache && 0) res(); }); }

  resize() {
    const w = innerWidth, h = innerHeight;
    this.renderer.setSize(w, h);
    const pr = this.renderer.getPixelRatio();
    this.pipe.setSize(w * pr, h * pr);
    if (this.camera) { this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); }
  }

  // ------------------------------------------------------------------ wardrobe props (interior)
  buildWardrobe() {
    const P = this.props; const grp = this.wardrobe = new THREE.Group();
    const at = (x, y, z) => b2t(x, y, z);
    const items = this.wardrobeItems = {};
    const make = (name, kind, pos, rot = 0, label) => {
      const m = P.mesh(name, { ext: false, shadow: false });
      m.position.copy(pos); m.rotation.y = rot;
      grp.add(m);
      if (kind) items[kind] = { obj: m, kind, label };
      return m;
    };
    // a dozen apparatuses hanging on the rail (dresses), helmets on the shelf
    for (let i = 0; i < 8; i++) {
      const x = -20.55 + i * 0.42;
      const suit = new THREE.Group();
      const t = P.mesh('diver_torso', { ext: false, shadow: false }); t.position.set(0, -0.6, 0); suit.add(t);
      const h = P.mesh('diver_hips', { ext: false, shadow: false }); h.position.set(0, -0.62, 0); suit.add(h);
      for (const s of [-1, 1]) {
        const th = P.mesh('diver_thigh', { ext: false, shadow: false }); th.position.set(0.1 * s, -0.72, 0); suit.add(th);
        const sn = P.mesh('diver_shin', { ext: false, shadow: false }); sn.position.set(0.1 * s, -1.13, 0.02); suit.add(sn);
        const ua = P.mesh('diver_upperarm', { ext: false, shadow: false }); ua.position.set(0.2 * s, -0.15, 0); ua.rotation.z = 0.1 * s; suit.add(ua);
      }
      suit.position.copy(at(x, -2.82, 2.0)); suit.rotation.y = 0;
      grp.add(suit);
      if (i === 5) items.suit = { obj: suit, kind: 'suit', label: 'Put on the diving dress' };
      const hm = make('diver_helmet', i === 5 ? 'helmet' : null, at(x, -2.92 + 0.15, 2.48), Math.PI, 'Put on the helmet');
    }
    make('diver_tank', 'tank', at(-18.6, -0.48, 0.47 + 0.25), Math.PI, 'Shoulder the reservoir');
    for (let k = 0; k < 3; k++) make('diver_lamp', k === 0 ? 'lamp' : null, at(-20.92, 0.6 + k * 0.28, 1.45), Math.PI / 2, 'Take a Ruhmkorff lamp');
    make('diver_stick', 'stick', at(-20.85, 1.75, 0.75), 0, 'Take the iron-pointed stick');
    items.stick.obj.rotation.z = 0.15;
    for (let k = 0; k < 2; k++) make('diver_gun', null, at(-20.9, 0.6 + k * 0.28, 1.25), Math.PI / 2);
    this.int.add(grp);
  }

  bindUI() {
    const $ = (id) => document.getElementById(id);
    $('m1').onclick = () => this.startMission(1);
    $('m2').onclick = () => this.startMission(2);
    $('tSettings').onclick = () => { this.openPause(true); };
    $('pResume').onclick = () => this.resume();
    $('pTitle').onclick = () => { this.ui.pause.hidden = true; this.enterTitle(); };
    $('eTitle').onclick = () => { this.ui.hideEnd(); this.enterTitle(); };
    $('eNext').onclick = () => { this.ui.hideEnd(); this.startMission(this.missionId === 1 ? 2 : 1); };
    const q = $('sQuality'), s = $('sSens'), v = $('sVol'), inv = $('sInv');
    q.value = this.settings.quality; s.value = this.settings.sens; v.value = this.settings.vol; inv.value = this.settings.invert ? '1' : '0';
    const save = () => { try { localStorage.setItem('ttl-settings', JSON.stringify(this.settings)); } catch (e) {} };
    q.onchange = () => { this.settings.userQuality = true; this.settings.quality = q.value; this.pipe.setQuality(QUALITY[q.value]); this.resize(); save(); };
    s.oninput = () => { this.settings.sens = +s.value; this.input.sensitivity = +s.value; save(); };
    v.oninput = () => { this.settings.vol = +v.value; this.audio.setVolume(+v.value); save(); };
    inv.onchange = () => { this.settings.invert = inv.value === '1'; this.input.invertY = this.settings.invert; save(); };
    document.addEventListener('pointerlockchange', () => {
      if (!document.pointerLockElement && this.mode === 'play' && !this.input.dragLook && !this.modal) this.openPause();
    });
    addEventListener('keydown', (e) => {
      if (e.code === 'Escape' && this.mode === 'play' && this.input.dragLook && !this.modal) this.openPause();
      if (e.code === 'Tab' && this.mode === 'play') { e.preventDefault(); this.ui.recallObjective(); }
    });
    this.renderer.domElement.addEventListener('click', () => { if (this.mode === 'play' && !this.input.locked && !this.modal) this.input.requestLock(); });
  }

  openPause(fromTitle = false) {
    this.prevMode = this.mode;
    if (!fromTitle) this.mode = 'paused';
    this.ui.pause.hidden = false;
    document.getElementById('pResume').textContent = fromTitle ? 'Close' : 'Resume';
    this.pauseFromTitle = fromTitle;
  }
  resume() {
    this.ui.pause.hidden = true;
    if (this.pauseFromTitle) return;
    this.mode = 'play'; this.input.requestLock();
  }

  enterTitle() {
    this.mode = 'title'; this.modal = false;
    if (document.pointerLockElement) document.exitPointerLock();
    this.ui.showTitle(true); this.ui.crosshair('none');
    this.titleT = 0;
    // a quiet establishing view: the saloon with its panels open on the sea
    const n = this.nautilus;
    n.state.ceiling = 0; n.state.ceilingVis = 0.0; n.state.panelsTarget = 1; n.state.panels = 1;
    this.player.medium = 'air'; this.helmet(false);
  }

  async startMission(id) {
    this.audio.start(); this.audio.setVolume(this.settings.vol);
    this.ui.showTitle(false); this.ui.clearThoughts();
    this.mode = 'card';
    const card = id === 1
      ? { kicker: 'Chapter One · Excursion I', title: 'The Coral Kingdom', quote: '“Here, there was no fine sand, no submarine prairies, no sea-forest. I immediately recognised that marvellous region in which, on that day, the Captain did the honours to us. It was the coral kingdom.”', cite: 'Part I, chapter XXIII', image: 'assets/ill/cemetery.jpg' }
      : { kicker: 'Chapter One · Excursion II', title: 'A Vanished Continent', quote: '“You have hitherto only visited the submarine depths by daylight, under the brightness of the sun. Would it suit you to see them in the darkness of the night?”', cite: 'Part II, chapter IX', image: 'assets/ill/atlantis.jpg' };
    const loading = this.loadMission(id);
    await this.ui.chapterCard(card);
    await loading;
    this.mission.start();
    this.mode = 'play';
    this.input.requestLock();
  }

  async loadMission(id, opts = {}) {
    if (this.mission && this.missionId === id && !opts.title && this.mission.reusable) { this.resetSequence(); this.mission.reset(); return; }
    if (this.mission) this.mission.dispose();
    this.missionId = id;
    this.world.parts.length = 0; this.world.dynamicOwners.length = 0;
    this.crowd.divers.length = 0; this.intCrowd.divers.length = 0; this.crowd.shrouds.length = 0;
    const M = id === 1 ? MissionCoral : MissionAtlantis;
    this.mission = new M(this);
    await this.mission.build();
    this.shadowTick = 0; this.cullDirty = true;
    this.nautilus.addColliders(this.world);
    this.world.build();
    this.resetSequence();
    if (!opts.title) this.mission.reset && this.mission.reset();
  }

  // ------------------------------------------------------------------ the sequence aboard
  resetSequence() {
    const n = this.nautilus;
    this.seq = { stage: 'cabin', suit: false, tank: false, lamp: false, stick: false, helmet: false, lock: 'open', lockLevel: 0, outside: false, holding: 0 };
    n.state.lockWater = 0; n.state.lockPressure = 1;
    for (const k in n.doors) { n.doors[k].target = 0; n.doors[k].open = 0; }
    n.setDoor('IA_door_lockInner', true); n.doors.IA_door_lockInner.open = 1;
    for (const k in this.wardrobeItems) this.wardrobeItems[k].obj.visible = true;
    this.helmet(false);
    this.player.setMedium('air'); this.player.speedScale = 1;
    this.lampOn = false; this.playerLamp.intensity = 0;
  }
  helmet(on) {
    this.helmetOn = on;
    this.pipe.finalMat.uniforms.uHelmet.value = on ? 1 : 0;
    this.pipe.finalMat.uniforms.uAberration.value = on ? 1 : 0;
  }

  bindInteractions() {
    bus.on('interact', (kind, entry) => this.onInteract(kind, entry));
    bus.on('modalClosed', () => { this.input.justPressed.clear(); this.coolUntil = performance.now() + 500; });
    bus.on('panels', (v) => this.audio.sfx('panels', this.nautilus.toWorld(b2t(9.55, 0, 2))));
    bus.on('ceiling', (v) => { if (!v) this.audio.sfx('ceilingOff'); });
  }

  onInteract(kind, entry) {
    const S = this.seq, n = this.nautilus;
    if (this.mission.onInteract && this.mission.onInteract(kind, entry)) return;
    const pos = entry.obj.getWorldPosition(new THREE.Vector3());
    switch (kind) {
      case 'note': this.mission.readNote(); return;
      case 'painting': bus.emit('say', `${entry.info.title} — ${entry.info.artist}.`); return;
      case 'instr_manometer': bus.emit('say', `The manometer: ${Math.round(n.state.depth)} metres of water above the hull, ${(1 + n.state.depth / 10).toFixed(1)} atmospheres.`); return;
      case 'instr_clock': { const h = n.state.clockHours ?? 10; bus.emit('say', `The electric clock, divided into twenty-four hours like the Italian clocks: ${Math.floor(h)} o’clock.`); return; }
      case 'instr_speed': bus.emit('say', n.state.speed > 0 ? `The speed dial: ${n.state.speed} miles an hour.` : 'The speed dial stands at nought. We are resting on the bottom.'); return;
      case 'instr_barometer': bus.emit('say', 'The barometer: it tells the weight of the air, and foretells the weather we never see.'); return;
      case 'instr_lockgauge': bus.emit('say', `The gauge of the cell: ${n.state.lockPressure.toFixed(1)} atmospheres.`); return;
      case 'organ': this.playOrgan(entry); return;
      case 'suit': if (!S.suit) { S.suit = true; entry.obj.visible = false; this.audio.sfx('suit', pos); this.dress('india-rubber dress'); } return;
      case 'tank':
        if (!S.suit) { bus.emit('say', 'First the dress.'); return; }
        S.tank = true; entry.obj.visible = false; this.audio.sfx('tank', pos); this.dress('reservoir'); return;
      case 'lamp':
        if (!S.tank) { bus.emit('say', 'The reservoir first, then the lamp.'); return; }
        S.lamp = true; entry.obj.visible = false; this.audio.sfx('lamp', pos); this.dress('lamp'); return;
      case 'stick':
        if (!S.tank) { bus.emit('say', 'The reservoir first.'); return; }
        S.stick = true; entry.obj.visible = false; this.audio.sfx('stick', pos); this.dress('stick'); return;
      case 'helmet': {
        const ready = S.suit && S.tank && (this.mission.needs === 'lamp' ? S.lamp : S.stick);
        if (!ready) { bus.emit('say', 'The helmet goes on last, when everything else is buckled.'); return; }
        S.helmet = true; entry.obj.visible = false; this.audio.sfx('helmet');
        bus.emit('say', 'The metal helmet was screwed upon the copper collar. Three holes, protected by thick glass, allowed me to see in all directions. The Rouquayrol apparatus began to act; I could breathe with ease.', 7);
        setTimeout(() => bus.emit('say', 'Imprisoned in these heavy garments, and glued to the deck by my leaden soles, it was nearly impossible for me to take a step.', 6), 7500);
        this.fadeTo(0.85, 0.5).then(() => { this.helmet(true); this.fadeTo(0, 1.2); });
        this.player.speedScale = 0.45;
        this.mission.onSuited && this.mission.onSuited();
        return;
      }
      case 'lockInner':
        if (!S.helmet) { bus.emit('say', 'Not without the diving dress.'); return; }
        if (!this.inCell()) { bus.emit('say', 'I must be inside the cell first.'); return; }
        if (!this.mission.nemoInCell || !this.mission.nemoInCell()) { bus.emit('say', 'Wait for the Captain.'); return; }
        if (S.lock === 'open') { n.setDoor('IA_door_lockInner', false); S.lock = 'closed'; this.audio.sfx('doorIron', pos); setTimeout(() => bus.emit('say', 'I heard a water-tight door close upon us, and we were wrapped in profound darkness.'), 1200); this.mission.onLockClosed && this.mission.onLockClosed(); }
        return;
      case 'lockOuter':
        if (S.lock !== 'flooded') { bus.emit('say', S.lock === 'flooding' ? 'Not until the cell is full.' : 'The sea is on the other side of that door.'); return; }
        n.setDoor('IA_door_lockOuter', true); S.lock = 'outerOpen'; this.audio.sfx('doorIron', pos, { ref: 6 });
        setTimeout(() => bus.emit('say', 'A second door cut in the side of the Nautilus then opened. We saw a faint light.'), 1500);
        this.mission.onOuterOpen && this.mission.onOuterOpen();
        return;
    }
  }
  dress(what) {
    this.fadeTo(0.5, 0.25).then(() => this.fadeTo(0, 0.5));
    const lines = {
      'india-rubber dress': 'Heavy and impervious clothes, made of india-rubber without seam. One would have thought it a suit of armour, both supple and resisting.',
      reservoir: 'The Rouquayrol apparatus: a reservoir of thick iron plates, fixed on the back by braces, like a soldier’s knapsack.',
      lamp: 'A Ruhmkorff lamp for the belt: a Bunsen pile, a wire, and a spiral glass holding a little carbonic gas.',
      stick: 'I felt them put an iron-pointed stick into my hand.',
    };
    if (lines[what]) bus.emit('say', lines[what], 5.5);
    const S = this.seq;
    const next = !S.tank ? 'Shoulder the Rouquayrol reservoir.' : this.mission.needs === 'lamp' && !S.lamp ? 'Take a Ruhmkorff lamp for the belt.' : this.mission.needs === 'stick' && !S.stick ? 'Take one of the iron-pointed sticks.' : !S.helmet ? 'The helmet last.' : '';
    if (next) this.ui.objective(next);
  }
  inCell() {
    const l = this.nautilus.localOf(this.player.pos);
    return l.x > -20.4 && l.x < -18.2 && l.z > -3.45 && l.z < -2.1;
  }
  playOrgan(entry) {
    // a few bars, as the captain played them alone at night
    const seq = [[69, 0.2], [67, 0.2], [69, 1.0], [67, 0.18], [65, 0.18], [64, 0.18], [62, 0.18], [61, 0.5], [62, 1.2], [57, 0.3], [55, 0.3], [57, 1.2]];
    let t = 0;
    const pos = entry.obj.getWorldPosition(new THREE.Vector3());
    for (const [m, d] of seq) { setTimeout(() => { this.audio.organNote(m, d + 0.1, 0.7, pos); this.audio.organNote(m - 12, d + 0.1, 0.5, pos); }, t * 1000); t += d; }
    bus.emit('say', 'Weber, Rossini, Mozart, Beethoven… “These musicians are the contemporaries of Orpheus,” he had said. “I am dead, Professor.”', 6);
  }
  fadeTo(v, sec) {
    return new Promise((res) => { this.fade = { from: this.pipe.finalMat.uniforms.uFade.value, to: v, t: 0, dur: sec, res }; });
  }

  // ------------------------------------------------------------------ debugging / photo mode
  async debugJump(id, z, opts = {}) {
    this.ui.showTitle(false); this.ui.clearThoughts();
    await this.loadMission(id);
    this.resetSequence(); this.mission.reset();
    const S = this.seq; S.suit = S.tank = S.helmet = true; S.lamp = id === 1; S.stick = id === 2;
    for (const k in this.wardrobeItems) this.wardrobeItems[k].obj.visible = false;
    this.helmet(true); S.lock = 'outerOpen'; S.lockLevel = 1; this.nautilus.setDoor('IA_door_lockOuter', true);
    const r = this.mission.route.atZ(z);
    this.player.teleport(new THREE.Vector3(r.x, r.y + 0.5, z), opts.yaw ?? 0, opts.pitch ?? 0);
    this.player.setMedium('water'); this.headMedium = 'water';
    this.mission.nemoState = 'drop'; this.mission.updateNemoAboard(0.01);
    this.mission.onOutside(); S.outside = true;
    this.mission.procession.s = r.s + (opts.ahead ?? 6);
    if (opts.lamps) { this.mission.lampsOn = true; this.lampOn = true; this.mission.triggers.gallery = 1; }
    this.mode = 'play'; this.pipe.finalMat.uniforms.uFade.value = 0; this.fade = null;
    return 'ok';
  }

  // ------------------------------------------------------------------ interaction picking
  pick() {
    const cam = this.camera; const rc = this.raycaster || (this.raycaster = new THREE.Raycaster());
    rc.setFromCamera({ x: 0, y: 0 }, cam);
    rc.far = this.player.medium === 'water' ? 3.0 : 2.4;
    const list = [];
    for (const e of this.nautilus.interactables()) list.push(e);
    for (const k in this.wardrobeItems) { const e = this.wardrobeItems[k]; if (e.obj.visible && this.mission.wants(k)) list.push(e); }
    if (this.mission.interactables) list.push(...this.mission.interactables());
    const objs = list.map((e) => e.obj).filter((o) => o.visible !== false);
    const hits = rc.intersectObjects(objs, true);
    if (!hits.length) return null;
    // find which entry owns the hit
    let o = hits[0].object;
    while (o) { const e = list.find((x) => x.obj === o); if (e) { e.dist = hits[0].distance; return e; } o = o.parent; }
    return null;
  }

  // ------------------------------------------------------------------ frame
  frame() {
    const now = performance.now(); let dt = Math.min(0.05, (now - this.last) / 1000) * (this.timeScale || 1); this.last = now;
    this.t += dt; UW.uniforms.uTime.value = this.t;
    const n = this.nautilus, P = this.player;
    if (this.fade) {
      const f = this.fade; f.t += dt; const k = Math.min(1, f.t / f.dur);
      this.pipe.finalMat.uniforms.uFade.value = f.from + (f.to - f.from) * k;
      if (k >= 1) { this.fade = null; f.res(); }
    }
    if (this.mode === 'title') {
      this.titleT += dt;
      const a = Math.sin(this.titleT * 0.05);
      this.camera.position.copy(n.toWorld(b2t(7.7 + Math.sin(this.titleT * 0.04) * 0.25, 0.9, 1.5 + Math.sin(this.titleT * 0.06) * 0.05)));
      const look = n.toWorld(b2t(8.95 + a * 0.35, 5.1, 1.35 + Math.sin(this.titleT * 0.09) * 0.1));
      this.camera.lookAt(look);
      if (this.pipe.finalMat.uniforms.uFade.value > 0 && !this.fade) this.fadeTo(0, 2.5);
      this.mission.update(dt, true);
    } else if (this.mode === 'play') {
      if (!this.modal) P.update(dt);
      this.updateSequence(dt);
      this.mission.update(dt, false);
      // interaction
      const e = this.modal ? null : this.pick();
      const E = this.input.pressed('KeyE') || (this.input.clicked && this.input.locked);
      if (e) {
        const hold = e.kind === 'valve';
        this.ui.crosshair('ring', e.label, hold ? this.seq.holding : 0);
        if (hold) {
          if (this.input.key('KeyE') || this.input.mouseDown) { this.seq.holding = Math.min(1, this.seq.holding + dt / 2.2); e.obj.rotation.x -= dt * 2.5; if (Math.random() < dt * 4) this.audio.sfx('valveTurn', e.obj.getWorldPosition(TMP)); }
          else this.seq.holding = Math.max(0, this.seq.holding - dt);
          if (this.seq.holding >= 1) { this.seq.holding = 0; this.startFlood(); }
        } else if (E && !(this.coolUntil > now)) {
          this.coolUntil = now + 350;
          n.interact(e, P);
        }
      } else {
        this.ui.crosshair(this.modal ? 'none' : 'dot');
        this.seq.holding = Math.max(0, this.seq.holding - dt);
      }
      if (this.input.pressed('KeyF') && this.seq.lamp && this.seq.helmet) this.toggleLamp();
      if (!this.input.locked && !this.input.dragLook && !this.modal) document.getElementById('clickToLook').hidden = false; else document.getElementById('clickToLook').hidden = true;
    }
    this.input.endFrame();
    this.autoQuality(now);
    // the Nautilus
    n.state.depth = this.mission.hullDepth ?? 9;
    n.update(dt, this.mode === 'title' ? this.camera.position : P.pos);
    this.world.refreshDynamic();
    this.crowd.update(dt, (x, z) => this.mission.ground(x, z));
    this.intCrowd.update(dt, null);
    this.updateLamp(dt);
    this.updateAudio(dt);
    this.ui.update(dt);
    this.render(dt);
  }

  // if the machine struggles, step the picture down once or twice (only when the player has not chosen)
  autoQuality(now) {
    if (this.mode !== 'play' || this.settings.userQuality || this.timeScale) { this.aq = null; return; }
    const a = this.aq || (this.aq = { t0: now, n: 0, wait: 2500 });
    if (now - a.t0 < a.wait) { a.n = 0; a.start = now; return; }
    a.n++;
    if (now - a.start > 4000) {
      const ms = (now - a.start) / a.n;
      const order = ['high', 'medium', 'low'];
      const i = order.indexOf(this.settings.quality);
      if (ms > 38 && i < 2) { this.settings.quality = order[i + 1]; this.pipe.setQuality(QUALITY[this.settings.quality]); this.resize(); document.getElementById('sQuality').value = this.settings.quality; }
      this.aq = { t0: now, n: 0, wait: 1500 };
      if (ms <= 38 || i >= 1) this.settings.userQuality = this.settings.userQuality || false, this.aqDone = (this.aqDone || 0) + 1;
      if (this.aqDone > 2) this.settings.userQuality = true;
    }
  }

  updateSequence(dt) {
    const S = this.seq, n = this.nautilus, P = this.player;
    if (S.lock === 'flooding') {
      S.lockLevel = Math.min(1, S.lockLevel + dt / 16);
      n.state.lockWater = S.lockLevel;
      n.state.lockPressure = 1 + (this.mission.outsideAtm - 1) * Math.pow(S.lockLevel, 3);
      if (S.lockLevel >= 1) { S.lock = 'flooded'; bus.emit('say', 'The cold mounted from my feet to my chest. The cell was full.'); this.ui.objective('Open the outer door.'); }
    }
    // which medium is the head in?
    const local = n.localOf(this.camera.position);
    const inBox = n.isInside(this.camera.position);
    const waterLine = S.lockLevel * 2.32;
    let medium = 'air';
    if (!inBox) medium = 'water';
    else if (this.inCell() && local.y > -0.2 && local.y < waterLine) medium = 'water';
    else if (this.inCell() && S.lock === 'outerOpen') medium = 'water';
    if (medium !== this.headMedium) {
      if (this.headMedium && medium === 'water') this.audio.sfx('splashIn');
      this.headMedium = medium;
    }
    const feetInWater = !inBox || (this.inCell() && (S.lock === 'outerOpen' || waterLine > 1.2));
    P.setMedium(feetInWater ? 'water' : 'air');
    this.pipe.compMat.uniforms.uLocalFog.value = inBox && medium === 'water' ? 1 : 0;
    if (!S.outside && !inBox && S.lock === 'outerOpen') { S.outside = true; this.mission.onOutside && this.mission.onOutside(); }
  }
  startFlood() {
    if (this.seq.lock !== 'closed') { bus.emit('say', this.seq.lock === 'open' ? 'The inner door is still open.' : ''); return; }
    this.seq.lock = 'flooding';
    bus.emit('say', 'A loud hissing was heard. They had given entrance to the water.');
    this.mission.onFlood && this.mission.onFlood();
  }
  toggleLamp() {
    this.lampOn = !this.lampOn;
    this.audio.sfx('lamp');
    if (this.lampOn && this.mission.onLamp) this.mission.onLamp();
  }
  updateLamp(dt) {
    const L = this.playerLamp, P = this.player;
    const on = this.lampOn && this.mode === 'play';
    this.lampLevel = (this.lampLevel || 0) + ((on ? 1 : 0) - (this.lampLevel || 0)) * Math.min(1, dt * (on ? 3 : 6));
    // the lamp hangs from the belt: light comes from the waist and follows the body, not the eyes
    const yaw = P.yaw; const pitch = THREE.MathUtils.clamp(P.pitch, -0.7, 0.25);
    this.lampYaw = this.lampYaw === undefined ? yaw : this.lampYaw + Math.atan2(Math.sin(yaw - this.lampYaw), Math.cos(yaw - this.lampYaw)) * Math.min(1, dt * 4);
    this.lampPitch = this.lampPitch === undefined ? pitch : this.lampPitch + (pitch - this.lampPitch) * Math.min(1, dt * 3);
    const fwd = new THREE.Vector3(-Math.sin(this.lampYaw) * Math.cos(this.lampPitch - 0.2), Math.sin(this.lampPitch - 0.2), -Math.cos(this.lampYaw) * Math.cos(this.lampPitch - 0.2));
    const right = new THREE.Vector3(Math.cos(this.lampYaw), 0, -Math.sin(this.lampYaw));
    L.position.set(P.pos.x, P.pos.y + 1.0 + P.crouch * -0.3, P.pos.z).addScaledVector(right, 0.18).addScaledVector(fwd, 0.15);
    L.target.position.copy(L.position).add(fwd);
    L.intensity = 340 * this.lampLevel * (0.97 + Math.sin(this.t * 37) * 0.015 + Math.sin(this.t * 13.3) * 0.01);
    L.target.updateMatrixWorld();
    const outsideKit = this.mode === 'play' && this.helmetOn && this.headMedium === 'water';
    this.viewStick.visible = outsideKit && this.seq.stick;
    if (this.viewStick.visible) {
      const sp = Math.hypot(P.vel.x, P.vel.z);
      this.viewStick.position.set(0.36 + Math.cos(P.bobT) * 0.012 * sp, -0.5 + Math.abs(Math.sin(P.bobT)) * 0.02 * sp, -0.58);
      this.viewStick.rotation.x = Math.sin(P.bobT) * 0.05 * sp;
    }
    this.viewLamp.visible = outsideKit && this.seq.lamp;
    if (this.viewLamp.visible) { this.viewLamp.position.copy(L.position).add(new THREE.Vector3(0, 0.12, 0)); this.viewLamp.rotation.set(Math.sin(this.t * 1.7) * 0.1, this.lampYaw, Math.cos(this.t * 1.3) * 0.08); }
  }
  updateAudio(dt) {
    const P = this.player, S = this.seq, n = this.nautilus;
    const water = this.headMedium === 'water' || this.mode === 'title' && false;
    const local = n.localOf(this.camera.position);
    let room = 'cabin';
    if (local.x > 5 && local.x < 14.1 && local.z > -2.9 && local.z < 2.9) room = 'saloon';
    else if (local.x < 0.4 || (local.z < -2.0 && local.x > 14.2)) room = 'iron';
    if (this.inCell()) room = 'lock';
    const depth = water ? depthAt(this.camera.position.y) : (this.mission.hullDepth ?? 9);
    const speed = Math.hypot(P.vel.x, P.vel.z);
    const env = {
      medium: this.mode === 'title' ? 'air' : (water ? 'water' : 'air'), depth, helmet: this.helmetOn && this.mode === 'play', room,
      panels: n.state.panels, engine: 1, screw: n.state.speed > 0 ? 1 : 0,
      lockFlood: S.lock === 'flooding', lockDrain: false, lockLevel: S.lockLevel,
      exertion: Math.min(1, speed / 1.4 + (P.ladder ? 0.6 : 0)), stress: this.mission.stress || 0, lamp: this.lampOn,
      ...(this.mission.audioEnv ? this.mission.audioEnv(water) : {}),
    };
    this.audio.update(dt, env, { pos: this.camera.position, yaw: P.yaw });
  }

  render(dt) {
    const n = this.nautilus, m = this.mission;
    // whole cells of scenery beyond the reach of the eye in this water are skipped
    if (!this.cullList || this.cullDirty) { this.cullList = []; this.ext.traverse((o) => { if (o.userData.cullable) this.cullList.push(o); }); this.cullDirty = false; }
    if ((this.shadowTick || 0) % 6 === 0) {
      const cp = this.camera.position, far = m.cullDistance || 80;
      for (const o of this.cullList) o.visible = o.userData.center.distanceTo(cp) - o.userData.radius < Math.min(far, o.userData.cull || 1e9);
    }
    // shadow maps are redrawn only when something that casts or receives them has moved
    const inside0 = n.isInside(this.camera.position);
    const SM = (l, on) => { l.shadow.autoUpdate = false; if (on) l.shadow.needsUpdate = true; };
    this.shadowTick = (this.shadowTick || 0) + 1;
    SM(this.playerLamp, this.lampLevel > 0.01 && !inside0);
    SM(n.lantern, this.shadowTick < 3 || this.shadowTick % 120 === 0);
    SM(this.volB, this.shadowTick < 3 || this.volB.shadow.needsUpdate);
    for (const b of n.beams) SM(b, inside0 && n.state.panels > 0.01 && (this.shadowTick % 12 === 0 || n.state.panelsMoving));
    // lights for the volumetric pass, most important first
    const inside = n.isInside(this.camera.position) && this.headMedium !== 'water';
    const spots = inside
      ? [...n.beams, n.lantern, ...n.windowLights]
      : [this.playerLamp, this.nemoLamp, ...(m.volumetricSpots ? m.volumetricSpots() : []), n.lantern, ...n.windowLights];
    const points = [];
    if (inside) { const pool = n.pool.filter((l) => l.intensity > 0).slice(0, 2); points.push(...pool); }
    points.push(...this.crewLights);
    this.snow.uniforms.uGlow.value = m.glow || 0;
    this.pipe.render({
      extScene: this.ext, intScene: this.int, camera: this.camera,
      air: n.airBox(), insideAir: inside,
      lights: { sun: m.sunOn ? this.sun : null, spots, points },
      particles: this.snow, current: m.current,
    }, dt, this.t);
  }
}
