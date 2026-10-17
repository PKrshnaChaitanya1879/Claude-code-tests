// DOM overlay: title, chapter cards, the crosshair and verb, Aronnax's thoughts, notes, pause.
import { bus } from './bus.js';

const $ = (sel, root = document) => root.querySelector(sel);

export class UI {
  constructor() {
    this.root = $('#ui');
    this.cross = $('#cross'); this.verb = $('#verb'); this.hold = $('#holdring');
    this.say = $('#say'); this.goal = $('#goal');
    this.card = $('#card'); this.note = $('#note'); this.pause = $('#pause'); this.title = $('#title');
    this.loading = $('#loading'); this.end = $('#end');
    this.sayTimer = 0; this.goalTimer = 0; this.queue = [];
    bus.on('say', (text, dur) => this.thought(text, dur));
  }
  setLoading(p, text) {
    this.loading.hidden = p >= 1;
    $('#loadbar').style.transform = `scaleX(${p})`;
    if (text) $('#loadtext').textContent = text;
  }
  showTitle(on) { this.title.hidden = !on; }
  crosshair(state, label = '', progress = 0) {
    this.cross.dataset.state = state;           // 'none' | 'dot' | 'ring'
    this.verb.textContent = label;
    this.verb.hidden = !label;
    this.hold.style.setProperty('--p', progress);
    this.hold.hidden = !(progress > 0);
  }
  thought(text, dur) {
    this.queue.push({ text, dur: dur ?? Math.max(3.5, text.length * 0.06) });
    if (this.sayTimer <= 0) this.nextThought();
  }
  clearThoughts() { this.queue.length = 0; this.sayTimer = 0; this.say.classList.remove('on'); this.goal.classList.remove('on'); this.goalTimer = 0; }
  nextThought() {
    const n = this.queue.shift();
    if (!n) { this.say.classList.remove('on'); return; }
    this.say.textContent = n.text; this.say.classList.add('on'); this.sayTimer = n.dur;
  }
  objective(text) { this.goal.textContent = text; this.goal.classList.add('on'); this.goalTimer = 6; this.lastGoal = text; }
  recallObjective() { if (this.lastGoal) { this.goal.classList.add('on'); this.goalTimer = 4; } }
  update(dt) {
    if (this.sayTimer > 0) { this.sayTimer -= dt; if (this.sayTimer <= 0) { this.say.classList.remove('on'); setTimeout(() => this.nextThought(), 500); } }
    if (this.goalTimer > 0) { this.goalTimer -= dt; if (this.goalTimer <= 0) this.goal.classList.remove('on'); }
  }
  chapterCard({ kicker, title, quote, cite, image }) {
    return new Promise((res) => {
      $('#cardKicker').textContent = kicker; $('#cardTitle').textContent = title;
      $('#cardQuote').textContent = quote; $('#cardCite').textContent = cite;
      $('#cardImg').src = image;
      this.card.hidden = false; this.card.classList.remove('out');
      const go = () => { this.card.classList.add('out'); setTimeout(() => { this.card.hidden = true; res(); }, 900); removeEventListener('keydown', key); };
      const key = (e) => { if (e.code === 'Space' || e.code === 'Enter') go(); };
      $('#cardGo').onclick = go; addEventListener('keydown', key);
    });
  }
  showNote({ head, body, sign }) {
    return new Promise((res) => {
      $('#noteHead').textContent = head; $('#noteBody').textContent = body; $('#noteSign').textContent = sign;
      this.note.hidden = false;
      const close = () => { this.note.hidden = true; removeEventListener('keydown', key); bus.emit('modalClosed'); res(); };
      const key = (e) => { if (['KeyE', 'Escape', 'Space', 'Enter'].includes(e.code)) { e.preventDefault(); close(); } };
      setTimeout(() => addEventListener('keydown', key), 200);
      $('#noteClose').onclick = close;
    });
  }
  showEnd({ title, lines, cite }) {
    $('#endTitle').textContent = title; $('#endLines').innerHTML = '';
    for (const l of lines) { const p = document.createElement('p'); p.textContent = l; $('#endLines').appendChild(p); }
    $('#endCite').textContent = cite;
    this.end.hidden = false;
  }
  hideEnd() { this.end.hidden = true; }
}
