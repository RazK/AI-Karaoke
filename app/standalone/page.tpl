<title>Hollow Karaoke</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;800&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --ground:#0c0a11; --panel:#16121e; --edge:#2a2336;
  --ink:#f3eefb; --dim:#857b99;
  --lit:#ffcf7a;              /* the new words, as they are sung */
  --was:#57d0bd;              /* the words that used to be there */
  --sans:"IBM Plex Sans",system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,monospace;
  --disp:"Archivo","Arial Narrow",system-ui,sans-serif;
}
/* A karaoke screen is a dark room. This page commits to that in both host
   themes rather than inverting into something nobody sings from. */
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
  height:100dvh;overflow:hidden;display:flex;flex-direction:column}
button{font:inherit;color:inherit;background:none;border:0;cursor:pointer}
button:focus-visible{outline:2px solid var(--lit);outline-offset:2px;border-radius:6px}

/* ── head ─────────────────────────────────────────────────────────────── */
header{flex:none;padding:14px 18px 10px;border-bottom:1px solid var(--edge);
  background:linear-gradient(180deg,#120e1a,var(--ground))}
.song{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.song h1{margin:0;font-family:var(--disp);font-size:19px;font-weight:800;
  letter-spacing:-.01em}
.song .by{color:var(--dim);font-size:13px}
.song .lic{font-family:var(--mono);font-size:10.5px;color:var(--dim);
  border:1px solid var(--edge);border-radius:999px;padding:2px 8px}
.takes{display:flex;gap:8px;margin-top:11px;overflow-x:auto;padding-bottom:2px}
.take{flex:none;border:1px solid var(--edge);border-radius:11px;padding:8px 12px;
  text-align:left;background:var(--panel);transition:border-color .15s,background .15s}
.take:hover{border-color:#40354f}
.take[aria-pressed="true"]{border-color:var(--lit);background:#241c15}
.take .corpus{display:block;font-size:12.5px;font-weight:600;white-space:nowrap}
.take .meta{display:block;font-family:var(--mono);font-size:10.5px;color:var(--dim);
  margin-top:3px;font-variant-numeric:tabular-nums}
.take[aria-pressed="true"] .meta{color:var(--lit)}

/* ── stage ────────────────────────────────────────────────────────────── */
#stage{flex:1;position:relative;overflow:clip;
  mask-image:linear-gradient(to bottom,transparent,#000 15%,#000 85%,transparent)}
#reel{position:absolute;left:0;right:0;top:50%;will-change:transform;
  transition:transform .42s cubic-bezier(.2,.7,.3,1)}
.line{padding:10px 20px;text-align:center}
/* The two rows are a pair, so they are sized as one: the sung line leads and
   the original sits just under it, close enough to read as its partner rather
   than as a caption. --fit shrinks a long line to the width it has. */
.line{--now:clamp(21px,5.6vw,38px);--was:clamp(16px,4.1vw,27px)}
.line.past,.line.soon{--now:clamp(14px,2.5vw,21px);--was:clamp(11px,1.9vw,15px)}
.was{font-family:var(--sans);font-size:calc(var(--was) * var(--fit,1));
  font-weight:500;color:#2c5a54;line-height:1.3;margin-bottom:6px;min-height:16px}
.now{font-family:var(--disp);font-size:calc(var(--now) * var(--fit,1));
  font-weight:800;line-height:1.18;letter-spacing:-.015em;overflow-wrap:break-word}
.w,.ow{transition:color .1s}
.w{color:#39304a}
.ow{color:#2c5a54}
.line.on .was{color:#39786f}
.line.on .ow.lit{color:var(--was)}
.line.on .w.lit{color:var(--lit);text-shadow:0 0 26px rgba(255,207,122,.45)}
.line.past .w{color:rgba(243,238,251,.22)}
.line.past .now,.line.soon .now{font-weight:600}
.line.past .was,.line.soon .was{display:none}
.line.next .was{display:block;font-size:clamp(11px,1.8vw,14px);color:#24504b}
.line.soon .w{color:#4c4162}
.line.far{opacity:.4}
.line.unsure .now::after{content:"?";color:#c98b4b;font-size:.5em;
  vertical-align:super;margin-left:5px}
/* Word over word, and only on the line being sung and the one after it, where
   both rows are on screen. One grid for the whole line, not one per row:
   display:contents dissolves the wrappers so every word from both rows is an
   item of the same grid, which is what makes the columns resolve identically
   instead of drifting a few pixels a word. */
body.aligned .line.on,body.aligned .line.next{display:grid;
  grid-template-columns:var(--cols);align-items:baseline;justify-items:start;
  column-gap:8px;row-gap:5px;width:max-content;max-width:100%;margin-inline:auto}
body.aligned .line.on .was,body.aligned .line.on .now,
body.aligned .line.next .was,body.aligned .line.next .now{display:contents}
body.aligned .line.on .ow,body.aligned .line.next .ow{grid-row:1;white-space:nowrap}
body.aligned .line.on .w,body.aligned .line.next .w{grid-row:2;white-space:nowrap}

/* ── transport ────────────────────────────────────────────────────────── */
footer{flex:none;border-top:1px solid var(--edge);background:#100d17;
  padding:11px 18px calc(14px + env(safe-area-inset-bottom))}
.scrub{display:flex;align-items:center;gap:11px;font-family:var(--mono);
  font-size:11px;color:var(--dim);font-variant-numeric:tabular-nums}
.scrub input{flex:1;accent-color:var(--lit);min-width:0}
.row{display:flex;align-items:center;justify-content:center;gap:9px;
  flex-wrap:wrap;margin-top:10px}
.pp{width:50px;height:50px;border-radius:50%;background:var(--lit);color:#241a08;
  display:grid;place-items:center;font-size:17px;flex:none}
.chip{border:1px solid var(--edge);border-radius:10px;padding:8px 11px;
  font-size:12px;color:var(--dim);background:var(--panel)}
.chip b{color:var(--ink);font-weight:600}
.chip:hover{border-color:#40354f}
.nudge{display:flex;align-items:center;border:1px solid var(--edge);
  border-radius:10px;background:var(--panel)}
.nudge button{padding:8px 11px;color:var(--dim);font-size:14px}
.nudge button:hover{color:var(--ink)}
.nudge .val{font-family:var(--mono);font-size:11px;color:var(--dim);
  min-width:62px;text-align:center;font-variant-numeric:tabular-nums}
.nudge .val b{color:var(--ink)}
.note{margin-top:9px;text-align:center;font-size:11px;color:#5d5570;line-height:1.5}
.note a{color:#7d7392}
@media (prefers-reduced-motion:reduce){#reel{transition:none}}
</style>

<header>
  <div class="song">
    <h1 id="title"></h1>
    <span class="by" id="by"></span>
    <span class="lic" id="lic"></span>
  </div>
  <div class="takes" id="takes"></div>
</header>

<div id="stage"><div id="reel"></div></div>

<footer>
  <div class="scrub">
    <span id="tnow">0:00</span>
    <input type="range" id="seek" min="0" max="1000" value="0" aria-label="Seek">
    <span id="tend">0:00</span>
  </div>
  <div class="row">
    <button class="chip" id="spacing">lines <b>flowing</b></button>
    <button class="pp" id="pp" aria-label="Play">&#9654;</button>
    <div class="nudge">
      <button id="back" aria-label="Lyrics earlier">&#9664;</button>
      <span class="val">lyrics <b id="off">0 ms</b></span>
      <button id="fwd" aria-label="Lyrics later">&#9654;</button>
    </div>
  </div>
  <div class="note" id="note"></div>
</footer>

<script>
const D = __BUNDLE__;
const $ = id => document.getElementById(id);
const esc = s => s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const clock = s => `${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`;

const audio = new Audio(D.audio);
audio.preload = 'auto';

let take = 0, offset = 0, rows = [], active = -1;
let aligned = false;
try { aligned = localStorage.getItem('lines') === 'aligned'; } catch (e) {}

// Two ways to set the words. Flowing is how lyrics are normally printed:
// centred, evenly spaced, easy to read and silent about rhythm. Word over word
// puts both lines on one grid with a column per syllable -- they sit on the
// same syllables, so each new word starts exactly where the word it replaces
// starts, and a held syllable is a wide column rather than a guess.
function slotWidths(owords, slots) {
  // One column per syllable, each only as wide as the widest word that lands on
  // it. The longer of the two lines therefore sets the width of the pair and the
  // shorter one spreads to match it. Sizing the columns by duration instead
  // stretched every line across the whole screen, which nobody can read.
  return `repeat(${slots},auto)`;
}

function grid(words, cls) {
  return words.map(w =>
    `<span class="${cls}" style="grid-column:${(w.i || 0) + 1}/span ${w.n || 1}">`
    + `${esc(w.w)}</span>`).join(' ');
}

// A long line can still be wider than the screen, so it is scaled to fit. Both
// rows are in one grid, so scaling the line scales them together and they stay
// aligned.
function fitLine(r) {
  if (!r) return;
  r.el.style.setProperty('--fit', '1');
  const room = $('stage').clientWidth - 28;
  if (room <= 0) return;
  const wide = r.el.scrollWidth;
  if (wide > room) r.el.style.setProperty('--fit', Math.max(0.4, room / wide).toFixed(3));
}

function fitLines() {
  fitLine(rows[Math.max(active, 0)]);
  fitLine(rows[Math.max(active, 0) + 1]);
}

$('title').textContent = D.title;
$('by').textContent = D.artist;
$('lic').textContent = D.licence;
$('note').innerHTML = `“${esc(D.title)}” by ${esc(D.artist)}, ${esc(D.licence)}, from `
  + `<a href="https://github.com/f90/jamendolyrics" target="_blank" rel="noopener">JamendoLyrics</a>. `
  + `The backing track is this recording with its vocal separated out on a machine. `
  + `The words are rewritten from an unrelated text onto the same syllables.`;

const NAMES = {
  'ikea-manuals': 'An IKEA assembly manual',
  'yelp-reviews-1star': 'One-star restaurant reviews',
  'legal-disclaimers': 'Terms and conditions',
};

D.takes.forEach((t, i) => {
  const b = document.createElement('button');
  b.className = 'take';
  b.setAttribute('aria-pressed', String(i === 0));
  b.innerHTML = `<span class="corpus">${esc(NAMES[t.corpus] || t.corpus.replace(/-/g, ' '))}</span>`
    + `<span class="meta">licence ${t.licence.toFixed(2)} · ${t.score.toFixed(2)}/10 · `
    + `${Math.round(t.fromCorpus * 100)}% lifted</span>`;
  b.onclick = () => pick(i);
  $('takes').append(b);
});

function pick(i) {
  take = i;
  [...$('takes').children].forEach((b, k) =>
    b.setAttribute('aria-pressed', String(k === i)));
  build();
}

function build() {
  const t = D.takes[take];
  $('reel').innerHTML = '';
  rows = D.lines.map((l, i) => {
    const el = document.createElement('div');
    el.className = 'line' + (l.u ? ' unsure' : '');
    el.style.setProperty('--cols', slotWidths(l.ow, l.k || l.ow.length || 1));
    el.innerHTML = `<div class="was">${l.ow.length ? grid(l.ow, 'ow') : esc(l.o)}</div>`
      + `<div class="now">${grid(t.words[i], 'w')}</div>`;
    el.onclick = () => { audio.currentTime = Math.max(0, l.s - 0.3); };
    $('reel').append(el);
    return { el, line: l, words: t.words[i], owords: l.ow,
             spans: [...el.querySelectorAll('.now .w')],
             ospans: [...el.querySelectorAll('.was .ow')] };
  });
  active = -1;
  paint(true);
  if (aligned) fitLines();
}

function paint(force) {
  const t = audio.currentTime - offset / 1000;
  let i = -1;
  for (let k = 0; k < rows.length; k++) if (t >= rows[k].line.s - 0.25) i = k;
  if (i !== active || force) {
    active = i;
    rows.forEach((r, k) => {
      r.el.className = 'line' + (r.line.u ? ' unsure' : '')
        + (k === i ? ' on' : k < i ? ' past' : ' soon')
        + (k === i + 1 ? ' next' : '')
        + (Math.abs(k - i) > 3 ? ' far' : '');
    });
    if (aligned) { fitLine(rows[Math.max(i, 0)]); fitLine(rows[Math.max(i, 0) + 1]); }
    const target = rows[Math.max(i, 0)];
    if (target) $('reel').style.transform =
      `translateY(${-(target.el.offsetTop + target.el.offsetHeight / 2)}px)`;
  }
  if (i >= 0) {
    const r = rows[i];
    // Both lines light together. They sit on the same syllables, so watching
    // them at once shows which new word takes the place of which old one.
    r.words.forEach((w, k) => r.spans[k].classList.toggle('lit', t >= w.t));
    r.owords.forEach((w, k) => {
      if (r.ospans[k]) r.ospans[k].classList.toggle('lit', t >= w.t);
    });
  }
}

function frame() {
  requestAnimationFrame(frame);
  if (!audio.duration) return;
  if (!seeking) {
    $('seek').value = Math.round(1000 * audio.currentTime / audio.duration);
    $('tnow').textContent = clock(audio.currentTime);
  }
  paint(false);
}

let seeking = false;
$('seek').addEventListener('pointerdown', () => { seeking = true; });
$('seek').addEventListener('pointerup', () => { seeking = false; });
$('seek').oninput = e => {
  if (audio.duration) audio.currentTime = audio.duration * e.target.value / 1000;
};
audio.onloadedmetadata = () => { $('tend').textContent = clock(audio.duration); };
audio.onplay = () => { $('pp').innerHTML = '&#10073;&#10073;'; $('pp').setAttribute('aria-label','Pause'); };
audio.onpause = () => { $('pp').innerHTML = '&#9654;'; $('pp').setAttribute('aria-label','Play'); };
$('pp').onclick = () => { audio.paused ? audio.play() : audio.pause(); };

function nudge(ms) {
  offset = Math.max(-3000, Math.min(3000, offset + ms));
  $('off').textContent = `${offset >= 0 ? '' : '-'}${Math.abs(offset)} ms`;
  paint(true);
}
$('back').onclick = () => nudge(-100);
$('fwd').onclick = () => nudge(100);

function applyLayout() {
  document.body.classList.toggle('aligned', aligned);
  $('spacing').innerHTML = `lines <b>${aligned ? 'word over word' : 'flowing'}</b>`;
  if (aligned) fitLines();
}
$('spacing').onclick = () => {
  aligned = !aligned;
  try { localStorage.setItem('lines', aligned ? 'aligned' : 'flowing'); } catch (e) {}
  applyLayout();
};
addEventListener('resize', () => { if (aligned) fitLines(); });

document.addEventListener('keydown', e => {
  if (e.code === 'Space') { e.preventDefault(); $('pp').click(); }
  if (e.code === 'ArrowLeft') nudge(-100);
  if (e.code === 'ArrowRight') nudge(100);
});

applyLayout();
build();
frame();
</script>
