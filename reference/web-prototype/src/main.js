import { Game } from './game.js';
const game = new Game();
window.__game = game;
game.boot().catch((e) => {
  console.error(e);
  const t = document.getElementById('loadtext');
  if (t) t.textContent = 'This page needs WebGL 2, which this browser did not provide. ' + (e && e.message ? '(' + e.message + ')' : '');
});
