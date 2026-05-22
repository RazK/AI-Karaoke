'use client';

import { useState, useEffect, useRef } from 'react';
import { Song, Dataset, LyricLine, GeneratedWord } from '@/app/types';

// Max syllables before a line splits into a new visual sub-row.
// Both generated and original split at the same syllable boundary.
const MAX_SYLLABLES_PER_ROW = 8;

const MOCK_LYRICS: LyricLine[] = [
  {
    lineIndex: 0,
    startMs: 0,
    syllableCount: 5,
    original: [
      { word: 'Is', syllables: 1 },
      { word: 'this', syllables: 1 },
      { word: 'the', syllables: 1 },
      { word: 'real', syllables: 1 },
      { word: 'life?', syllables: 1 },
    ],
    generated: [
      { word: 'Fix', syllables: 1 },
      { word: 'the', syllables: 1 },
      { word: 'shelf', syllables: 1 },
      { word: 'right', syllables: 1 },
      { word: 'now', syllables: 1 },
    ],
  },
  {
    lineIndex: 1,
    startMs: 2550,
    syllableCount: 6,
    original: [
      { word: 'Is', syllables: 1 },
      { word: 'this', syllables: 1 },
      { word: 'just', syllables: 1 },
      { word: 'fan-', syllables: 1 },
      { word: 'ta-', syllables: 1 },
      { word: 'sy?', syllables: 1 },
    ],
    generated: [
      { word: 'Tigh-', syllables: 1 },
      { word: 'ten', syllables: 1 },
      { word: 'all', syllables: 1 },
      { word: 'the', syllables: 1 },
      { word: 'four', syllables: 1 },
      { word: 'bolts', syllables: 1 },
    ],
  },
  {
    lineIndex: 2,
    startMs: 5170,
    syllableCount: 5,
    original: [
      { word: 'Caught', syllables: 1 },
      { word: 'in', syllables: 1 },
      { word: 'a', syllables: 1 },
      { word: 'land-', syllables: 1 },
      { word: 'slide', syllables: 1 },
    ],
    generated: [
      { word: 'Check', syllables: 1 },
      { word: 'the', syllables: 1 },
      { word: 'di-', syllables: 1 },
      { word: 'a-', syllables: 1 },
      { word: 'gram', syllables: 1 },
    ],
  },
  {
    lineIndex: 3,
    startMs: 7630,
    syllableCount: 8,
    original: [
      { word: 'No', syllables: 1 },
      { word: 'es-cape', syllables: 2 },
      { word: 'from', syllables: 1 },
      { word: 're-al-i-ty', syllables: 4 },
    ],
    generated: [
      { word: 'Check', syllables: 1 },
      { word: 'the', syllables: 1 },
      { word: 'di-a-gram', syllables: 3 },
      { word: 'care-ful-ly', syllables: 3 },
    ],
  },
  {
    lineIndex: 4,
    startMs: 10220,
    syllableCount: 4,
    original: [
      { word: 'O-pen', syllables: 2 },
      { word: 'your', syllables: 1 },
      { word: 'eyes', syllables: 1 },
    ],
    generated: [
      { word: 'Al-len', syllables: 2 },
      { word: 'key', syllables: 1 },
      { word: 'here', syllables: 1 },
    ],
  },
];

// Compute how many syllables go in each visual row given a max per row.
function computeRowSizes(totalSyllables: number, maxPerRow: number): number[] {
  const rows: number[] = [];
  let remaining = totalSyllables;
  while (remaining > 0) {
    rows.push(Math.min(remaining, maxPerRow));
    remaining -= maxPerRow;
  }
  return rows;
}

// Split words greedily into rows matching the given row sizes.
// Generated and original must use the same rowSizes so they wrap together.
function splitWordsIntoRows(words: GeneratedWord[], rowSizes: number[]): GeneratedWord[][] {
  const rows: GeneratedWord[][] = [];
  let wordIdx = 0;
  for (const targetSize of rowSizes) {
    const row: GeneratedWord[] = [];
    let rowSyls = 0;
    while (wordIdx < words.length && rowSyls + words[wordIdx].syllables <= targetSize) {
      row.push(words[wordIdx]);
      rowSyls += words[wordIdx].syllables;
      wordIdx++;
    }
    if (row.length > 0) rows.push(row);
  }
  if (wordIdx < words.length) rows.push(words.slice(wordIdx));
  return rows;
}

interface LyricRowProps {
  line: LyricLine;
  role: 'prev' | 'current' | 'next';
  highlightedWordIndex?: number;
}

function LyricRow({ line, role, highlightedWordIndex }: LyricRowProps) {
  const isCurrent = role === 'current';
  const isPrev = role === 'prev';

  const opacity = isCurrent ? 1 : isPrev ? 0.2 : 0.4;
  const genFontSize = isCurrent ? '52px' : '36px';
  const genFontWeight = isCurrent ? 800 : 700;
  const origFontSize = isCurrent ? '22px' : '16px';
  const wordColor = isCurrent ? '#F8FAFC' : '#3F3F46';
  const origColor = isCurrent ? '#94A3B8' : '#3F3F46';

  // Derive syllable count from actual words — robust against mismatched metadata
  const totalSyllables = line.generated.reduce((s, w) => s + w.syllables, 0);
  const rowSizes = computeRowSizes(totalSyllables, MAX_SYLLABLES_PER_ROW);
  const genRows = splitWordsIntoRows(line.generated, rowSizes);
  const origRows = splitWordsIntoRows(line.original, rowSizes);

  let wordOffset = 0;

  return (
    <div
      style={{
        opacity,
        padding: '8px 16px',
        borderRadius: '8px',
        background: isCurrent ? 'rgba(167,139,250,0.12)' : 'transparent',
        boxShadow: isCurrent ? '0 0 24px rgba(167,139,250,0.4)' : 'none',
        transition: 'opacity 150ms ease, background 150ms ease, box-shadow 150ms ease',
      }}
    >
      {rowSizes.map((_, rowIdx) => {
        const genRow = genRows[rowIdx] ?? [];
        const origRow = origRows[rowIdx] ?? [];
        const rowStartWordIdx = wordOffset;
        wordOffset += genRow.length;
        const rowCols = genRow.reduce((s, w) => s + w.syllables, 0);

        return (
          <div key={rowIdx} style={{ marginBottom: rowIdx < rowSizes.length - 1 ? '12px' : 0 }}>
            {/* Generated line */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${rowCols}, 1fr)`,
                gap: '4px',
                marginBottom: '4px',
              }}
            >
              {genRow.map((word, wIdx) => {
                const globalIdx = rowStartWordIdx + wIdx;
                const isHighlighted = isCurrent && highlightedWordIndex === globalIdx;
                return (
                  <span
                    key={wIdx}
                    style={{
                      gridColumn: `span ${word.syllables}`,
                      fontSize: genFontSize,
                      fontWeight: genFontWeight,
                      color: isHighlighted ? '#FCD34D' : wordColor,
                      textShadow: isHighlighted ? '0 0 20px rgba(252,211,77,0.5)' : 'none',
                      textAlign: 'center',
                      lineHeight: 1.1,
                      transition: 'color 80ms ease, text-shadow 80ms ease',
                    }}
                  >
                    {word.word}
                  </span>
                );
              })}
            </div>

            {/* Original line — same grid as generated, so syllables align vertically */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${rowCols}, 1fr)`,
                gap: '4px',
              }}
            >
              {origRow.map((word, wIdx) => (
                <span
                  key={wIdx}
                  style={{
                    gridColumn: `span ${word.syllables}`,
                    fontSize: origFontSize,
                    fontWeight: 400,
                    color: origColor,
                    textAlign: 'center',
                    lineHeight: 1.4,
                  }}
                >
                  {word.word}
                </span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

interface KaraokeScreenProps {
  song: Song;
  dataset: Dataset;
  lyrics: LyricLine[];
  onRegenerate: () => void;
  onNewCombo: () => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function KaraokeScreen({
  song,
  dataset,
  lyrics,
  onRegenerate,
  onNewCombo,
}: KaraokeScreenProps) {
  const displayLyrics = lyrics.length > 0 ? lyrics : MOCK_LYRICS;
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentLineIndex, setCurrentLineIndex] = useState(0);
  const [highlightedWordIndex, setHighlightedWordIndex] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const LINE_DURATION_MS = 3000;

  // Phase 1: cycle through lines every 3s
  useEffect(() => {
    if (!isPlaying) return;
    intervalRef.current = setInterval(() => {
      setCurrentLineIndex((i) => (i + 1) % displayLyrics.length);
    }, LINE_DURATION_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, displayLyrics.length]);

  // Word highlight: advance each word proportionally by its syllable count
  useEffect(() => {
    if (!isPlaying) return;
    setHighlightedWordIndex(0);

    const line = displayLyrics[currentLineIndex];
    const totalSyllables = line.generated.reduce((s, w) => s + w.syllables, 0);
    const timeouts: ReturnType<typeof setTimeout>[] = [];
    let cumSyllables = 0;

    line.generated.forEach((word, i) => {
      const startMs = (cumSyllables / totalSyllables) * LINE_DURATION_MS;
      if (startMs > 0) {
        timeouts.push(setTimeout(() => setHighlightedWordIndex(i), startMs));
      }
      cumSyllables += word.syllables;
    });

    return () => timeouts.forEach(clearTimeout);
  }, [currentLineIndex, isPlaying, displayLyrics]);

  const handlePlay = () => {
    setCurrentLineIndex(0);
    setHighlightedWordIndex(0);
    setIsPlaying(true);
  };

  const prevLine = currentLineIndex > 0 ? displayLyrics[currentLineIndex - 1] : null;
  const currentLine = displayLyrics[currentLineIndex];
  const nextLine =
    currentLineIndex < displayLyrics.length - 1 ? displayLyrics[currentLineIndex + 1] : null;

  const comboLabel = `🎵 ${song.title} × 📋 ${dataset.label}`;
  const totalDuration = formatTime(song.durationSeconds);

  return (
    <div
      style={{
        height: '100svh',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        zIndex: 1,
        overflow: 'hidden',
      }}
    >
      {/* Top bar */}
      <div
        style={{
          height: '56px',
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px',
          background: 'rgba(255,255,255,0.05)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        <span
          style={{
            color: '#F8FAFC',
            fontSize: '15px',
            fontWeight: 500,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: '60%',
          }}
        >
          {comboLabel}
        </span>
        <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
          <button
            onClick={onRegenerate}
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.15)',
              background: 'transparent',
              color: '#F8FAFC',
              fontSize: '13px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Regenerate
          </button>
          <button
            onClick={onNewCombo}
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.15)',
              background: 'transparent',
              color: '#F8FAFC',
              fontSize: '13px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            New Combo
          </button>
        </div>
      </div>

      {/* Main content */}
      <div style={{ flex: 1, display: 'flex', position: 'relative', overflow: 'hidden' }}>
        {/* YouTube placeholder — top right */}
        <div
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            width: '200px',
            height: '120px',
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(255,255,255,0.05)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#94A3B8',
            fontSize: '14px',
            zIndex: 2,
          }}
        >
          ▶ YouTube
        </div>

        {/* Lyric area */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px 240px 16px 24px',
          }}
        >
          {!isPlaying ? (
            <button
              onClick={handlePlay}
              style={{
                padding: '20px 48px',
                borderRadius: '16px',
                border: '2px solid rgba(124,58,237,0.6)',
                background: 'rgba(124,58,237,0.15)',
                color: '#F8FAFC',
                fontSize: '24px',
                fontWeight: 700,
                cursor: 'pointer',
                backdropFilter: 'blur(12px)',
              }}
            >
              ▶ Play
            </button>
          ) : (
            // key change triggers the CSS slide-in animation on every line advance
            <div
              key={currentLineIndex}
              className="lyrics-slide-in"
              style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '16px' }}
            >
              {prevLine && <LyricRow line={prevLine} role="prev" />}
              {currentLine && (
                <LyricRow
                  line={currentLine}
                  role="current"
                  highlightedWordIndex={highlightedWordIndex}
                />
              )}
              {nextLine && <LyricRow line={nextLine} role="next" />}
            </div>
          )}
        </div>
      </div>

      {/* Bottom progress bar */}
      <div
        style={{
          height: '48px',
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          gap: '12px',
          borderTop: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        <div
          style={{
            flex: 1,
            height: '6px',
            borderRadius: '999px',
            background: 'rgba(255,255,255,0.1)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: '0%',
              borderRadius: '999px',
              background: 'linear-gradient(90deg, #7C3AED, #06B6D4)',
            }}
          />
        </div>
        <span style={{ color: '#94A3B8', fontSize: '13px', flexShrink: 0 }}>
          0:00 / {totalDuration}
        </span>
      </div>
    </div>
  );
}
