// Sound, synthesised from physics rather than samples.
// In air: the Nautilus's electric hum, the 120-per-second screw, ventilation, rooms with their own
// reverberation, the sea heard through iron. In water: the ears are inside a copper ball, so the world
// is low-passed by the helmet; sound travels ~4.3x faster than in air so the two ears hear almost the
// same thing (direction is hard to tell: panning is narrowed); high frequencies are barely absorbed
// over these distances, so rain on the surface can still be heard far below. Breathing through the
// Rouquayrol regulator gets heavier with depth (the air you breathe is denser at 1 + depth/10 atm).
import { bus } from './bus.js';

const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

export class AudioEngine {
  constructor() { this.ctx = null; this.started = false; this.env = { medium: 'air', depth: 9, helmet: false, room: 'cabin' }; this.volume = 0.9; }

  start() {
    if (window.__noAudio) return;
    if (this.started) { this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = this.ctx = new AC();
    this.started = true;
    const sr = ctx.sampleRate;
    // shared noise buffers
    const mkBuf = (sec, fn) => { const b = ctx.createBuffer(2, Math.floor(sr * sec), sr); for (let ch = 0; ch < 2; ch++) { const d = b.getChannelData(ch); fn(d, ch); } return b; };
    this.white = mkBuf(4, (d) => { for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; });
    this.brown = mkBuf(6, (d) => { let l = 0; for (let i = 0; i < d.length; i++) { l = (l + 0.02 * (Math.random() * 2 - 1)) / 1.02; d[i] = l * 3.5; } });
    this.crackle = mkBuf(5, (d, ch) => { for (let i = 0; i < d.length; i++) d[i] = 0; for (let k = 0; k < 2600; k++) { const p = Math.floor(Math.random() * (d.length - 200)); const a = Math.random() * 0.9; for (let j = 0; j < 40; j++) d[p + j] += a * (Math.random() * 2 - 1) * Math.exp(-j / 6); } });
    // rain on the surface, heard from below: many tiny bubbles ringing at 10-20 kHz plus broadband splash
    this.rainBuf = mkBuf(6, (d) => {
      for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * 0.05;
      for (let k = 0; k < 9000; k++) {
        const p = Math.floor(Math.random() * (d.length - 800)); const f0 = 3000 + Math.random() * 9000; const a = 0.1 + Math.random() * 0.25; let ph = 0;
        for (let j = 0; j < 500; j++) { const f = f0 * (1 + j / 500 * 0.6); ph += 2 * Math.PI * f / sr; d[p + j] += a * Math.sin(ph) * Math.exp(-j / 90); }
      }
    });
    // master chain
    this.master = ctx.createGain(); this.master.gain.value = this.volume;
    const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -16; comp.ratio.value = 3; comp.knee.value = 12;
    this.master.connect(comp); comp.connect(ctx.destination);
    // world bus -> medium lowpass -> (dry, reverb sends)
    this.world = ctx.createGain();
    this.medLP = ctx.createBiquadFilter(); this.medLP.type = 'lowpass'; this.medLP.frequency.value = 18000; this.medLP.Q.value = 0.5;
    this.medShelf = ctx.createBiquadFilter(); this.medShelf.type = 'lowshelf'; this.medShelf.frequency.value = 220; this.medShelf.gain.value = 0;
    this.world.connect(this.medLP); this.medLP.connect(this.medShelf);
    this.dry = ctx.createGain(); this.medShelf.connect(this.dry); this.dry.connect(this.master);
    // two reverbs: rooms (air) and water
    const ir = (sec, decay, lp, bright = 1) => mkBuf(sec, (d) => { let l = 0; for (let i = 0; i < d.length; i++) { const t = i / sr; const n = Math.random() * 2 - 1; l += (n - l) * lp; d[i] = (l * (1 - bright) + n * bright) * Math.pow(1 - t / sec, decay) * Math.exp(-t * 2.0 / sec); } });
    // two convolvers only (cheap on old laptops): rooms of the Nautilus, and the open water
    this.revRoom = ctx.createConvolver(); this.revRoom.buffer = ir(1.3, 2.2, 0.35, 0.6);
    this.revWater = ctx.createConvolver(); this.revWater.buffer = ir(2.4, 1.6, 0.08, 0.1);
    this.sendRoom = ctx.createGain(); this.sendWater = ctx.createGain();
    this.sendSaloon = this.sendRoom; this.sendIron = this.sendRoom;
    for (const [s, r] of [[this.sendRoom, this.revRoom], [this.sendWater, this.revWater]]) {
      this.medShelf.connect(s); s.connect(r); r.connect(this.master); s.gain.value = 0;
    }
    // helmet: what you yourself make inside the copper ball (breath), small metal cavity resonance
    this.body = ctx.createGain(); this.body.gain.value = 1;
    this.helmetPeak = ctx.createBiquadFilter(); this.helmetPeak.type = 'peaking'; this.helmetPeak.frequency.value = 1150; this.helmetPeak.Q.value = 3; this.helmetPeak.gain.value = 0;
    const hd = ctx.createDelay(0.05); hd.delayTime.value = 0.0021; const hfb = ctx.createGain(); hfb.gain.value = 0.0;
    this.helmetFB = hfb;
    this.body.connect(this.helmetPeak); this.helmetPeak.connect(this.master);
    this.helmetPeak.connect(hd); hd.connect(hfb); hfb.connect(this.helmetPeak);
    // continuous beds
    this.beds = {};
    const bed = (name, buf, type, freq, q, gain = 0, dest = this.world, rate = 1) => {
      const s = ctx.createBufferSource(); s.buffer = buf; s.loop = true; s.playbackRate.value = rate;
      s.loopStart = Math.random() * 2; s.start(0, Math.random() * 2);
      const f = ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q;
      const g = ctx.createGain(); g.gain.value = gain;
      s.connect(f); f.connect(g); g.connect(dest);
      this.beds[name] = { src: s, f, g };
      return this.beds[name];
    };
    bed('vent', this.white, 'bandpass', 700, 0.6);
    bed('seaHull', this.brown, 'lowpass', 160, 0.7);
    bed('waterAmb', this.brown, 'lowpass', 420, 0.5);
    bed('swell', this.brown, 'lowpass', 90, 0.8);
    bed('reef', this.crackle, 'highpass', 1800, 0.5);
    bed('rain', this.rainBuf, 'lowpass', 6000, 0.4);
    bed('rumble', this.brown, 'lowpass', 55, 1.0, 0, this.world, 0.6);
    bed('lockHiss', this.white, 'bandpass', 2400, 0.8);
    bed('lockGurgle', this.brown, 'bandpass', 300, 2.5);
    // the Nautilus: electric hum and the screw (120 revolutions a second)
    this.humG = ctx.createGain(); this.humG.gain.value = 0; this.humG.connect(this.world);
    for (const [f, a] of [[50, 0.5], [100, 0.3], [150, 0.12], [200, 0.06]]) { const o = ctx.createOscillator(); o.frequency.value = f; const g = ctx.createGain(); g.gain.value = a; o.connect(g); g.connect(this.humG); o.start(); }
    this.screwG = ctx.createGain(); this.screwG.gain.value = 0; this.screwG.connect(this.world);
    const so = ctx.createOscillator(); so.type = 'triangle'; so.frequency.value = 120; const sf = ctx.createBiquadFilter(); sf.type = 'lowpass'; sf.frequency.value = 400; so.connect(sf); sf.connect(this.screwG); so.start();
    // Ruhmkorff coil buzz while the lamp burns
    this.coilG = ctx.createGain(); this.coilG.gain.value = 0; this.coilG.connect(this.body);
    const co = ctx.createOscillator(); co.type = 'sawtooth'; co.frequency.value = 140; const cf = ctx.createBiquadFilter(); cf.type = 'bandpass'; cf.frequency.value = 900; cf.Q.value = 2; co.connect(cf); cf.connect(this.coilG); co.start();
    // a pad for two moments of revelation
    this.padG = ctx.createGain(); this.padG.gain.value = 0; this.padG.connect(this.world); this.padG.connect(this.sendWater);
    this.padF = ctx.createBiquadFilter(); this.padF.type = 'lowpass'; this.padF.frequency.value = 600; this.padF.connect(this.padG);
    this.padOsc = [];
    for (const f of [55, 82.4, 110, 130.8, 164.8]) for (const det of [-4, 4]) { const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = f; o.detune.value = det; const g = ctx.createGain(); g.gain.value = 0.05; o.connect(g); g.connect(this.padF); o.start(); this.padOsc.push(o); }
    this.breath = { t: 0, phase: 'in', dur: 1.6, rate: 1 };
    this.listener = { pos: { x: 0, y: 0, z: 0 }, yaw: 0 };
    bus.on('sfx', (name, pos, opt) => this.sfx(name, pos, opt));
  }

  setVolume(v) { this.volume = v; if (this.master) this.master.gain.setTargetAtTime(v, this.ctx.currentTime, 0.1); }
  ramp(param, v, tc = 0.4) { if (!param) return; param.setTargetAtTime(v, this.ctx.currentTime, tc); }

  // env: { medium, depth, helmet, room, insideHull, panels, rain, volcano(0..1), reef(0..1), exertion, stress, engine, lockFlood, lockDrain, lamp }
  update(dt, env, listener) {
    if (!this.ctx) return;
    this.env = env; if (listener) this.listener = listener;
    const r = (p, v, tc) => this.ramp(p, v, tc);
    const water = env.medium === 'water';
    const depthAtm = 1 + (env.depth || 0) / 10;
    // what reaches the ears from the world
    if (water) {
      r(this.medLP.frequency, env.helmet ? 1500 : 900, 0.25);
      r(this.medShelf.gain, 6, 0.3);
    } else {
      r(this.medLP.frequency, env.helmet ? 2600 : env.lockFlood ? 5000 : 16000, 0.25);
      r(this.medShelf.gain, 0, 0.3);
    }
    r(this.helmetPeak.gain, env.helmet ? 5 : 0, 0.3);
    r(this.helmetFB.gain, env.helmet ? 0.35 : 0, 0.3);
    // reverbs
    const room = env.room || 'cabin';
    r(this.sendRoom.gain, water ? 0 : room === 'saloon' ? 0.4 : room === 'cabin' ? 0.22 : 0.3, 0.5);
    r(this.sendWater.gain, water ? 0.4 : 0, 0.5);
    // beds
    const B = this.beds;
    const inside = !water;
    r(B.vent.g.gain, inside ? (room === 'iron' ? 0.05 : 0.025) : 0, 0.6);
    r(B.seaHull.g.gain, inside ? 0.18 + (env.panels || 0) * 0.25 : 0, 0.8);
    r(this.humG.gain, inside ? (room === 'iron' ? 0.05 : 0.025) * (env.engine ?? 1) : 0.004 * (env.nearHull || 0), 0.8);
    r(this.screwG.gain, (env.screw || 0) * (inside ? 0.06 : 0.03), 1.0);
    const shallow = clamp(1 - (env.depth || 0) / 60, 0, 1);
    r(B.waterAmb.g.gain, water ? 0.22 + 0.25 * shallow : 0, 0.8);
    r(B.waterAmb.f.frequency, 220 + 500 * shallow, 1.0);
    r(B.swell.g.gain, water ? 0.35 * (0.4 + shallow) : 0, 1.0);
    r(B.reef.g.gain, water ? 0.05 * (env.reef || 0) : 0, 1.0);
    r(B.rain.g.gain, water ? 0.12 * (env.rain || 0) : 0, 1.5);
    r(B.rumble.g.gain, 0.9 * (env.volcano || 0), 0.8);
    r(B.lockHiss.g.gain, env.lockFlood ? 0.35 : 0, 0.15);
    r(B.lockHiss.f.frequency, 2400 - 1200 * (env.lockLevel || 0), 0.3);
    r(B.lockGurgle.g.gain, (env.lockFlood || env.lockDrain) ? 0.25 : 0, 0.3);
    r(B.lockGurgle.f.frequency, 180 + 600 * (env.lockLevel || 0), 0.3); // the air pocket shrinks: its resonance rises
    r(this.coilG.gain, env.lamp && water ? 0.008 : 0, 0.2);
    // breathing through the regulator
    if (env.helmet) this.updateBreath(dt, env, depthAtm);
  }

  updateBreath(dt, env, atm) {
    const b = this.breath;
    b.t += dt;
    const ex = clamp(env.exertion || 0, 0, 1), st = clamp(env.stress || 0, 0, 1);
    if (b.t >= b.dur) {
      b.t = 0;
      if (b.phase === 'in') { b.phase = 'out'; b.dur = (2.3 - ex * 0.9 - st * 0.6) * (0.9 + 0.1 * atm); this.exhale(b.dur, atm); }
      else if (b.phase === 'out') { b.phase = 'pause'; b.dur = 0.6 + Math.random() * 0.8 - ex * 0.4 - st * 0.3; }
      else { b.phase = 'in'; b.dur = (1.5 - ex * 0.5 - st * 0.3) * (0.95 + 0.05 * atm); this.inhale(b.dur, atm, ex); }
    }
  }
  inhale(dur, atm, ex) {
    const ctx = this.ctx, t = ctx.currentTime;
    // valve click as the tongue opens the inspirator
    this.click(this.body, 0.2, 2800, t);
    const s = ctx.createBufferSource(); s.buffer = this.white; s.start(t, Math.random() * 3);
    const f = ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 1500 / Math.sqrt(atm) + ex * 400; f.Q.value = 1.2;
    const g = ctx.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.11 + ex * 0.05, t + dur * 0.3); g.gain.linearRampToValueAtTime(0.0, t + dur);
    s.connect(f); f.connect(g); g.connect(this.body); s.stop(t + dur + 0.1);
  }
  exhale(dur, atm) {
    const ctx = this.ctx, t0 = ctx.currentTime;
    // foul air leaves through the expirator: a stream of bubbles that rattle past the helmet
    const n = Math.floor(14 + Math.random() * 10);
    for (let i = 0; i < n; i++) {
      const t = t0 + 0.05 + (i / n) * dur * 0.7 + Math.random() * 0.05;
      const rmm = 1.2 + Math.random() * 4; // bubble radius in mm -> Minnaert resonance ~3.3 kHz*mm / r
      this.bubble(this.body, 3300 / rmm * Math.sqrt(atm) * 0.5, 0.035 + Math.random() * 0.035, t, 0.08);
    }
    const s = ctx.createBufferSource(); s.buffer = this.brown; s.start(t0, Math.random() * 4);
    const f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 500; const g = ctx.createGain();
    g.gain.setValueAtTime(0, t0); g.gain.linearRampToValueAtTime(0.25, t0 + 0.2); g.gain.linearRampToValueAtTime(0, t0 + dur);
    s.connect(f); f.connect(g); g.connect(this.body); s.stop(t0 + dur + 0.1);
  }
  bubble(dest, f, dur, t, amp = 0.1) {
    const ctx = this.ctx; const o = ctx.createOscillator(); o.type = 'sine';
    o.frequency.setValueAtTime(f, t); o.frequency.exponentialRampToValueAtTime(f * 1.9, t + dur);
    const g = ctx.createGain(); g.gain.setValueAtTime(amp, t); g.gain.exponentialRampToValueAtTime(0.0005, t + dur);
    o.connect(g); g.connect(dest); o.start(t); o.stop(t + dur + 0.02);
  }
  click(dest, amp, freq, t) {
    const ctx = this.ctx; const s = ctx.createBufferSource(); s.buffer = this.white;
    const f = ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = freq; f.Q.value = 4;
    const g = ctx.createGain(); g.gain.setValueAtTime(amp, t); g.gain.exponentialRampToValueAtTime(0.0005, t + 0.03);
    s.connect(f); f.connect(g); g.connect(dest); s.start(t, Math.random() * 3); s.stop(t + 0.05);
  }
  noiseHit(dest, { buf = this.white, type = 'bandpass', f = 1000, q = 1, amp = 0.3, att = 0.002, dec = 0.2, t = this.ctx.currentTime, fEnd = null }) {
    const ctx = this.ctx; const s = ctx.createBufferSource(); s.buffer = buf;
    const fl = ctx.createBiquadFilter(); fl.type = type; fl.frequency.setValueAtTime(f, t); fl.Q.value = q;
    if (fEnd) fl.frequency.exponentialRampToValueAtTime(fEnd, t + att + dec);
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(amp, t + att); g.gain.exponentialRampToValueAtTime(0.0005, t + att + dec);
    s.connect(fl); fl.connect(g); g.connect(dest); s.start(t, Math.random() * 2); s.stop(t + att + dec + 0.05);
  }
  tone(dest, { f = 440, type = 'sine', amp = 0.2, att = 0.005, dec = 0.5, t = this.ctx.currentTime, fEnd = null }) {
    const ctx = this.ctx; const o = ctx.createOscillator(); o.type = type; o.frequency.setValueAtTime(f, t);
    if (fEnd) o.frequency.exponentialRampToValueAtTime(fEnd, t + att + dec);
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(amp, t + att); g.gain.exponentialRampToValueAtTime(0.0005, t + att + dec);
    o.connect(g); g.connect(dest); o.start(t); o.stop(t + att + dec + 0.05);
  }
  // positional output: gain by distance, narrow panning in water
  spatial(pos, ref = 3) {
    const ctx = this.ctx; const g = ctx.createGain(); const p = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    if (pos) {
      const L = this.listener; const dx = pos.x - L.pos.x, dy = pos.y - L.pos.y, dz = pos.z - L.pos.z;
      const d = Math.sqrt(dx * dx + dy * dy + dz * dz);
      g.gain.value = 1 / (1 + Math.max(0, d - 0.5) / ref);
      if (p) {
        const ang = Math.atan2(dx, -dz) + L.yaw; // relative
        const width = this.env.medium === 'water' ? 0.25 : 0.85;
        p.pan.value = clamp(Math.sin(ang) * width, -1, 1);
      }
    }
    if (p) { g.connect(p); p.connect(this.world); } else g.connect(this.world);
    return g;
  }

  step(surface, intensity = 1, water = false) {
    if (!this.ctx) return;
    const d = this.spatial(null); const t = this.ctx.currentTime; const a = 0.2 + 0.25 * intensity;
    if (water) {
      // lead soles: the step rings through the water and the body
      this.tone(d, { f: 70 + Math.random() * 25, amp: a * 0.9, dec: 0.18, fEnd: 45 });
      this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 300, amp: a * 0.6, dec: 0.12 });
      if (surface === 6 || surface === 7) this.noiseHit(d, { f: 1400, q: 3, amp: a * 0.25, dec: 0.06 });
      if (surface === 8) for (let i = 0; i < 4; i++) this.click(d, 0.08, 2500 + Math.random() * 2000, t + i * 0.012);
      this.tone(d, { f: 620 + Math.random() * 60, amp: a * 0.05, dec: 0.25 });
      return;
    }
    switch (surface) {
      case 1: this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 380, amp: a * 0.5, dec: 0.12 }); break;
      case 3: case 4:
        for (const f of [820, 1730, 2650]) this.noiseHit(d, { f, q: 18, amp: a * 0.35, dec: 0.25 + Math.random() * 0.1 });
        this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 500, amp: a * 0.4, dec: 0.08 }); break;
      default:
        this.tone(d, { f: 160 + Math.random() * 30, amp: a * 0.35, dec: 0.09 });
        this.noiseHit(d, { f: 900, q: 1.5, amp: a * 0.25, dec: 0.05 });
    }
  }

  sfx(name, pos, opt = {}) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    const d = this.spatial(pos, opt.ref || 3);
    switch (name) {
      case 'doorWood':
        this.noiseHit(d, { f: 1800, q: 6, amp: 0.25, dec: 0.04 });
        this.tone(d, { f: 110, amp: 0.15, dec: 0.3, t: t + 0.02 });
        this.noiseHit(d, { f: 600, q: 8, amp: 0.05, att: 0.2, dec: 0.5, fEnd: 900, t: t + 0.05 }); break;
      case 'doorIron':
        this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 300, amp: 0.6, dec: 0.4 });
        for (const f of [180, 433, 911, 1497]) this.noiseHit(d, { f, q: 25, amp: 0.3, dec: 1.2 });
        this.noiseHit(d, { f: 2500, q: 10, amp: 0.05, att: 0.3, dec: 0.4, t: t + 0.1 }); break;
      case 'doorLocked':
        for (let i = 0; i < 3; i++) { this.noiseHit(d, { f: 1200, q: 8, amp: 0.25, dec: 0.05, t: t + i * 0.09 }); this.tone(d, { f: 140, amp: 0.1, dec: 0.08, t: t + i * 0.09 }); } break;
      case 'switch': this.click(d, 0.5, 3000, t); this.tone(d, { f: 100, amp: 0.08, dec: 0.25, t: t + 0.01 }); break;
      case 'lever':
        for (let i = 0; i < 5; i++) this.click(d, 0.2, 2200, t + i * 0.035);
        this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 400, amp: 0.4, dec: 0.2, t: t + 0.2 }); break;
      case 'panels': {
        // the iron panels grind along their grooves in the hull
        const dur = 5.5;
        const s = this.ctx.createBufferSource(); s.buffer = this.brown; s.loop = true;
        const f = this.ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 220;
        const g = this.ctx.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.7, t + 0.4); g.gain.setValueAtTime(0.7, t + dur - 0.5); g.gain.linearRampToValueAtTime(0, t + dur);
        s.connect(f); f.connect(g); g.connect(d); s.start(t); s.stop(t + dur + 0.1);
        const s2 = this.ctx.createBufferSource(); s2.buffer = this.white; s2.loop = true;
        const f2 = this.ctx.createBiquadFilter(); f2.type = 'bandpass'; f2.frequency.value = 640; f2.Q.value = 12;
        const lfo = this.ctx.createOscillator(); lfo.frequency.value = 3.3; const lg = this.ctx.createGain(); lg.gain.value = 120; lfo.connect(lg); lg.connect(f2.frequency); lfo.start(t); lfo.stop(t + dur);
        const g2 = this.ctx.createGain(); g2.gain.setValueAtTime(0, t); g2.gain.linearRampToValueAtTime(0.12, t + 0.6); g2.gain.linearRampToValueAtTime(0, t + dur);
        s2.connect(f2); f2.connect(g2); g2.connect(d); s2.start(t); s2.stop(t + dur + 0.1);
        this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 250, amp: 0.8, dec: 0.6, t: t + dur }); break;
      }
      case 'ceilingOff': this.tone(d, { f: 60, amp: 0.1, dec: 0.6, fEnd: 30 }); this.click(d, 0.3, 4000, t); break;
      case 'valveTurn': for (let i = 0; i < 3; i++) this.noiseHit(d, { f: 1100 + i * 200, q: 15, amp: 0.15, dec: 0.15, t: t + i * 0.12 }); break;
      case 'pumps': for (let i = 0; i < 14; i++) { this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 160, amp: 0.5, dec: 0.25, t: t + i * 0.62 }); this.tone(d, { f: 55, amp: 0.15, dec: 0.3, t: t + i * 0.62 }); } break;
      case 'helmet':
        for (let i = 0; i < 9; i++) this.noiseHit(this.body, { f: 2600 + Math.random() * 600, q: 12, amp: 0.12, dec: 0.05, t: t + i * 0.11 });
        this.noiseHit(this.body, { buf: this.brown, type: 'lowpass', f: 500, amp: 0.6, dec: 0.4, t: t + 1.05 });
        for (const f of [740, 1480, 2210]) this.noiseHit(this.body, { f, q: 30, amp: 0.18, dec: 1.4, t: t + 1.05 }); break;
      case 'suit': for (let i = 0; i < 6; i++) this.noiseHit(d, { f: 500 + Math.random() * 1500, q: 6, amp: 0.12, att: 0.05, dec: 0.15, t: t + i * 0.18 }); break;
      case 'tank': this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 400, amp: 0.5, dec: 0.3 }); for (const f of [520, 1310]) this.noiseHit(d, { f, q: 20, amp: 0.2, dec: 0.8 }); this.noiseHit(d, { f: 4000, q: 1, amp: 0.15, att: 0.3, dec: 0.8, t: t + 0.3 }); break;
      case 'lamp': this.click(this.body, 0.3, 2500, t); this.noiseHit(this.body, { f: 5000, q: 2, amp: 0.08, dec: 0.2, t: t + 0.02 }); break;
      case 'stick': this.tone(d, { f: 1900 + Math.random() * 300, amp: 0.08, dec: 0.3 }); this.click(d, 0.12, 3500, t); break;
      case 'pickaxe':
        // iron striking flint at the bottom of the sea: rings, and is heard a long way
        for (const f of [1320, 2780, 4100]) this.tone(d, { f: f * (0.97 + Math.random() * 0.06), amp: 0.12, dec: 0.7 });
        this.noiseHit(d, { f: 3000, q: 2, amp: 0.25, dec: 0.05 });
        this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 300, amp: 0.3, dec: 0.2 }); break;
      case 'polyp': this.bubble(d, 900 + Math.random() * 500, 0.05, t, 0.06); break;
      case 'tremor':
        this.tone(d, { f: 28, amp: 0.9, att: 0.3, dec: 3.5, fEnd: 18 });
        this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 120, amp: 0.9, att: 0.2, dec: 3.0 });
        for (let i = 0; i < 25; i++) this.click(d, 0.06, 900 + Math.random() * 2500, t + 0.4 + Math.random() * 2.2); break;
      case 'steam': this.noiseHit(d, { f: 3000, q: 0.7, amp: 0.25, att: 0.3, dec: 1.5 }); for (let i = 0; i < 12; i++) this.click(d, 0.1, 1500 + Math.random() * 3000, t + Math.random() * 1.5); break;
      case 'claws': for (let i = 0; i < 3; i++) { this.click(d, 0.35, 2200 + Math.random() * 800, t + i * 0.13); this.tone(d, { f: 900, amp: 0.05, dec: 0.08, t: t + i * 0.13 }); } break;
      case 'chalk': for (let i = 0; i < 10; i++) this.noiseHit(d, { f: 3500 + Math.random() * 1500, q: 8, amp: 0.05, att: 0.02, dec: 0.08, t: t + i * 0.09 }); break;
      case 'rockfall': for (let i = 0; i < 10; i++) this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 250, amp: 0.4, dec: 0.3, t: t + i * 0.12 + Math.random() * 0.1 }); break;
      case 'splashIn': this.noiseHit(d, { f: 1200, q: 0.5, amp: 0.4, att: 0.05, dec: 1.2 }); for (let i = 0; i < 30; i++) this.bubble(d, 300 + Math.random() * 1200, 0.06, t + Math.random() * 1.2, 0.06); break;
      case 'ui': this.tone(d, { f: 660, amp: 0.05, dec: 0.12 }); break;
      case 'bump': this.noiseHit(d, { buf: this.brown, type: 'lowpass', f: 220, amp: 0.4, dec: 0.15 }); break;
    }
  }

  organNote(midi, dur = 1.6, vel = 0.5, pos) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime; const f0 = 440 * Math.pow(2, (midi - 69) / 12);
    const d = this.spatial(pos, 6);
    const g = this.ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(vel * 0.16, t + 0.06); g.gain.setValueAtTime(vel * 0.16, t + dur); g.gain.exponentialRampToValueAtTime(0.0005, t + dur + 0.9);
    g.connect(d); g.connect(this.sendSaloon);
    for (const [h, a] of [[1, 1], [2, 0.6], [3, 0.35], [4, 0.25], [6, 0.12], [8, 0.08]]) {
      const o = this.ctx.createOscillator(); o.frequency.value = f0 * h; o.detune.value = (Math.random() - 0.5) * 6;
      const og = this.ctx.createGain(); og.gain.value = a / h * 0.9; o.connect(og); og.connect(g); o.start(t); o.stop(t + dur + 1);
    }
    this.noiseHit(d, { f: f0 * 4, q: 3, amp: vel * 0.04, att: 0.01, dec: 0.08 });
  }
  pad(on, tc = 3) { if (this.padG) this.ramp(this.padG.gain, on ? 0.18 : 0, tc); }
}
