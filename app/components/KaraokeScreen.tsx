'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Song, Dataset, LyricLine, GeneratedWord } from '@/app/types';

const MAX_SYLLABLES_PER_ROW = 8;
const LAST_LINE_PAD_MS = 3000;

const MOCK_LYRICS: LyricLine[] = [
  {
    lineIndex: 0, startMs: 0, syllableCount: 5,
    original: [{ word: 'Is', syllables: 1 }, { word: 'this', syllables: 1 }, { word: 'the', syllables: 1 }, { word: 'real', syllables: 1 }, { word: 'life?', syllables: 1 }],
    generated: [{ word: 'Fix', syllables: 1 }, { word: 'the', syllables: 1 }, { word: 'shelf', syllables: 1 }, { word: 'right', syllables: 1 }, { word: 'now', syllables: 1 }],
  },
  {
    lineIndex: 1, startMs: 2550, syllableCount: 6,
    original: [{ word: 'Is', syllables: 1 }, { word: 'this', syllables: 1 }, { word: 'just', syllables: 1 }, { word: 'fan-', syllables: 1 }, { word: 'ta-', syllables: 1 }, { word: 'sy?', syllables: 1 }],
    generated: [{ word: 'Tigh-', syllables: 1 }, { word: 'ten', syllables: 1 }, { word: 'all', syllables: 1 }, { word: 'the', syllables: 1 }, { word: 'four', syllables: 1 }, { word: 'bolts', syllables: 1 }],
  },
  {
    lineIndex: 2, startMs: 5170, syllableCount: 5,
    original: [{ word: 'Caught', syllables: 1 }, { word: 'in', syllables: 1 }, { word: 'a', syllables: 1 }, { word: 'land-', syllables: 1 }, { word: 'slide', syllables: 1 }],
    generated: [{ word: 'Check', syllables: 1 }, { word: 'the', syllables: 1 }, { word: 'di-', syllables: 1 }, { word: 'a-', syllables: 1 }, { word: 'gram', syllables: 1 }],
  },
  {
    lineIndex: 3, startMs: 7630, syllableCount: 8,
    original: [{ word: 'No', syllables: 1 }, { word: 'es-cape', syllables: 2 }, { word: 'from', syllables: 1 }, { word: 're-al-i-ty', syllables: 4 }],
    generated: [{ word: 'Check', syllables: 1 }, { word: 'the', syllables: 1 }, { word: 'di-a-gram', syllables: 3 }, { word: 'care-ful-ly', syllables: 3 }],
  },
  {
    lineIndex: 4, startMs: 10220, syllableCount: 4,
    original: [{ word: 'O-pen', syllables: 2 }, { word: 'your', syllables: 1 }, { word: 'eyes', syllables: 1 }],
    generated: [{ word: 'Al-len', syllables: 2 }, { word: 'key', syllables: 1 }, { word: 'here', syllables: 1 }],
  },
];

// ── row-splitting helpers ─────────────────────────────────────────────────────

function findRowBreakPoints(gen: GeneratedWord[], max: number): number[] {
  const pts: number[] = [];
  let cum = 0;
  for (const w of gen) {
    if (cum > 0 && cum + w.syllables > max) pts.push(cum);
    cum += w.syllables;
  }
  return pts;
}

function splitAtBreakPoints(words: GeneratedWord[], pts: number[]): GeneratedWord[][] {
  if (!pts.length) return words.length ? [words] : [];
  const rows: GeneratedWord[][] = [];
  let cur: GeneratedWord[] = [], cum = 0, bi = 0;
  for (const w of words) {
    if (bi < pts.length && cum >= pts[bi]) { if (cur.length) rows.push(cur); cur = []; bi++; }
    cur.push(w); cum += w.syllables;
  }
  if (cur.length) rows.push(cur);
  return rows;
}

function buildAlignedRows(gen: GeneratedWord[], orig: GeneratedWord[], max: number) {
  const pts = findRowBreakPoints(gen, max);
  const gRows = splitAtBreakPoints(gen, pts);
  const oRows = splitAtBreakPoints(orig, pts);
  return gRows.map((genRow, i) => ({
    genRow,
    origRow: oRows[i] ?? [],
    cols: genRow.reduce((s, w) => s + w.syllables, 0),
  }));
}

function getOrigHiIdx(gen: GeneratedWord[], orig: GeneratedWord[], gi: number): number {
  const start = gen.slice(0, gi).reduce((s, w) => s + w.syllables, 0);
  let cum = 0;
  for (let i = 0; i < orig.length; i++) {
    if (start < cum + orig[i].syllables) return i;
    cum += orig[i].syllables;
  }
  return orig.length - 1;
}

// ── LyricLineItem ─────────────────────────────────────────────────────────────

function LyricLineItem({
  line, isCurrent, highlightedWordIndex, setRef,
}: {
  line: LyricLine;
  isCurrent: boolean;
  highlightedWordIndex: number | undefined;
  setRef: (el: HTMLDivElement | null) => void;
}) {
  const genSz = isCurrent ? '42px' : '22px';
  const genWt = isCurrent ? 800 : 600;
  const origSz = isCurrent ? '17px' : '12px';
  const colW = isCurrent ? 120 : 65;

  const origHi =
    isCurrent && highlightedWordIndex !== undefined
      ? getOrigHiIdx(line.generated, line.original, highlightedWordIndex)
      : -1;

  const rows = buildAlignedRows(line.generated, line.original, MAX_SYLLABLES_PER_ROW);
  let gOff = 0, oOff = 0;

  return (
    <div
      ref={setRef}
      style={{
        opacity: isCurrent ? 1 : 0.35,
        padding: isCurrent ? '18px 20px 20px' : '8px 20px',
        borderRadius: '12px',
        background: isCurrent ? 'rgba(167,139,250,0.10)' : 'transparent',
        boxShadow: isCurrent ? '0 0 40px rgba(167,139,250,0.25)' : 'none',
        transition: 'opacity 250ms ease, background 250ms ease, box-shadow 250ms ease, padding 250ms ease',
      }}
    >
      {rows.map(({ genRow, origRow, cols }, ri) => {
        const gs = gOff; gOff += genRow.length;
        const os = oOff; oOff += origRow.length;
        return (
          <div
            key={ri}
            style={{
              maxWidth: `${cols * colW}px`,
              width: '100%',
              margin: '0 auto',
              marginBottom: ri < rows.length - 1 ? '10px' : 0,
            }}
          >
            {/* Generated */}
            <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: '4px', marginBottom: '3px' }}>
              {genRow.map((w, wi) => {
                const hi = isCurrent && highlightedWordIndex === gs + wi;
                return (
                  <span
                    key={wi}
                    style={{
                      gridColumn: `span ${w.syllables}`,
                      fontSize: genSz, fontWeight: genWt,
                      color: hi ? '#FCD34D' : '#F8FAFC',
                      textShadow: hi ? '0 0 24px rgba(252,211,77,0.5)' : 'none',
                      textAlign: 'center', lineHeight: 1.1,
                      transition: 'color 80ms, text-shadow 80ms, font-size 250ms',
                    }}
                  >
                    {w.word}
                  </span>
                );
              })}
            </div>
            {/* Original — flex-centered so it never orphans when syllable counts mismatch */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', flexWrap: 'wrap' }}>
              {origRow.map((w, oi) => {
                const hi = isCurrent && origHi === os + oi;
                return (
                  <span
                    key={oi}
                    style={{
                      fontSize: origSz,
                      fontWeight: hi ? 600 : 400,
                      color: hi ? '#FDE68A' : '#94A3B8',
                      textShadow: hi ? '0 0 12px rgba(253,230,138,0.4)' : 'none',
                      lineHeight: 1.5,
                      transition: 'color 80ms, text-shadow 80ms, font-size 250ms',
                    }}
                  >
                    {w.word}
                  </span>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── KaraokeScreen ─────────────────────────────────────────────────────────────

const btnStyle: React.CSSProperties = {
  padding: '8px 14px', borderRadius: '8px',
  border: '1px solid rgba(255,255,255,0.15)',
  background: 'transparent', color: '#F8FAFC',
  fontSize: '13px', fontWeight: 500, cursor: 'pointer',
};

function fmtMs(ms: number) {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

export default function KaraokeScreen({
  song, dataset, lyrics, onRegenerate, onNewCombo,
}: {
  song: Song; dataset: Dataset; lyrics: LyricLine[];
  onRegenerate: () => void; onNewCombo: () => void;
}) {
  const display = lyrics.length > 0 ? lyrics : MOCK_LYRICS;
  const totalMs = display[display.length - 1].startMs + LAST_LINE_PAD_MS;

  const [currentMs, setCurrentMs] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isSeeking, setIsSeeking] = useState(false);

  const currentMsRef = useRef(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const lineRefs = useRef<(HTMLDivElement | null)[]>([]);
  const userScrolling = useRef(false);
  const progScroll = useRef(false);
  const scrollResetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isSeekingRef = useRef(false);

  // Derived: current line index
  const curIdx = display.reduce((acc, l, i) => (l.startMs <= currentMs ? i : acc), 0);

  // Derived: word highlight
  const curLine = display[curIdx];
  const lineStart = curLine.startMs;
  const lineEnd = display[curIdx + 1]?.startMs ?? lineStart + LAST_LINE_PAD_MS;
  const lineDur = lineEnd - lineStart;
  const lineElapsed = Math.max(0, currentMs - lineStart);
  const totalSyl = curLine.generated.reduce((s, w) => s + w.syllables, 0);
  let cumSyl = 0, hiWord = 0;
  for (let i = 0; i < curLine.generated.length; i++) {
    if (lineElapsed >= (cumSyl / totalSyl) * lineDur) hiWord = i;
    cumSyl += curLine.generated[i].syllables;
  }

  // Playback interval — restarts when isPlaying or isSeeking changes
  useEffect(() => {
    if (!isPlaying || isSeeking) return;
    const wall0 = Date.now() - currentMsRef.current;
    const id = setInterval(() => {
      const t = Date.now() - wall0;
      if (t >= totalMs) {
        currentMsRef.current = totalMs;
        setCurrentMs(totalMs);
        setIsPlaying(false);
        return;
      }
      currentMsRef.current = t;
      setCurrentMs(t);
    }, 50);
    return () => clearInterval(id);
  }, [isPlaying, isSeeking, totalMs]);

  // Auto-scroll to current line (skips if user is scrolling)
  useEffect(() => {
    if (userScrolling.current) return;
    const el = lineRefs.current[curIdx];
    const c = scrollRef.current;
    if (!el || !c) return;
    const top = c.scrollTop + el.getBoundingClientRect().top
      - c.getBoundingClientRect().top
      - c.clientHeight / 2
      + el.clientHeight / 2;
    progScroll.current = true;
    c.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    if (scrollResetTimer.current) clearTimeout(scrollResetTimer.current);
    scrollResetTimer.current = setTimeout(() => { progScroll.current = false; }, 500);
  }, [curIdx]);

  // User scroll detection — ignores programmatic scrolls and seeks
  const handleScroll = useCallback(() => {
    if (progScroll.current || isSeekingRef.current) return;
    userScrolling.current = true;
    if (scrollResetTimer.current) clearTimeout(scrollResetTimer.current);
    scrollResetTimer.current = setTimeout(() => { userScrolling.current = false; }, 3000);
  }, []);

  const seekTo = (ms: number) => {
    const t = Math.max(0, Math.min(ms, totalMs));
    currentMsRef.current = t;
    setCurrentMs(t);
  };

  const togglePlay = () => {
    if (currentMs >= totalMs) {
      currentMsRef.current = 0;
      setCurrentMs(0);
      setIsPlaying(true);
    } else {
      setIsPlaying((p) => !p);
    }
  };

  return (
    <div style={{ height: '100svh', display: 'flex', flexDirection: 'column', position: 'relative', zIndex: 1, overflow: 'hidden' }}>
      {/* Top bar */}
      <div style={{ height: '56px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(12px)', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
        <span style={{ fontSize: '15px', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '60%' }}>
          <span style={{ whiteSpace: 'nowrap' }}>🎵 {song.title}</span>
          {' × '}
          <span style={{ whiteSpace: 'nowrap' }}>📋 {dataset.label}</span>
        </span>
        <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
          <button onClick={onRegenerate} style={btnStyle}>Regenerate</button>
          <button onClick={onNewCombo} style={btnStyle}>New Combo</button>
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', display: 'flex' }}>
        {/* Scrollable lyrics list */}
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          style={{ flex: 1, overflowY: 'auto', padding: '32px 24px 0', display: 'flex', flexDirection: 'column', gap: '6px' }}
        >
          {display.map((line, i) => (
            <LyricLineItem
              key={i}
              line={line}
              isCurrent={i === curIdx}
              highlightedWordIndex={i === curIdx ? hiWord : undefined}
              setRef={(el) => { lineRefs.current[i] = el; }}
            />
          ))}
          {/* Trailing space so the last line can scroll to center */}
          <div style={{ height: '50vh', flexShrink: 0 }} />
        </div>
      </div>

      {/* Bottom: play + seekbar */}
      <div style={{ height: '56px', flexShrink: 0, display: 'flex', alignItems: 'center', padding: '0 16px', gap: '12px', borderTop: '1px solid rgba(255,255,255,0.08)', background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(12px)' }}>
        <button
          onClick={togglePlay}
          aria-label={isPlaying ? 'Pause' : 'Play'}
          style={{ background: 'none', border: 'none', color: '#F8FAFC', fontSize: '22px', cursor: 'pointer', lineHeight: 1, padding: '4px', flexShrink: 0 }}
        >
          {isPlaying ? '⏸' : '▶'}
        </button>

        <input
          type="range"
          min={0}
          max={totalMs}
          value={currentMs}
          onPointerDown={() => { isSeekingRef.current = true; setIsSeeking(true); userScrolling.current = false; }}
          onPointerUp={() => { isSeekingRef.current = false; setIsSeeking(false); }}
          onChange={(e) => seekTo(Number(e.target.value))}
          style={{ flex: 1, accentColor: '#7C3AED', cursor: 'pointer' }}
        />

        <span style={{ color: '#94A3B8', fontSize: '13px', flexShrink: 0, fontVariantNumeric: 'tabular-nums' }}>
          {fmtMs(currentMs)} / {fmtMs(totalMs)}
        </span>
      </div>
    </div>
  );
}
