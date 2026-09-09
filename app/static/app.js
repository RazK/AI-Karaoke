'use strict';
// The stage. One song, one body of text, one dial, then play it.

const $ = id => document.getElementById(id);
const api = (u, o) => fetch(u, o).then(r => r.ok ? r.json() : r.json().then(e => {
  throw new Error(e.detail || r.statusText); }));
const clock = s => (s < 0 ? '0:00'
  : Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0'));

let songs = [], pickedSong = null, pickedCorpus = null, poll = null;

// ── setup screen ──────────────────────────────────────────────────────────

const LICENCE = [
  [0.15, 'only phrases the text already contains'],
  [0.35, 'its own words, trimmed to fit'],
  [0.65, 'rearranged and paraphrased'],
  [0.85, 'freely rewritten'],
  [1.01, 'puns, padding and invented words'],
];

function licenceLabel(v) {
  $('licv').textContent = v.toFixed(2);
  $('licd').textContent = LICENCE.find(([hi]) => v < hi)[1];
}

$('lic').oninput = e => licenceLabel(+e.target.value);
$('own').oninput = () => { if ($('own').value.trim()) pickCorpus(null); ready(); };

function ready() {
  $('make').disabled = !(pickedSong && (pickedCorpus || $('own').value.trim()));
}

const toggle = id => {
  const el = $(id);
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
};

async function loadLibrary() {
  songs = await api('/api/songs');
  $('songs').innerHTML = songs.length ? '' :
    '<p class="note">No songs yet. Add one from a YouTube URL, or import a karaoke file.</p>';
  songs.forEach(s => {
    const b = document.createElement('button');
    b.className = 'card' + (pickedSong === s.ref ? ' sel' : '');
    b.innerHTML = `<b>${esc(s.title)}</b><small>${esc(s.artist)}
      <span class="tag">${s.source_kind === 'youtube' ? 'YouTube' : 'karaoke file'}</span></small>
      <small style="display:block;margin-top:3px">${clock(s.duration)} · ${s.n_lines} lines${
        s.uncertain_lines ? ` · ${s.uncertain_lines} uncertain` : ''}</small>`;
    b.onclick = () => { pickedSong = s.ref; loadLibrary(); ready(); };
    $('songs').append(b);
  });

  const cs = await api('/api/corpora');
  $('corpora').innerHTML = '';
  cs.forEach(c => {
    const b = document.createElement('button');
    b.className = 'card' + (pickedCorpus === c.id ? ' sel' : '');
    b.innerHTML = `<b>${esc(c.label)}</b><small>${esc(c.description || '')}</small>`;
    b.onclick = () => { pickCorpus(c.id); $('own').value = ''; };
    $('corpora').append(b);
  });
}

function pickCorpus(id) {
  pickedCorpus = id;
  document.querySelectorAll('#corpora .card').forEach(el => el.classList.remove('sel'));
  loadLibrary().then(ready);
}

const esc = s => String(s == null ? '' : s).replace(/[<>&]/g,
  c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]));

// ── jobs: never leave the screen saying nothing ───────────────────────────

function watch(jobId, done) {
  $('work').classList.add('on');
  clearInterval(poll);
  poll = setInterval(async () => {
    const j = await api('/api/jobs/' + jobId);
    $('what').textContent = j.what;
    $('log').textContent = j.log.join('\n');
    $('log').className = '';
    if (j.state === 'done') {
      clearInterval(poll);
      $('work').classList.remove('on');
      done(j.result);
    } else if (j.state === 'failed') {
      clearInterval(poll);
      document.querySelector('#work .spin').style.display = 'none';
      $('what').textContent = 'That did not work';
      $('log').textContent = j.error;
      $('log').className = 'err';
    }
  }, 900);
}

async function addYouTube() {
  const url = $('yt').value.trim();
  if (!url) return;
  const { job } = await api('/api/ingest/youtube', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  watch(job, r => { pickedSong = r.ref; $('yt').value = ''; loadLibrary().then(ready); });
}

async function addKaraoke() {
  if (!$('lrc').files[0] || !$('aud').files[0]) {
    alert('Pick both the karaoke file and the recording it belongs to.'); return;
  }
  const fd = new FormData();
  fd.append('lrc', $('lrc').files[0]);
  fd.append('audio', $('aud').files[0]);
  const { job } = await (await fetch('/api/ingest/karaoke', { method: 'POST', body: fd })).json();
  watch(job, r => { pickedSong = r.ref; loadLibrary().then(ready); });
}

async function make() {
  const body = {
    ref: pickedSong, licence: +$('lic').value,
    corpus: pickedCorpus || '', text: $('own').value.trim(),
    name: pickedCorpus ? '' : 'pasted text',
  };
  $('make').disabled = true;
  const { job } = await api('/api/generate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  watch(job, r => { $("make").disabled = false; openSong(r.ref, r.name); });
}

// ── player ────────────────────────────────────────────────────────────────

const au = $('au');
let show = null, offset = 0, rows = [], raf = null, active = -1;

async function openSong(ref, name) {
  const song = await api('/api/song/' + ref);
  const d = await api(`/api/song/${ref}/dressing/${name}`);
  show = { ref, name, song, d };
  offset = 0;
  $('off').textContent = '0 ms';
  $('ptitle').textContent = `${song.song.title} — ${song.song.artist}`;
  $('psub').textContent =
    `${d.corpus} · licence ${d.licence.toFixed(2)} · ${d.card.singable.toFixed(1)}/10`
    + (d.bends.length ? ` · ${d.bends.length} bent` : '');

  $('inner').innerHTML = '<div id="count"></div>';
  rows = song.lines.map((l, i) => {
    const el = document.createElement('div');
    el.className = 'ln' + (l.uncertain ? ' unsure' : '');
    const ow = l.owords || [];
    el.style.setProperty('--cols', slotWidths(ow, l.slots));
    el.innerHTML = `<div class="orig">${
      ow.length ? grid(ow, 'ow') : esc(l.original)}</div><div class="txt">${
      grid(d.words[i], 'w')}</div>`;
    el.onclick = () => { au.currentTime = Math.max(0, l.start - 0.3); };
    $('inner').append(el);
    return { el, line: l, words: d.words[i], owords: ow,
             spans: [...el.querySelectorAll('.txt .w')],
             ospans: [...el.querySelectorAll('.orig .ow')] };
  });

  au.src = `/api/audio/${ref}?track=instrumental`;
  au.onloadedmetadata = () => { $('tend').textContent = clock(au.duration); };
  $('setup').classList.remove('on');
  $('play').classList.add('on');
  if (aligned) fitLines();  // needs the player on screen: a hidden rail has no width
  $('bar').style.display = 'none';
  active = -1;
  au.play().catch(() => {});
  tick();
}

function back() {
  au.pause();
  cancelAnimationFrame(raf);
  $('play').classList.remove('on');
  $('setup').classList.add('on');
  $('bar').style.display = '';
  closeSheets();
  loadLibrary();
}

function toggleplay() { au.paused ? au.play() : au.pause(); }
au.onplay = () => { $('pp').textContent = '❚❚'; };
au.onpause = () => { $('pp').textContent = '▶'; };
au.onended = () => openRate();

function nudge(ms) {
  offset += ms;
  $('off').textContent = (offset > 0 ? '+' : '') + offset + ' ms';
}
document.addEventListener('keydown', e => {
  if (!$('play').classList.contains('on')) return;
  if (e.key === 'ArrowLeft') nudge(-50);
  else if (e.key === 'ArrowRight') nudge(50);
  else if (e.key === ' ') { e.preventDefault(); toggleplay(); }
});

// Two ways to set the words.
//
// Flowing is how lyrics are normally printed: centred, evenly spaced, easy to
// read and silent about rhythm.
//
// Word over word puts both lines on one grid with a column per syllable. The
// original and the rewrite sit on the same syllables, so each new word lands
// directly under the old one it replaces, and the columns are as wide as the
// syllables are long -- which is where the rhythm becomes visible, and where a
// held note becomes a wide column rather than a guess.
function slotWidths(owords, slots) {
  // One column per syllable, each only as wide as the widest word that lands on
  // it. The longer of the two lines therefore sets the width of the pair and
  // the shorter one spreads to match it. Sizing the columns by duration instead
  // stretched every line across the whole screen, which nobody can read.
  return `repeat(${slots},auto)`;
}

function grid(words, cls) {
  return words.map(w =>
    `<span class="${cls}" style="grid-column:${(w.i || 0) + 1}/span ${w.n || 1}">`
    // A space between the spans, not nothing: in flowing mode it is the space
    // between the words, and in grid mode whitespace is never a grid item.
    + `${esc(w.w)}</span>`).join(' ');
}

let aligned = localStorage.getItem('lines') === 'aligned';

function applyLayout() {
  $('play').classList.toggle('aligned', aligned);
  $('spacing').innerHTML = `lines <b>${aligned ? 'word over word' : 'flowing'}</b>`;
  if (aligned) fitLines();
}

// A long line can still be wider than the screen, so it is scaled to fit. Both
// rows are in one grid, so scaling the line scales them together and they stay
// aligned. Only the two lines that are laid out this way need measuring, and
// only when they change.
function fitLine(r) {
  if (!r) return;
  r.el.style.setProperty('--fit', '1');
  const room = $('rail').clientWidth - 28;
  if (room <= 0) return;
  const wide = r.el.scrollWidth;
  if (wide > room) r.el.style.setProperty('--fit', Math.max(0.4, room / wide).toFixed(3));
}

function fitLines() {
  fitLine(rows[Math.max(active, 0)]);
  fitLine(rows[Math.max(active, 0) + 1]);
}

$('spacing').onclick = () => {
  aligned = !aligned;
  try { localStorage.setItem('lines', aligned ? 'aligned' : 'flowing'); } catch (e) {}
  applyLayout();
};
addEventListener('resize', () => { if (aligned) fitLines(); });
applyLayout();

$('seek').oninput = e => { if (au.duration) au.currentTime = au.duration * e.target.value / 1000; };

// One rAF loop drives everything: which line is live, which words are lit, and
// where the rail sits. Nothing is animated by CSS transitions on colour --
// they fight with this and the highlight ends up lagging the audio.
function tick() {
  raf = requestAnimationFrame(tick);
  if (!show) return;
  const t = au.currentTime - offset / 1000;

  if (!au.seeking && au.duration) {
    $('seek').value = Math.round(1000 * au.currentTime / au.duration);
    $('tnow').textContent = clock(au.currentTime);
  }

  let i = -1;
  for (let k = 0; k < rows.length; k++) if (t >= rows[k].line.start - 0.25) i = k;

  const first = rows[0] ? rows[0].line.start : 0;
  const lead = first - t;
  $('count').textContent = (i < 0 && lead < 4 && lead > 0)
    ? '•'.repeat(Math.ceil(lead)) : '';

  if (i !== active) {
    active = i;
    rows.forEach((r, k) => {
      r.el.className = 'ln' + (r.line.uncertain ? ' unsure' : '')
        + (k === i ? ' on' : k < i ? ' done' : ' ahead')
        + (k === i + 1 ? ' next' : '')
        + (Math.abs(k - i) > 3 ? ' far' : '');
    });
    if (aligned) { fitLine(rows[Math.max(i, 0)]); fitLine(rows[Math.max(i, 0) + 1]); }
    const target = rows[Math.max(i, 0)];
    if (target) {
      $('inner').style.transition = 'transform .42s cubic-bezier(.2,.7,.3,1)';
      $('inner').style.transform =
        `translateY(${-(target.el.offsetTop + target.el.offsetHeight / 2)}px)`;
    }
  }
  if (i >= 0) {
    const r = rows[i];
    r.words.forEach((w, k) => r.spans[k].classList.toggle('lit', t >= w.t));
    // The original lights in step with the rewrite. Both sets of words sit on
    // the same slots, so watching them together is how you see which new word
    // takes the place of which old one -- which is the thing you sing from.
    r.owords.forEach((w, k) => {
      if (r.ospans[k]) r.ospans[k].classList.toggle('lit', t >= w.t);
    });
  }
}

// ── the card, and what Raz thinks of it ───────────────────────────────────

function openCard() {
  const c = show.d.card, e = c.exam;
  $('cscore').innerHTML = `${c.singable.toFixed(2)}<small>singability — out of 10</small>`;
  $('cbody').innerHTML = c.unsingable
    ? `<p class="note">Below the gate of 7. Nothing else is reported: a song nobody
       can sing has no comedy value and no fidelity worth discussing.</p>`
    : [
      metric('From the corpus', (c.corpus_fidelity * 100).toFixed(0) + '%', c.corpus_note),
      metric('Register gap', c.register_distance.toFixed(2),
        'five surface features — word length, function words, vocabulary, sentence length, numbers'),
      metric('Lines that parse', (c.grammar * 100).toFixed(0) + '%', c.grammar_note),
      metric('Bend honesty', c.honesty.toFixed(2),
        `${show.d.bends.length} declared, ${c.undeclared_bends.length} undeclared`),
      `<p class="note" style="margin-top:12px">fit ${e.fit.toFixed(2)} ·
        stress ${e.stress.toFixed(2)} · rhyme ${e.rhyme.toFixed(2)} ·
        vowel ${e.vowel.toFixed(2)}${c.excluded.length
          ? ` · ${c.excluded.length} line${c.excluded.length > 1 ? 's' : ''} excluded as uncertain`
          : ''}</p>`,
      show.d.bends.length ? '<h2>Where the tune had to bend</h2>' + show.d.bends.map(b =>
        `<div class="bend">line ${b.line}: wanted ${b.slots} syllables, got ${b.written}
         — ${esc(b.why)}</div>`).join('') : '',
    ].join('');
  $('card').classList.add('on');
}

const metric = (label, value, note) =>
  `<div class="metric"><span>${label}<br><small style="color:var(--dimmer)">${
    esc(note)}</small></span><b>${value}</b></div>`;

function openRate() {
  $('stars').innerHTML = '';
  for (let n = 1; n <= 10; n++) {
    const b = document.createElement('button');
    b.textContent = n;
    b.onclick = async () => {
      const r = await api('/api/rate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ref: show.ref, dressing: show.name, stars: n }),
      });
      $('rateNote').textContent = r.gap > 2
        ? `You said ${n}, the exam said ${r.machine.toFixed(1)}. That is more than two
           points apart, so this one is flagged — the exam is measuring the wrong thing here.`
        : `Thanks. The exam said ${r.machine.toFixed(1)}, so you are close to agreeing.`;
      [...$('stars').children].forEach(el => el.classList.remove('pick'));
      b.classList.add('pick');
      loadDisagreements();
    };
    $('stars').append(b);
  }
  $('rateSheet').classList.add('on');
}

const closeSheets = () =>
  document.querySelectorAll('.sheet').forEach(s => s.classList.remove('on'));

// A disagreement means the exam is measuring the wrong thing. They are shown,
// counted, and left alone.
async function loadDisagreements() {
  const rows = await api('/api/disagreements');
  $('disagree-link').style.display = rows.length ? 'block' : 'none';
  $('disagree-n').textContent = rows.length ? `(${rows.length})` : '';
  return rows;
}

async function openDisagreements() {
  const rows = await loadDisagreements();
  $('disagree-body').innerHTML = rows.map(r => metric(
    `${esc(r.song)}`,
    `${r.human} vs ${r.machine.toFixed(1)}`,
    `${esc(r.dressing)} — ${r.gap.toFixed(1)} points apart`)).join('');
  $('disagree').classList.add('on');
}

licenceLabel(0);
loadLibrary();
loadDisagreements();
