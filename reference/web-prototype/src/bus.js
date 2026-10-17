// Tiny event bus shared by game systems (audio, ui, missions listen; world objects emit).
const handlers = {};
export const bus = {
  on(ev, fn) { (handlers[ev] ||= []).push(fn); return () => { handlers[ev] = handlers[ev].filter((f) => f !== fn); }; },
  emit(ev, ...a) { (handlers[ev] || []).slice().forEach((f) => f(...a)); },
  clear() { for (const k in handlers) delete handlers[k]; },
};
