/* Grvty — window logic */
"use strict";
const $ = (s, e = document) => e.querySelector(s), $$ = (s, e = document) => [...e.querySelectorAll(s)];
const G = window.gsap;
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const anim = () => G && !reduce;
const bridge = () => (window.pywebview && window.pywebview.api) || null;
const clone = (o) => JSON.parse(JSON.stringify(o));
const getPath = (o, p) => p.split(".").reduce((a, k) => a[k], o);
const setPath = (o, p, v) => { const ks = p.split("."), last = ks.pop(); ks.reduce((a, k) => a[k], o)[last] = v; };

const S = {
  schema: null, photos: [], current: null, params: {}, undo: {}, redo: {}, ticked: new Set(),
  view: "looks", looks: [], sel: -1, count: 12, prompt: "", busy: false, clipboard: null,
  info: {}, settings: { theme: "light", folder: "", open: ["light", "colour"] },
};
const P = () => S.params[S.current];
const defaults = () => clone(S.schema.defaults);

/* ───────────── server ───────────── */
async function post(route, body, blob = false) {
  const r = await fetch("/api/" + route, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.statusText);
  return blob ? r.blob() : r.json();
}
async function get(route) { const r = await fetch("/api/" + route); if (!r.ok) throw new Error(r.statusText); return r.json(); }
async function renderBlob(id, params, size) { return URL.createObjectURL(await post("render", { id, params, size }, true)); }

/* ───────────── images + ambient room ───────────── */
const IMG = new Map();
function loadImg(src) {
  if (!IMG.has(src)) IMG.set(src, new Promise((res) => { const im = new Image(); im.decoding = "async"; im.onload = () => (im.decode ? im.decode().catch(() => {}) : Promise.resolve()).then(() => res(im)); im.onerror = () => res(null); im.src = src; }));
  return IMG.get(src);
}
let ambientSrc = "";
async function setAmbient(src) {
  if (!src || src === ambientSrc) return; ambientSrc = src;
  const im = await loadImg(src); if (!im || src !== ambientSrc) return;
  const c = document.createElement("canvas"); c.width = 64; c.height = 40; c.className = "out";
  const x = c.getContext("2d"); x.filter = "blur(3px) saturate(1.5)"; x.drawImage(im, -6, -6, 76, 52);
  const amb = $("#ambient"), olds = $$("canvas", amb);
  amb.appendChild(c);
  requestAnimationFrame(() => requestAnimationFrame(() => { c.classList.remove("out"); olds.forEach((o) => o.classList.add("out")); }));
  setTimeout(() => olds.forEach((o) => o.remove()), 1000);
}

/* ───────────── theme ───────────── */
function setTheme(t, fromEl) {
  S.settings.theme = t; saveSettings();
  const apply = () => { document.documentElement.dataset.theme = t; syncDrops(); drawCurve(); drawHisto(); };
  if (!document.startViewTransition || reduce || !fromEl) return apply();
  const r = fromEl.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
  const end = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
  const vt = document.startViewTransition(apply);
  vt.ready.then(() => document.documentElement.animate({ clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${end}px at ${x}px ${y}px)`] },
    { duration: 700, easing: "cubic-bezier(.7,0,.2,1)", pseudoElement: "::view-transition-new(root)" }));
}

/* ───────────── liquid drop indicators ───────────── */
function moveDrop(group, btn, animate = true) {
  const drop = $(":scope > .drop", group); if (!drop || !btn || !group.offsetParent) return;
  const gr = group.getBoundingClientRect(), br = btn.getBoundingClientRect();
  const left0 = parseFloat(getComputedStyle(drop).left) || 0, x = br.left - gr.left - left0, w = br.width;
  if (!animate || !anim()) { if (G) G.set(drop, { x, width: w }); else { drop.style.transform = `translateX(${x}px)`; drop.style.width = w + "px"; } return; }
  const curX = G.getProperty(drop, "x"), curW = parseFloat(drop.style.width) || w;
  const minX = Math.min(curX, x), maxR = Math.max(curX + curW, x + w);
  G.timeline().to(drop, { x: minX, width: maxR - minX, scaleY: .86, duration: .2, ease: "power2.in" })
    .to(drop, { x, width: w, scaleY: 1, duration: .55, ease: "elastic.out(1, .55)" });
}
function syncDrops() {
  $$("[data-theme-pick]").forEach((b) => b.classList.toggle("on", b.dataset.themePick === (S.settings.theme || "light")));
  for (const g of $$(".tabs, .mode, .seg, .toggle, .subtabs")) moveDrop(g, $(":scope > button.on", g), false);
}
function wireSeg(group, onPick) {
  $$(":scope > button", group).forEach((b) => b.addEventListener("click", () => {
    if (b.disabled) return;
    if (onPick && onPick(b) === false) return;
    $$(":scope > button", group).forEach((x) => x.classList.toggle("on", x === b)); moveDrop(group, b);
  }));
}

/* ───────────── pointer light ───────────── */
const LIGHT = { items: [], x: -999, y: -999, queued: false };
function initLight() {
  LIGHT.items = $$(".glass").map((el) => {
    let sp = $(":scope > .spec", el);
    if (!sp) { sp = document.createElement("i"); sp.className = "spec"; sp.innerHTML = "<b></b>"; el.prepend(sp); }
    return { el, b: $("b", sp), r: null };
  });
  measureLight();
}
function measureLight() { for (const it of LIGHT.items) it.r = it.el.getBoundingClientRect(); }
function paintLight() {
  LIGHT.queued = false;
  for (const it of LIGHT.items) {
    const r = it.r; if (!r || !r.width) continue;
    const near = LIGHT.x > r.left - 260 && LIGHT.x < r.right + 260 && LIGHT.y > r.top - 260 && LIGHT.y < r.bottom + 260;
    if (!near && it.parked) continue;
    it.parked = !near;
    it.b.style.transform = near ? `translate3d(${LIGHT.x - r.left}px, ${LIGHT.y - r.top}px, 0)` : "translate3d(30%, -300px, 0)";
  }
}
addEventListener("pointermove", (e) => { LIGHT.x = e.clientX; LIGHT.y = e.clientY; if (!LIGHT.queued && !reduce) { LIGHT.queued = true; requestAnimationFrame(paintLight); } }, { passive: true });
addEventListener("resize", () => { measureLight(); syncDrops(); });
addEventListener("scroll", measureLight, { passive: true, capture: true });

/* ───────────── views ───────────── */
function updateChrome() {
  const has = S.photos.length > 0;
  $("#empty").hidden = has;
  $("#vLooks").hidden = !has || S.view !== "looks";
  $("#vEdit").hidden = !has || S.view !== "edit";
  $("#sideEmpty").hidden = has;
  $("#sideLooks").hidden = !has || S.view !== "looks";
  $("#sideEdit").hidden = !has || S.view !== "edit";
  $("#btnExport").disabled = !has;
  $$("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.view === S.view));
  const n = S.photos.length, t = S.ticked.size;
  $("#dockMeta").innerHTML = n ? `<b>${n} photo${n > 1 ? "s" : ""}</b>${t ? `${t} ticked` : "Tick to batch"}` : "<b>No photos yet</b>Add some to start";
  $("#applyLbl").textContent = t > 1 ? `Use on ${t} ticked photos` : "Use on this photo";
  $("#tickCount").textContent = t; $("#allCount").textContent = n;
}
function setView(v) {
  if (!S.photos.length) return;
  if (v === S.view && !$("#v" + (v === "looks" ? "Looks" : "Edit")).hidden) return;
  S.view = v;
  updateChrome();
  moveDrop($("#tabs"), $("#tabs button.on"));
  const show = v === "looks" ? ["#vLooks", "#sideLooks"] : ["#vEdit", "#sideEdit"];
  if (v === "edit") { refreshEdit(); requestRender(false); }
  if (v === "looks" && !S.looks.length) grade();
  if (anim()) G.fromTo(show.map((s) => $(s)), { opacity: 0, y: 14, scale: .985 }, { opacity: 1, y: 0, scale: 1, duration: .5, ease: "expo.out", stagger: .05, clearProps: "transform" });
  requestAnimationFrame(() => { syncDrops(); measureLight(); });
}

/* ───────────── LOOKS ───────────── */
function tileEl(look, k) {
  const t = document.createElement("div");
  t.className = "tile"; t.dataset.k = k;
  t.innerHTML = `<img src="${look.url}" alt="${look.name}" decoding="async"><span class="dev"></span><span class="glare"></span><span class="n">${k + 1}</span><span class="name">${look.name}</span><span class="heart"><svg viewBox="0 0 24 24"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg></span>`;
  t.addEventListener("click", () => select(k));
  t.addEventListener("dblclick", () => { select(k); tuneInEdit(); });
  if (anim()) {
    G.set(t, { transformPerspective: 900 });
    const rx = G.quickTo(t, "rotationX", { duration: .45, ease: "power3.out" }), ry = G.quickTo(t, "rotationY", { duration: .45, ease: "power3.out" });
    let rect = null, raf = 0, ev = null;
    t.addEventListener("pointerenter", () => { rect = t.getBoundingClientRect(); });
    t.addEventListener("pointermove", (e) => {
      if (S.busy) return; ev = e; if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0; if (!rect || !ev) return;
        const px = (ev.clientX - rect.left) / rect.width, py = (ev.clientY - rect.top) / rect.height;
        t.style.setProperty("--gx", px * 100 + "%"); t.style.setProperty("--gy", py * 100 + "%");
        ry((px - .5) * 9); rx((.5 - py) * 9);
      });
    });
    t.addEventListener("pointerleave", () => G.to(t, { rotationX: 0, rotationY: 0, duration: .8, ease: "elastic.out(1,.5)", overwrite: "auto" }));
  }
  return t;
}
function gridCols(n) { return n <= 4 ? 2 : n <= 9 ? (n <= 6 ? 3 : 4) : 4; }
function buildGrid() {
  const g = $("#grid"); g.innerHTML = "";
  g.style.setProperty("--cols", gridCols(S.looks.length));
  S.looks.forEach((l, k) => g.appendChild(tileEl(l, k)));
  markSel();
  return $$(".tile", g);
}
function markSel() {
  $$("#grid .tile").forEach((t) => t.classList.toggle("sel", +t.dataset.k === S.sel));
  $("#grid").classList.toggle("focus", S.sel >= 0);
}
async function renderLooks(list) {
  const id = S.current;
  let i = 0;
  const work = async () => { while (i < list.length) { const l = list[i++]; l.url = await renderBlob(id, l.params, "grid"); await loadImg(l.url); } };
  await Promise.all([work(), work(), work()]);
  return list;
}
function freeLooks(keep) { for (const l of S.looks) if (l.url && l !== keep && l.url.startsWith("blob:")) URL.revokeObjectURL(l.url); }

function dropIn(tiles) {
  if (!anim() || !tiles.length) return Promise.resolve();
  if (S.settings.theme === "dark") {
    const tl = G.timeline();
    tl.fromTo(tiles, { y: 24, scale: .97, opacity: 0 }, { y: 0, scale: 1, opacity: 1, duration: .7, ease: "expo.out", stagger: { each: .045, from: "center", grid: "auto" } }, 0);
    tl.fromTo(tiles.map((t) => $(".dev", t)), { opacity: .95 }, { opacity: 0, duration: 1.1, ease: "power2.out", stagger: { each: .045, from: "center", grid: "auto" } }, 0);
    return tl.then();
  }
  return G.fromTo(tiles, { y: -220, rotation: () => G.utils.random(-8, 8), opacity: 0 },
    { y: 0, rotation: 0, opacity: 1, duration: .95, ease: "bounce.out", stagger: { each: .04, from: "random" } }).then();
}
function fallAway(tiles) {
  if (!anim() || !tiles.length) return Promise.resolve();
  return G.to(tiles, { y: () => innerHeight * .8, rotation: () => G.utils.random(-22, 22), opacity: 0, duration: .42, ease: "power2.in", stagger: { each: .018, from: "random" } }).then();
}

async function grade() {
  if (S.busy || !S.current) return;
  S.busy = true; $("#btnGrade").classList.add("busy");
  try {
    S.prompt = $("#promptIn").value.trim();
    const listP = post("looks", { prompt: S.prompt, count: S.count }).then(renderLooks);
    const [list] = await Promise.all([listP, fallAway($$("#grid .tile"))]);
    freeLooks(); S.looks = list; S.sel = 0;
    const tiles = buildGrid(); showPick(0);
    $("#btnGrade").classList.remove("busy");
    await dropIn(tiles);
  } catch (e) { toast("Couldn't make looks: " + e.message); }
  $("#btnGrade").classList.remove("busy"); S.busy = false;
}

function select(k) {
  if (S.busy || !S.looks[k]) return;
  S.sel = k; markSel();
  const t = $(`#grid .tile[data-k="${k}"]`);
  if (t && anim()) G.fromTo(t, { scale: .94 }, { scale: 1, duration: .7, ease: "elastic.out(1,.45)" });
  showPick(k);
}
function showPick(k) {
  const L = S.looks[k]; if (!L) return;
  const img = $("#pickImg");
  if (anim() && img.src) G.timeline().to(img, { opacity: 0, scale: 1.04, duration: .14, overwrite: true }).add(() => { img.src = L.url; }).to(img, { opacity: 1, scale: 1, duration: .45, ease: "power3.out" });
  else img.src = L.url;
  $("#pickName").textContent = L.name;
  $("#pickTags").innerHTML = (L.tags.length ? L.tags : ["Natural"]).map((t) => `<span class="tag-pill">${t}</span>`).join("");
  if (anim()) {
    G.fromTo("#pickName", { y: 10, opacity: 0 }, { y: 0, opacity: 1, duration: .5, delay: .1, ease: "power3.out" });
    G.from("#pickTags .tag-pill", { y: 8, opacity: 0, scale: .9, duration: .45, stagger: .05, ease: "back.out(2)", delay: .15 });
  }
  setAmbient(L.url);
}
function chosen() { return S.looks[S.sel]; }
function recordPick() { const L = chosen(); if (L) post("pick", { prompt: S.prompt, params: L.params, shown: S.looks.length }).catch(() => {}); }

async function moreLikeThis() {
  const L = chosen(); if (S.busy || !L) return;
  S.busy = true; recordPick();
  const g = $("#grid"), sel = $(".tile.sel", g);
  try {
    const listP = post("looks", { around: L.params, count: S.count }).then((list) => { list[0].url = L.url; return renderLooks(list.slice(1)).then(() => list); });
    if (sel && anim()) {
      const sr = sel.getBoundingClientRect(), cx = sr.left + sr.width / 2, cy = sr.top + sr.height / 2;
      G.to(sel, { scale: 1.06, duration: .45, ease: "power2.out", yoyo: true, repeat: 1 });
      await G.to($$(".tile:not(.sel)", g), {
        x: (i, el) => { const r = el.getBoundingClientRect(); return cx - (r.left + r.width / 2); },
        y: (i, el) => { const r = el.getBoundingClientRect(); return cy - (r.top + r.height / 2); },
        scale: .12, rotation: () => G.utils.random(-140, 140), opacity: 0, duration: .6, ease: "power3.in", stagger: { each: .022, from: "edges" },
      }).then();
    }
    const list = await listP;
    list[0].name = L.name === "Closest match" ? "Your pick" : L.name;
    freeLooks(L); S.looks = list; S.sel = 0;
    const tiles = buildGrid(); showPick(0);
    const ns = $(".tile.sel", g);
    if (ns && anim()) {
      const nr = ns.getBoundingClientRect(), ncx = nr.left + nr.width / 2, ncy = nr.top + nr.height / 2;
      await G.from(tiles.filter((t) => t !== ns), {
        x: (i, el) => { const r = el.getBoundingClientRect(); return ncx - (r.left + r.width / 2); },
        y: (i, el) => { const r = el.getBoundingClientRect(); return ncy - (r.top + r.height / 2); },
        scale: .1, opacity: 0, rotation: () => G.utils.random(-60, 60), duration: .85, ease: "back.out(1.4)", stagger: { each: .03, from: "center" },
      }).then();
    }
  } catch (e) { toast("Couldn't make more looks: " + e.message); }
  S.busy = false;
}
function useLook(ids) {
  const L = chosen(); if (!L) return;
  for (const id of ids) { pushUndo(id); S.params[id] = clone(L.params); markEdited(id); refreshThumb(id); }
}
function tuneInEdit() { const L = chosen(); if (!L) return; recordPick(); useLook([S.current]); setView("edit"); }

/* ───────────── EDIT: controls ───────────── */
const HUE_COL = { red: "#E0413A", orange: "#EE8A2E", yellow: "#E8C734", green: "#4FB348", aqua: "#3CC0C4", blue: "#3B6FE0", purple: "#8A4FD8", magenta: "#D649B5" };
const HUE_NAME = { red: "Red", orange: "Orange", yellow: "Yellow", green: "Green", aqua: "Aqua", blue: "Blue", purple: "Purple", magenta: "Magenta" };
const ICON = {
  light: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>',
  colour: '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
  mixer: '<circle cx="8" cy="9" r="4"/><circle cx="16" cy="9" r="4"/><circle cx="12" cy="15" r="4"/>',
  grade: '<circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18"/>',
  curve: '<path d="M3 20C8 20 10 4 21 4"/>',
  presence: '<path d="M4 18l4-6 3 4 3-5 6 7z"/>',
  effects: '<circle cx="6" cy="6" r="1"/><circle cx="12" cy="8" r="1"/><circle cx="18" cy="5" r="1"/><circle cx="8" cy="13" r="1"/><circle cx="15" cy="14" r="1"/><circle cx="6" cy="19" r="1"/><circle cx="12" cy="18" r="1"/><circle cx="18" cy="19" r="1"/>',
};
const SECTIONS = [
  { id: "light", title: "Light", keys: ["exposure", "contrast", "highlights", "shadows", "whites", "blacks"] },
  { id: "colour", title: "Colour", keys: ["bw", "temp", "tint", "vibrance", "saturation"] },
  { id: "mixer", title: "Colour mixer", keys: ["hsl_hue", "hsl_sat", "hsl_lum", "bw_mix"] },
  { id: "grade", title: "Colour grading", keys: ["grade"] },
  { id: "curve", title: "Tone curve", keys: ["curve"] },
  { id: "presence", title: "Texture & clarity", keys: ["texture", "clarity"] },
  { id: "effects", title: "Vignette & grain", keys: ["vignette", "vignette_mid", "vignette_feather", "grain", "grain_size"] },
];
const sliders = [];

function makeSlider({ path, min = -100, max = 100, step = 1, dec = 0, track = null, onCommit, onChange, get, set, compact = false }) {
  const el = document.createElement("div");
  el.className = "slider" + (track ? " custom" : ""); el.tabIndex = 0; el.setAttribute("role", "slider");
  el.innerHTML = `<span class="trk"></span>${compact ? "" : '<span class="mid"></span>'}<span class="fill"></span><span class="lens"></span><span class="bub"></span>`;
  if (track) el.style.setProperty("--trk-bg", track);
  const lens = $(".lens", el), bub = $(".bub", el), fill = $(".fill", el);
  const zero = Math.max(min, Math.min(max, 0)), zp = (zero - min) / (max - min) * 100;
  el.style.setProperty("--zero", zp + "%");
  const getV = get || (() => getPath(P(), path)), setV = set || ((v) => setPath(P(), path, v));
  const fmt = (v) => (min < 0 && v > 0 ? "+" : "") + (+v).toFixed(dec);
  const s = { el, path, paint() {
    const v = getV(), p = (v - min) / (max - min) * 100;
    lens.style.left = p + "%"; bub.style.left = p + "%";
    fill.style.left = Math.min(p, zp) + "%"; fill.style.width = Math.abs(p - zp) + "%";
    bub.textContent = fmt(v); el.setAttribute("aria-valuenow", v);
    if (s.out) s.out.textContent = fmt(v);
    if (s.row) s.row.classList.toggle("ch", Math.abs(v - (s.def ?? 0)) > 1e-9);
  } };
  const fromX = (x) => {
    const r = el.getBoundingClientRect(); const p = Math.max(0, Math.min(1, (x - r.left) / r.width));
    let v = min + p * (max - min); v = Math.round(v / step) * step;
    if (min < 0 && Math.abs(v) < step * 2.5) v = 0;
    setV(+v.toFixed(dec)); s.paint(); (onChange || changed)(true);
  };
  el.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    el.setPointerCapture(e.pointerId); if (!onChange) beginChange();
    if (anim()) { G.to(lens, { scale: 1.35, duration: .35, ease: "back.out(3)" }); G.to(bub, { opacity: 1, scale: 1, y: -2, duration: .35, ease: "back.out(3)" }); }
    fromX(e.clientX);
    const mv = (ev) => fromX(ev.clientX);
    const up = () => {
      el.removeEventListener("pointermove", mv); el.removeEventListener("pointerup", up); el.removeEventListener("pointercancel", up);
      if (anim()) { G.to(lens, { scale: 1, duration: .6, ease: "elastic.out(1,.4)" }); G.to(bub, { opacity: 0, scale: .4, y: 0, duration: .25 }); }
      (onCommit || commitChange)();
    };
    el.addEventListener("pointermove", mv); el.addEventListener("pointerup", up); el.addEventListener("pointercancel", up);
  });
  el.addEventListener("dblclick", () => { if (!onChange) beginChange(); setV(s.def ?? zero); s.paint(); (onChange || changed)(false); (onCommit || commitChange)(); });
  el.addEventListener("keydown", (e) => {
    const d = step * (e.shiftKey ? 10 : 1); let v = getV();
    if (e.key === "ArrowRight" || e.key === "ArrowUp") v = Math.min(max, v + d);
    else if (e.key === "ArrowLeft" || e.key === "ArrowDown") v = Math.max(min, v - d);
    else return;
    e.preventDefault(); e.stopPropagation(); if (!onChange) beginChange(); setV(+v.toFixed(dec)); s.paint(); (onChange || changed)(false); (onCommit || commitChange)();
  });
  return s;
}
function row(label, opts, swatch) {
  const r = document.createElement("div"); r.className = "row";
  r.innerHTML = `<label>${swatch ? `<span class="sw" style="background:${swatch}"></span>` : ""}${label}</label><span class="v"></span>`;
  const s = makeSlider(opts); s.row = r; s.out = $(".v", r); s.def = opts.path ? getPath(S.schema.defaults, opts.path) : 0;
  r.insertBefore(s.el, s.out); sliders.push(s); return r;
}

function buildEditPanel() {
  const side = $("#sideEdit"); side.innerHTML = "";
  side.insertAdjacentHTML("beforeend", `<div style="display:grid;gap:8px"><div class="histo"><canvas id="histo" width="600" height="172"></canvas></div><div class="exif mono" id="exif"></div></div>`);
  for (const sec of SECTIONS) {
    const el = document.createElement("section");
    el.className = "sec" + (S.settings.open.includes(sec.id) ? "" : " closed"); el.dataset.id = sec.id;
    el.innerHTML = `<button class="sec-head"><span class="bubble-ico"><svg class="i" viewBox="0 0 24 24">${ICON[sec.id]}</svg></span><span class="t">${sec.title}</span><span class="dot"></span><span class="reset" role="button" tabindex="-1">Reset</span><svg class="i chev" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg></button><div class="sec-body"><div class="sec-inner"></div></div>`;
    const inner = $(".sec-inner", el);
    if (sec.id === "light") {
      inner.append(row("Exposure", { path: "exposure", min: -5, max: 5, step: .05, dec: 2 }), row("Contrast", { path: "contrast" }), row("Highlights", { path: "highlights" }),
        row("Shadows", { path: "shadows" }), row("Whites", { path: "whites" }), row("Blacks", { path: "blacks" }));
    }
    if (sec.id === "colour") {
      const t = document.createElement("div"); t.className = "toggle"; t.id = "bwToggle";
      t.innerHTML = `<span class="drop"></span><button data-v="colour" class="on">Colour</button><button data-v="bw">Black &amp; white</button>`;
      wireSeg(t, (b) => { beginChange(); P().bw = b.dataset.v === "bw"; refreshEdit(); changed(false); commitChange(); });
      inner.append(t, Object.assign(document.createElement("div"), { style: "height:6px" }));
      inner.append(row("Temperature", { path: "temp", track: "linear-gradient(90deg,#3E6FD8,#B9C3CF,#E9B23A)" }), row("Tint", { path: "tint", track: "linear-gradient(90deg,#46A54A,#C9C2C6,#C64BB0)" }));
      const v = row("Vibrance", { path: "vibrance" }), sa = row("Saturation", { path: "saturation" });
      v.classList.add("colour-only"); sa.classList.add("colour-only"); inner.append(v, sa);
    }
    if (sec.id === "mixer") buildMixer(inner);
    if (sec.id === "grade") buildGrade(inner);
    if (sec.id === "curve") buildCurve(inner);
    if (sec.id === "presence") inner.append(row("Texture", { path: "texture" }), row("Clarity", { path: "clarity" }));
    if (sec.id === "effects") {
      inner.append(row("Vignette", { path: "vignette" }), row("Midpoint", { path: "vignette_mid", min: 0, max: 100 }), row("Feather", { path: "vignette_feather", min: 0, max: 100 }),
        row("Grain", { path: "grain", min: 0, max: 100 }), row("Grain size", { path: "grain_size", min: 0, max: 100 }));
    }
    $(".sec-head", el).addEventListener("click", (e) => {
      if (e.target.closest(".reset")) {
        beginChange(); const d = defaults(); sec.keys.forEach((k) => { if (!(sec.id === "colour" && k === "bw")) P()[k] = clone(d[k]); });
        refreshEdit(); changed(false); commitChange(); return;
      }
      toggleSection(el);
    });
    side.appendChild(el);
  }
}
function toggleSection(el) {
  const body = $(".sec-body", el), open = el.classList.contains("closed");
  if (anim()) {
    if (open) { el.classList.remove("closed"); G.fromTo(body, { height: 0 }, { height: "auto", duration: .45, ease: "expo.out", onComplete: () => { body.style.height = ""; measureLight(); } }); requestAnimationFrame(() => { syncDrops(); drawCurve(); }); }
    else G.to(body, { height: 0, duration: .3, ease: "power2.in", onComplete: () => { el.classList.add("closed"); body.style.height = ""; measureLight(); } });
  } else { el.classList.toggle("closed"); }
  const id = el.dataset.id;
  S.settings.open = open ? [...new Set([...S.settings.open, id])] : S.settings.open.filter((x) => x !== id);
  saveSettings();
}
function buildMixer(inner) {
  const tabs = document.createElement("div"); tabs.className = "subtabs colour-only";
  tabs.innerHTML = `<span class="drop"></span><button data-t="hsl_hue">Hue</button><button data-t="hsl_sat" class="on">Saturation</button><button data-t="hsl_lum">Luminance</button>`;
  inner.appendChild(tabs);
  const groups = {}, hues = S.schema.hues;
  for (const g of ["hsl_hue", "hsl_sat", "hsl_lum", "bw_mix"]) {
    const wrap = document.createElement("div"); wrap.className = g === "bw_mix" ? "bw-only" : "colour-only"; wrap.style.cssText = "display:grid;gap:2px";
    hues.forEach((h, i) => {
      const c = HUE_COL[h]; let track;
      if (g === "hsl_hue") track = `linear-gradient(90deg,${HUE_COL[hues[(i + 7) % 8]]},${c},${HUE_COL[hues[(i + 1) % 8]]})`;
      if (g === "hsl_sat") track = `linear-gradient(90deg,#9A9A9A,${c})`;
      if (g === "hsl_lum") track = `linear-gradient(90deg,#1E1E1E,${c},#F4F4F4)`;
      if (g === "bw_mix") track = `linear-gradient(90deg,#1E1E1E,#F2F2F2)`;
      wrap.appendChild(row(HUE_NAME[h], { path: `${g}.${h}`, track }, c));
    });
    groups[g] = wrap; inner.appendChild(wrap);
  }
  const show = (t) => ["hsl_hue", "hsl_sat", "hsl_lum"].forEach((g) => (groups[g].dataset.tab = g === t ? "on" : "off"));
  wireSeg(tabs, (b) => { show(b.dataset.t); applyMode(); });
  show("hsl_sat");
  const hint = document.createElement("p"); hint.className = "hint bw-only"; hint.textContent = "Slide a colour to make it lighter or darker in black & white.";
  inner.appendChild(hint);
}

/* colour wheels */
const wheels = [];
function hsl2rgb(h, s, l) { const a = s * Math.min(l, 1 - l), f = (n) => { const k = (n + h / 30) % 12; return l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)); }; return [f(0) * 255, f(8) * 255, f(4) * 255]; }
function drawWheel(canvas) {
  const size = canvas.width, ctx = canvas.getContext("2d"), r = size / 2, img = ctx.createImageData(size, size);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const dx = x - r + .5, dy = y - r + .5, d = Math.hypot(dx, dy) / r, i = (y * size + x) * 4;
    if (d > 1) { img.data[i + 3] = 0; continue; }
    const hue = (Math.atan2(-dy, dx) * 180 / Math.PI + 360) % 360, [R, Gg, B] = hsl2rgb(hue, .85 * d, .62 - .12 * d * d);
    img.data[i] = R; img.data[i + 1] = Gg; img.data[i + 2] = B; img.data[i + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
}
function buildGrade(inner) {
  const box = document.createElement("div"); box.className = "wheels";
  for (const [zone, name] of [["shadows", "Shadows"], ["midtones", "Midtones"], ["highlights", "Highlights"]]) {
    const wb = document.createElement("div"); wb.className = "wheel-box";
    wb.innerHTML = `<div class="wheel"><canvas width="168" height="168"></canvas><div class="puck"></div></div><span class="wname">${name}</span>`;
    const wheel = $(".wheel", wb); drawWheel($("canvas", wb));
    const lum = makeSlider({ path: `grade.${zone}.lum`, compact: true, track: "linear-gradient(90deg,#1E1E1E,#F2F2F2)" }); lum.def = 0; sliders.push(lum);
    lum.el.title = "Brightness"; wb.appendChild(lum.el);
    wheels.push({ zone, wb, puck: $(".puck", wb) });
    const pick = (e) => {
      const r = wheel.getBoundingClientRect(), dx = e.clientX - r.left - r.width / 2, dy = e.clientY - r.top - r.height / 2;
      P().grade[zone].hue = Math.round((Math.atan2(-dy, dx) * 180 / Math.PI + 360) % 360);
      P().grade[zone].sat = Math.round(Math.min(1, Math.hypot(dx, dy) / (r.width / 2)) * 100);
      syncWheels(); changed(true);
    };
    wheel.addEventListener("pointerdown", (e) => {
      wheel.setPointerCapture(e.pointerId); beginChange(); pick(e);
      const mv = (ev) => pick(ev), up = () => { wheel.removeEventListener("pointermove", mv); wheel.removeEventListener("pointerup", up); commitChange(); };
      wheel.addEventListener("pointermove", mv); wheel.addEventListener("pointerup", up);
    });
    wheel.addEventListener("dblclick", () => { beginChange(); P().grade[zone].hue = 0; P().grade[zone].sat = 0; syncWheels(); changed(false); commitChange(); });
    box.appendChild(wb);
  }
  inner.append(box, row("Blending", { path: "grade.blending", min: 0, max: 100 }), row("Balance", { path: "grade.balance" }));
}
function syncWheels() {
  if (!P()) return;
  for (const w of wheels) {
    const g = P().grade[w.zone], a = g.hue * Math.PI / 180, r = g.sat / 100 * 50;
    w.puck.style.left = `${50 + r * Math.cos(a)}%`; w.puck.style.top = `${50 - r * Math.sin(a)}%`;
    w.puck.style.background = g.sat ? `hsl(${g.hue} 80% 55%)` : "#888";
    w.wb.classList.toggle("ch", g.sat > 0 || g.lum !== 0);
  }
}

/* tone curve */
let curve = null;
function buildCurve(inner) {
  const wrap = document.createElement("div"); wrap.className = "curve-wrap"; wrap.innerHTML = "<canvas></canvas>";
  inner.appendChild(wrap);
  const canvas = $("canvas", wrap);
  curve = { canvas, wrap, drag: -1 };
  inner.appendChild(row("Fade", {
    min: 0, max: 100, get: () => (P().curve[0][0] === 0 ? Math.round(P().curve[0][1] / .6) : 0),
    set: (v) => { P().curve[0] = [0, Math.round(v * .6)]; drawCurve(); },
  }));
  const hint = document.createElement("p"); hint.className = "hint"; hint.textContent = "Click to add a point, drag to shape, double-click a point to remove it.";
  inner.appendChild(hint);
  const toPt = (e) => { const r = canvas.getBoundingClientRect(); return [Math.max(0, Math.min(255, (e.clientX - r.left) / r.width * 255)), Math.max(0, Math.min(255, (1 - (e.clientY - r.top) / r.height) * 255))]; };
  const nearest = (p) => { let best = -1, bd = 1e9; P().curve.forEach((q, i) => { const d = Math.hypot(q[0] - p[0], q[1] - p[1]); if (d < bd) { bd = d; best = i; } }); return bd < 16 ? best : -1; };
  canvas.addEventListener("pointerdown", (e) => {
    beginChange(); const p = toPt(e), pts = P().curve; let i = nearest(p);
    if (i < 0) { const np = [Math.round(p[0]), Math.round(p[1])]; pts.push(np); pts.sort((a, b) => a[0] - b[0]); i = pts.indexOf(np); }
    curve.drag = i; canvas.setPointerCapture(e.pointerId); drawCurve(); changed(true);
  });
  canvas.addEventListener("pointermove", (e) => {
    if (curve.drag < 0) return;
    const pts = P().curve, i = curve.drag, p = toPt(e);
    const lo = i === 0 ? 0 : pts[i - 1][0] + 2, hi = i === pts.length - 1 ? 255 : pts[i + 1][0] - 2;
    pts[i] = [Math.round(Math.max(lo, Math.min(hi, p[0]))), Math.round(p[1])];
    drawCurve(); changed(true);
  });
  canvas.addEventListener("pointerup", () => { if (curve.drag >= 0) { curve.drag = -1; commitChange(); } });
  canvas.addEventListener("dblclick", (e) => { const pts = P().curve, i = nearest(toPt(e)); if (i > 0 && i < pts.length - 1) { beginChange(); pts.splice(i, 1); drawCurve(); changed(false); commitChange(); } });
  new ResizeObserver(() => drawCurve()).observe(wrap);
}
function cssVar(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
function monotone(points) {
  const x = points.map((p) => p[0] / 255), y = points.map((p) => p[1] / 255), n = x.length, out = [], d = [], m = new Array(n).fill(0);
  for (let i = 0; i < n - 1; i++) d.push((y[i + 1] - y[i]) / Math.max(1e-6, x[i + 1] - x[i]));
  if (n === 2) { for (let k = 0; k <= 128; k++) { const t = k / 128; out.push(t <= x[0] ? y[0] : t >= x[1] ? y[1] : y[0] + d[0] * (t - x[0])); } return out; }
  m[0] = d[0]; m[n - 1] = d[n - 2]; for (let i = 1; i < n - 1; i++) m[i] = (d[i - 1] + d[i]) / 2;
  for (let i = 0; i < n - 1; i++) { if (Math.abs(d[i]) < 1e-9) { m[i] = m[i + 1] = 0; continue; } const a = m[i] / d[i], b = m[i + 1] / d[i], s = a * a + b * b; if (s > 9) { const t = 3 / Math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]; } }
  for (let k = 0; k <= 128; k++) {
    const t = k / 128; if (t <= x[0]) { out.push(y[0]); continue; } if (t >= x[n - 1]) { out.push(y[n - 1]); continue; }
    let i = 0; while (i < n - 2 && t > x[i + 1]) i++;
    const h = x[i + 1] - x[i], u = (t - x[i]) / h;
    out.push(Math.max(0, Math.min(1, (2 * u ** 3 - 3 * u ** 2 + 1) * y[i] + (u ** 3 - 2 * u ** 2 + u) * h * m[i] + (-2 * u ** 3 + 3 * u ** 2) * y[i + 1] + (u ** 3 - u ** 2) * h * m[i + 1])));
  }
  return out;
}
function drawCurve() {
  if (!curve || !P()) return;
  const c = curve.canvas, dpr = devicePixelRatio || 1, W = c.clientWidth, H = c.clientHeight; if (!W) return;
  c.width = W * dpr; c.height = H * dpr;
  const ctx = c.getContext("2d"); ctx.scale(dpr, dpr);
  ctx.strokeStyle = cssVar("--track"); ctx.lineWidth = 1;
  for (let i = 1; i < 4; i++) { ctx.beginPath(); ctx.moveTo(W * i / 4, 0); ctx.lineTo(W * i / 4, H); ctx.moveTo(0, H * i / 4); ctx.lineTo(W, H * i / 4); ctx.stroke(); }
  ctx.setLineDash([3, 4]); ctx.strokeStyle = cssVar("--ink-3"); ctx.beginPath(); ctx.moveTo(0, H); ctx.lineTo(W, 0); ctx.stroke(); ctx.setLineDash([]);
  const pts = P().curve, ys = monotone(pts);
  ctx.strokeStyle = cssVar("--ink"); ctx.lineWidth = 2; ctx.beginPath();
  ys.forEach((v, k) => { const X = k / 128 * W, Y = (1 - v) * H; k ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); }); ctx.stroke();
  for (const [px, py] of pts) { ctx.beginPath(); ctx.arc(px / 255 * W, (1 - py / 255) * H, 5, 0, Math.PI * 2); ctx.fillStyle = "#fff"; ctx.fill(); ctx.strokeStyle = cssVar("--accent"); ctx.lineWidth = 2; ctx.stroke(); }
}

function applyMode() {
  if (!P()) return;
  const bw = P().bw;
  $$(".colour-only").forEach((e) => (e.hidden = bw || e.dataset.tab === "off"));
  $$(".bw-only").forEach((e) => (e.hidden = !bw));
  const t = $("#bwToggle"); if (t) { $$(":scope > button", t).forEach((b) => b.classList.toggle("on", (b.dataset.v === "bw") === bw)); moveDrop(t, $(":scope > button.on", t), false); }
  const mt = $('.sec[data-id="mixer"] .t'); if (mt) mt.textContent = bw ? "Black & white mix" : "Colour mixer";
}
function syncSections() {
  const d = S.schema.defaults;
  for (const sec of SECTIONS) {
    const el = $(`.sec[data-id="${sec.id}"]`); if (!el) continue;
    el.classList.toggle("changed", sec.keys.some((k) => k !== "bw" && JSON.stringify(P()[k]) !== JSON.stringify(d[k])));
  }
}
function refreshEdit() {
  if (!P()) return;
  sliders.forEach((s) => s.paint()); syncWheels(); drawCurve(); applyMode(); syncSections(); refreshInfo();
  $("#btnUndo").disabled = !(S.undo[S.current] || []).length;
  $("#btnRedo").disabled = !(S.redo[S.current] || []).length;
}

/* ───────────── change tracking, undo ───────────── */
let pending = null;
function pushUndo(id) { (S.undo[id] = S.undo[id] || []).push(JSON.stringify(S.params[id])); if (S.undo[id].length > 200) S.undo[id].shift(); S.redo[id] = []; }
function beginChange() { pending = JSON.stringify(P()); }
function changed(fast) { syncSections(); requestRender(fast); }
function commitChange() {
  const id = S.current; if (!id) return;
  const now = JSON.stringify(P());
  if (pending && pending !== now) { (S.undo[id] = S.undo[id] || []).push(pending); S.redo[id] = []; }
  pending = null;
  requestRender(false); markEdited(id); refreshThumb(id); refreshEdit();
}
function undo() { const id = S.current, u = S.undo[id]; if (!u || !u.length) return; (S.redo[id] = S.redo[id] || []).push(JSON.stringify(P())); S.params[id] = JSON.parse(u.pop()); afterHistory(); }
function redo() { const id = S.current, r = S.redo[id]; if (!r || !r.length) return; (S.undo[id] = S.undo[id] || []).push(JSON.stringify(P())); S.params[id] = JSON.parse(r.pop()); afterHistory(); }
function afterHistory() { refreshEdit(); requestRender(false); markEdited(S.current); refreshThumb(S.current); }

/* ───────────── rendering ───────────── */
const R = { busy: false, pending: null, url: null };
function requestRender(fast) {
  if (!S.current || S.view !== "edit") return;
  R.pending = { id: S.current, params: clone(P()), size: fast ? "drag" : null };
  pump();
}
async function pump() {
  if (R.busy || !R.pending) return;
  const job = R.pending; R.pending = null; R.busy = true;
  const spin = setTimeout(() => ($("#busy").hidden = false), 300);
  try {
    const url = await renderBlob(job.id, job.params, job.size);
    if (job.id === S.current) {
      const img = $("#after");
      await new Promise((res) => { img.onload = res; img.onerror = res; img.src = url; });
      if (R.url) URL.revokeObjectURL(R.url); R.url = url;
      if (!job.size) { setAmbient(url); queueHisto(); }
    } else URL.revokeObjectURL(url);
  } catch (e) { toast("Couldn't render: " + e.message); }
  clearTimeout(spin); $("#busy").hidden = true; R.busy = false;
  if (R.pending) pump();
}
let histoT = 0;
function queueHisto() { clearTimeout(histoT); histoT = setTimeout(() => requestAnimationFrame(drawHisto), 40); }
function drawHisto() {
  const c = $("#histo"), img = $("#after"); if (!c || !img.complete || !img.naturalWidth || $("#sideEdit").hidden) return;
  const w = 160, h = Math.max(1, Math.round(160 * img.naturalHeight / img.naturalWidth)), off = document.createElement("canvas"); off.width = w; off.height = h;
  const o = off.getContext("2d"); o.drawImage(img, 0, 0, w, h);
  const d = o.getImageData(0, 0, w, h).data, b = [new Float32Array(64), new Float32Array(64), new Float32Array(64)];
  for (let i = 0; i < d.length; i += 4) { b[0][d[i] >> 2]++; b[1][d[i + 1] >> 2]++; b[2][d[i + 2] >> 2]++; }
  let mx = 1; b.forEach((a) => a.forEach((x) => (mx = Math.max(mx, x))));
  const x = c.getContext("2d"), W = c.width, H = c.height; x.clearRect(0, 0, W, H);
  const mono = P() && P().bw, cols = mono ? ["#bdbdbd"] : ["#ff4f6d", "#3fd17c", "#4f8dff"];
  x.globalCompositeOperation = S.settings.theme === "dark" ? "screen" : "source-over";
  (mono ? [b[1]] : b).forEach((a, ch) => {
    x.beginPath(); x.moveTo(0, H); for (let k = 0; k < 64; k++) x.lineTo(k / 63 * W, H - Math.pow(a[k] / mx, .55) * (H - 8));
    x.lineTo(W, H); x.closePath(); x.fillStyle = cols[ch] + "55"; x.fill(); x.strokeStyle = cols[ch]; x.lineWidth = 2; x.stroke();
  });
  x.globalCompositeOperation = "source-over";
}
async function refreshInfo() {
  const id = S.current; if (!id) return;
  if (!S.info[id]) { try { S.info[id] = await get("info/" + id); } catch { S.info[id] = {}; } }
  if (id !== S.current) return;
  const i = S.info[id];
  $("#exif").innerHTML = [i.camera, i.focal, i.aperture, i.shutter, i.iso].filter(Boolean).map((t) => `<span>${t}</span>`).join("") || `<span>${(S.photos.find((p) => p.id === id) || {}).name || ""}</span>`;
}

/* before / after */
function initSplit() {
  const photo = $("#photo"), split = $("#split");
  split.addEventListener("pointerdown", (e) => {
    split.setPointerCapture(e.pointerId);
    const mv = (ev) => { const r = photo.getBoundingClientRect(); photo.style.setProperty("--split", Math.max(0, Math.min(100, (ev.clientX - r.left) / r.width * 100)) + "%"); };
    const up = () => { split.removeEventListener("pointermove", mv); split.removeEventListener("pointerup", up); if (anim()) G.fromTo($(".lens", split), { scale: 1.2 }, { scale: 1, duration: .8, ease: "elastic.out(1,.35)" }); };
    split.addEventListener("pointermove", mv); split.addEventListener("pointerup", up);
  });
  $("#btnCompare").addEventListener("click", (e) => { const on = e.currentTarget.classList.toggle("on"); split.hidden = !on; $("#before").hidden = !on; });
}

/* ───────────── photos + dock ───────────── */
async function addPhotos(list) {
  let added = 0;
  for (const p of list) {
    if (S.photos.find((q) => q.id === p.id)) continue;
    S.photos.push(p); S.params[p.id] = defaults(); S.undo[p.id] = []; S.redo[p.id] = [];
    addThumb(p); added++;
  }
  const first = !S.current && S.photos.length;
  if (first) await selectPhoto(S.photos[0].id);
  updateChrome();
  if (first && S.view === "looks") { requestAnimationFrame(() => { syncDrops(); measureLight(); }); grade(); }
  if (added && anim()) G.from($$("#strip .item").slice(-added), { y: 40, opacity: 0, scale: .6, duration: .8, ease: "back.out(1.8)", stagger: .05 });
}
function addThumb(p) {
  const t = document.createElement("div");
  t.className = "item loading"; t.dataset.id = p.id; t.title = p.name;
  t.innerHTML = `<img alt="" draggable="false"><span class="tick" title="Tick for batch (Ctrl+click)"><svg viewBox="0 0 24 24"><path d="M5 12l5 5 9-10"/></svg></span>${p.raw ? '<span class="raw">RAW</span>' : ""}`;
  const img = $("img", t); img.onload = () => t.classList.remove("loading"); img.src = `/api/thumb/${p.id}`;
  t.addEventListener("click", (e) => {
    if (e.target.closest(".tick") || e.ctrlKey || e.metaKey) { toggleTick(p.id); return; }
    selectPhoto(p.id);
  });
  $("#strip").appendChild(t);
  initDockMagnify();
}
function toggleTick(id) {
  S.ticked.has(id) ? S.ticked.delete(id) : S.ticked.add(id);
  const t = $(`.item[data-id="${id}"]`); t.classList.toggle("ticked", S.ticked.has(id));
  if (anim()) G.fromTo($(".tick", t), { scale: .6 }, { scale: 1, duration: .5, ease: "back.out(3)" });
  updateChrome();
}
function markEdited(id) {
  const t = $(`.item[data-id="${id}"]`); if (!t) return;
  const edited = JSON.stringify(S.params[id]) !== JSON.stringify(S.schema.defaults);
  let dot = $(".edited", t);
  if (edited && !dot) { dot = document.createElement("span"); dot.className = "edited"; t.appendChild(dot); }
  if (!edited && dot) dot.remove();
}
const thumbT = {};
function refreshThumb(id) {
  clearTimeout(thumbT[id]);
  thumbT[id] = setTimeout(async () => {
    try { const url = await renderBlob(id, S.params[id], "grid"); const img = $(`.item[data-id="${id}"] img`); if (!img) return; const old = img.src; img.src = url; if (old.startsWith("blob:")) URL.revokeObjectURL(old); } catch (_) {}
  }, 350);
}
async function selectPhoto(id) {
  if (S.current === id) return;
  S.current = id;
  $$("#strip .item").forEach((t) => t.classList.toggle("cur", t.dataset.id === id));
  const it = $(`#strip .item[data-id="${id}"]`);
  if (it && anim()) G.fromTo(it, { y: -16 }, { y: 0, duration: .8, ease: "bounce.out" });
  $("#before").src = `/api/original/${id}`;
  $("#after").src = `/api/original/${id}`;
  setAmbient(`/api/thumb/${id}`);
  if (S.view === "edit") { refreshEdit(); requestRender(false); }
  else if (S.looks.length) { S.looks = []; grade(); }
}
let dockQ = null;
function initDockMagnify() {
  if (!anim()) return;
  const dock = $("#dock"), items = $$(".item, .add", dock);
  dockQ = items.map((it) => ({ it, s: G.quickTo(it, "scale", { duration: .3, ease: "power3.out" }), y: G.quickTo(it, "y", { duration: .3, ease: "power3.out" }), cx: 0 }));
  if (dock.dataset.wired) return; dock.dataset.wired = "1";
  let raf = 0, px = 0;
  dock.addEventListener("pointerenter", () => { for (const o of dockQ) { const r = o.it.getBoundingClientRect(); o.cx = r.left + r.width / 2; } });
  $("#strip").addEventListener("scroll", () => { for (const o of dockQ) { const r = o.it.getBoundingClientRect(); o.cx = r.left + r.width / 2; } }, { passive: true });
  dock.addEventListener("pointermove", (e) => { px = e.clientX; if (raf) return; raf = requestAnimationFrame(() => { raf = 0; for (const o of dockQ) { const k = 1 + .38 * Math.max(0, 1 - Math.abs(px - o.cx) / 120); o.s(k); o.y(-(k - 1) * 20); } }); });
  dock.addEventListener("pointerleave", () => { for (const o of dockQ) { o.s(1); o.y(0); } });
}

/* opening files */
async function pickFiles() {
  const a = bridge();
  if (a && a.pick_files) { const paths = await a.pick_files(); if (paths && paths.length) await openPaths(paths); }
  else $("#filePicker").click();
}
async function openPaths(paths) { try { const l = await post("open", { paths }); if (!l.length) toast("No photos Grvty can open in there"); await addPhotos(l); } catch (e) { toast(e.message); } }
async function uploadFiles(files) {
  const exts = S.schema.formats, list = [...files].filter((f) => exts.some((x) => f.name.toLowerCase().endsWith(x)));
  if (!list.length) { toast("Those aren't photos Grvty can open. Try RAW or JPEG files."); return; }
  toast(`Adding ${list.length} photo${list.length > 1 ? "s" : ""}…`);
  for (const f of list) {
    try {
      const r = await fetch("/api/upload", { method: "POST", headers: { "X-Filename": encodeURIComponent(f.name) }, body: f });
      const j = await r.json(); if (!r.ok) throw new Error(j.error); await addPhotos([j]);
    } catch (e) { toast(e.message); }
  }
}

/* ───────────── export ───────────── */
let exportWhich = "current", quality = 95;
function openExport() {
  $("#exportVeil").hidden = false; $("#exportProgress").hidden = true; $("#btnOpenFolder").hidden = true; $("#btnExportGo").disabled = false;
  $("#exportFolder").textContent = S.settings.folder || "Pictures\\Grvty";
  exportWhich = S.ticked.size > 1 ? "ticked" : "current";
  $$("#exportWhich button").forEach((b) => b.classList.toggle("on", b.dataset.v === exportWhich));
  $("#sameLookRow").hidden = exportWhich === "current";
  if (anim()) G.fromTo("#exportVeil .sheet", { y: 30, scale: .94, opacity: 0 }, { y: 0, scale: 1, opacity: 1, duration: .55, ease: "back.out(1.6)" });
  requestAnimationFrame(() => { syncDrops(); qs.paint(); });
}
async function runExport() {
  const ids = exportWhich === "current" ? [S.current] : exportWhich === "ticked" ? [...S.ticked] : S.photos.map((p) => p.id);
  if (!ids.length) { toast("Tick some photos first"); return; }
  const same = $("#exportSameLook").checked && exportWhich !== "current";
  const items = ids.map((id) => ({ id, params: same ? P() : S.params[id] }));
  $("#btnExportGo").disabled = true;
  const prog = $("#exportProgress"), bar = $(".bar span", prog), txt = $(".ptext", prog);
  prog.hidden = false; bar.style.width = "0"; txt.textContent = `Exporting 0 of ${items.length}…`;
  try {
    const { job } = await post("export", { items, folder: S.settings.folder || null, quality });
    for (;;) {
      await new Promise((r) => setTimeout(r, 450));
      const st = await get("export/" + job);
      bar.style.width = (st.done / st.total * 100) + "%";
      txt.textContent = `Exporting ${st.done} of ${st.total}…`;
      if (st.finished) {
        txt.textContent = st.failed.length ? `Saved ${st.done - st.failed.length}. ${st.failed.length} couldn't be saved: ${st.failed[0]}` : `Done. Saved ${st.done} photo${st.done > 1 ? "s" : ""} to ${st.folder}`;
        S.lastFolder = st.folder; $("#btnOpenFolder").hidden = !bridge(); break;
      }
    }
  } catch (e) { txt.textContent = "Export failed: " + e.message; }
  $("#btnExportGo").disabled = false;
}
let qs;

/* ───────────── preset ───────────── */
function presetParams() { return S.view === "looks" && chosen() ? chosen().params : P(); }
function openPreset() {
  const L = chosen();
  $("#presetName").value = S.view === "looks" && L ? (L.name === "Closest match" || L.name === "Your pick" ? (S.prompt ? S.prompt.slice(0, 40) : "Grvty look") : L.name) : "My Grvty look";
  $("#presetVeil").hidden = false;
  if (anim()) G.fromTo("#presetVeil .sheet", { y: 30, scale: .94, opacity: 0 }, { y: 0, scale: 1, opacity: 1, duration: .55, ease: "back.out(1.6)" });
  setTimeout(() => $("#presetName").select(), 60);
}
async function savePreset(e) {
  e.preventDefault();
  const name = $("#presetName").value.trim() || "Grvty look";
  try {
    if (S.view === "looks") recordPick();
    const r = await post("preset", { name, params: presetParams() });
    $("#presetVeil").hidden = true;
    toast(r.files.length ? `Saved “${name}” to Lightroom presets` : "Couldn't save the preset file");
  } catch (err) { toast("Couldn't save the preset: " + err.message); }
}

/* ───────────── misc ───────────── */
async function saveSettings() { try { await post("settings", S.settings); } catch (_) {} }
let toastT;
function toast(m) {
  const t = $("#toast"); t.textContent = m; t.hidden = false;
  if (anim()) G.fromTo(t, { y: 20, opacity: 0, scale: .9 }, { y: 0, opacity: 1, scale: 1, duration: .5, ease: "back.out(2)" });
  clearTimeout(toastT);
  toastT = setTimeout(() => { if (anim()) G.to(t, { y: 14, opacity: 0, duration: .3, onComplete: () => (t.hidden = true) }); else t.hidden = true; }, 2800);
}
function intro() {
  if (!anim()) return;
  G.from(".top > *, .stage, .side, .dock", { y: 20, opacity: 0, scale: .98, duration: .8, ease: "expo.out", stagger: .06, clearProps: "transform,opacity", onComplete: measureLight });
  G.fromTo("#moon", { rotation: -360, svgOrigin: "12 15" }, { rotation: 0, svgOrigin: "12 15", duration: 2.2, ease: "power3.out" });
}

/* ───────────── boot ───────────── */
async function boot() {
  S.schema = await get("schema");
  try { Object.assign(S.settings, await get("settings")); } catch (_) {}
  if (!["light", "dark"].includes(S.settings.theme)) S.settings.theme = "light";
  document.documentElement.dataset.theme = S.settings.theme;
  buildEditPanel();

  $$("#tabs button").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
  $$("#mode button").forEach((b) => b.addEventListener("click", () => { moveDrop($("#mode"), b); setTheme(b.dataset.themePick, b); }));
  wireSeg($("#engineSeg"), (b) => { if (b.dataset.v === "ai") { toast("AI mode is still training. It arrives in the next update."); return false; } });
  wireSeg($("#countSeg"), (b) => { S.count = +b.dataset.n; setTimeout(grade, 10); });
  $("#promptForm").addEventListener("submit", (e) => { e.preventDefault(); grade(); });
  $$("#chips .chip").forEach((c) => c.addEventListener("click", () => { $("#promptIn").value = c.dataset.p; grade(); }));
  $("#btnMore").addEventListener("click", moreLikeThis);
  $("#btnTune").addEventListener("click", tuneInEdit);
  $("#btnPreset").addEventListener("click", openPreset);
  $("#btnApply").addEventListener("click", () => {
    const ids = S.ticked.size > 1 ? [...S.ticked] : [S.current];
    recordPick(); useLook(ids); toast(`${chosen().name} is on ${ids.length > 1 ? ids.length + " photos" : "this photo"}. Open Edit to fine-tune.`);
  });
  $("#btnUndo").addEventListener("click", undo);
  $("#btnRedo").addEventListener("click", redo);
  $("#btnReset").addEventListener("click", () => { beginChange(); S.params[S.current] = defaults(); refreshEdit(); commitChange(); });
  $("#btnCopy").addEventListener("click", () => { S.clipboard = clone(P()); $("#btnPaste").disabled = false; toast("Look copied. Tick photos in the strip, then Paste."); });
  $("#btnPaste").addEventListener("click", () => {
    if (!S.clipboard) return;
    const ids = S.ticked.size ? [...S.ticked] : [S.current];
    for (const id of ids) { pushUndo(id); S.params[id] = clone(S.clipboard); markEdited(id); refreshThumb(id); }
    refreshEdit(); requestRender(false); toast(`Pasted onto ${ids.length} photo${ids.length > 1 ? "s" : ""}`);
  });
  $("#btnExport").addEventListener("click", openExport);
  $("#btnExportClose").addEventListener("click", () => ($("#exportVeil").hidden = true));
  wireSeg($("#exportWhich"), (b) => { exportWhich = b.dataset.v; $("#sameLookRow").hidden = exportWhich === "current"; });
  qs = makeSlider({ min: 60, max: 100, get: () => quality, set: (v) => { quality = v; $("#qualityVal").textContent = v; }, onCommit: () => {}, onChange: () => {}, compact: true });
  qs.el.classList.add("plain"); $("#qualitySlider").replaceWith(qs.el);
  $("#btnExportGo").addEventListener("click", runExport);
  $("#btnFolder").addEventListener("click", async () => { const a = bridge(); if (a && a.pick_folder) { const f = await a.pick_folder(); if (f) { S.settings.folder = f; $("#exportFolder").textContent = f; saveSettings(); } } else toast("Folder picking works in the Grvty app window"); });
  $("#btnOpenFolder").addEventListener("click", () => { const a = bridge(); if (a && S.lastFolder) a.open_folder(S.lastFolder); });
  $("#presetForm").addEventListener("submit", savePreset);
  $("#btnPresetClose").addEventListener("click", () => ($("#presetVeil").hidden = true));
  for (const v of $$(".veil")) v.addEventListener("pointerdown", (e) => { if (e.target === v) v.hidden = true; });
  $("#btnAdd").addEventListener("click", pickFiles);
  $("#btnAddEmpty").addEventListener("click", pickFiles);
  $("#filePicker").addEventListener("change", (e) => { uploadFiles(e.target.files); e.target.value = ""; });
  initSplit();

  // drag and drop anywhere
  let depth = 0;
  addEventListener("dragenter", (e) => { if (![...e.dataTransfer.types].includes("Files")) return; e.preventDefault(); depth++; $("#dropHint").hidden = false; });
  addEventListener("dragleave", () => { if (--depth <= 0) { depth = 0; $("#dropHint").hidden = true; } });
  addEventListener("dragover", (e) => e.preventDefault());
  addEventListener("drop", (e) => { e.preventDefault(); depth = 0; $("#dropHint").hidden = true; if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files); });

  // keyboard
  addEventListener("keydown", (e) => {
    const typing = e.target.tagName === "INPUT" && e.target.type !== "checkbox";
    const ctrl = e.ctrlKey || e.metaKey, k = e.key.toLowerCase();
    if (e.key === "Escape") { $$(".veil").forEach((v) => (v.hidden = true)); return; }
    if (ctrl && k === "z" && !typing && S.view === "edit") { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
    if (ctrl && k === "y" && !typing && S.view === "edit") { e.preventDefault(); redo(); return; }
    if (typing || !S.current) return;
    if (S.view === "edit" && e.key === "\\") { $("#photo").classList.add("peek"); return; }
    if (S.view === "looks" && S.looks.length) {
      const cols = parseInt(getComputedStyle($("#grid")).getPropertyValue("--cols")) || 4;
      const mv = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: cols, ArrowUp: -cols }[e.key];
      if (mv) { e.preventDefault(); select(Math.max(0, Math.min(S.looks.length - 1, S.sel + mv))); }
      else if (e.key === "Enter" && !e.target.closest("button, [role=slider]")) tuneInEdit();
    }
  });
  addEventListener("keyup", (e) => { if (e.key === "\\") $("#photo").classList.remove("peek"); });
  $("#after").addEventListener("load", () => { if (!R.busy) queueHisto(); });

  initLight(); updateChrome(); syncDrops(); intro();
  if (document.fonts) document.fonts.ready.then(() => { syncDrops(); measureLight(); });
  try { const list = await get("photos"); if (list.length) await addPhotos(list); } catch (_) {}
}
boot();
