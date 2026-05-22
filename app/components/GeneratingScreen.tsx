'use client';

import { useState, useEffect, useRef } from 'react';
import { Song, Dataset, LyricLine } from '@/app/types';

const FLAVOR_TEXTS = [
  'Counting syllables…',
  'Consulting the manual…',
  'The AI is taking notes…',
  'Measuring in millimeters…',
  'Cross-referencing the reviews…',
];

const MOCK_LYRICS: LyricLine[] = [
  {
    lineIndex: 0,
    startMs: 0,
    syllableCount: 6,
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
    syllableCount: 7,
    original: [
      { word: 'No', syllables: 1 },
      { word: 'es-', syllables: 1 },
      { word: 'cape', syllables: 1 },
      { word: 'from', syllables: 1 },
      { word: 're-', syllables: 1 },
      { word: 'a-', syllables: 1 },
      { word: 'li-ty', syllables: 2 },
    ],
    generated: [
      { word: 'In-', syllables: 1 },
      { word: 'sert', syllables: 1 },
      { word: 'screw', syllables: 1 },
      { word: 'type', syllables: 1 },
      { word: 'A', syllables: 1 },
      { word: 'here', syllables: 1 },
      { word: 'care-ful-ly', syllables: 3 },
    ],
  },
  {
    lineIndex: 4,
    startMs: 10220,
    syllableCount: 4,
    original: [
      { word: 'O-', syllables: 1 },
      { word: 'pen', syllables: 1 },
      { word: 'your', syllables: 1 },
      { word: 'eyes', syllables: 1 },
    ],
    generated: [
      { word: 'Al-', syllables: 1 },
      { word: 'len', syllables: 1 },
      { word: 'key', syllables: 1 },
      { word: 'here', syllables: 1 },
    ],
  },
];

interface GeneratingScreenProps {
  song: Song;
  dataset: Dataset;
  onDone: (lyrics: LyricLine[]) => void;
}

export default function GeneratingScreen({ song, dataset, onDone }: GeneratingScreenProps) {
  const [progress, setProgress] = useState(0);
  const [flavorIndex, setFlavorIndex] = useState(0);
  const [flavorOpacity, setFlavorOpacity] = useState(1);
  const doneCalledRef = useRef(false);

  // Progress animation: 0 → 88% over 3s
  useEffect(() => {
    const startTime = Date.now();
    const duration = 3000;
    const targetProgress = 88;

    const rafId = { current: 0 };

    function animate() {
      const elapsed = Date.now() - startTime;
      const fraction = Math.min(elapsed / duration, 1);
      const currentProgress = Math.round(fraction * targetProgress);
      setProgress(currentProgress);

      if (fraction < 1) {
        rafId.current = requestAnimationFrame(animate);
      } else {
        // Hold at 88%, then jump to 100 and call onDone
        if (!doneCalledRef.current) {
          doneCalledRef.current = true;
          setTimeout(() => {
            setProgress(100);
            setTimeout(() => {
              onDone(MOCK_LYRICS);
            }, 200);
          }, 200);
        }
      }
    }

    rafId.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafId.current);
  }, [onDone]);

  // Flavor text rotation every 2.5s with fade
  useEffect(() => {
    const interval = setInterval(() => {
      // Fade out
      setFlavorOpacity(0);
      setTimeout(() => {
        setFlavorIndex((i) => (i + 1) % FLAVOR_TEXTS.length);
        // Fade in
        setFlavorOpacity(1);
      }, 300);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      style={{
        height: '100svh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        zIndex: 1,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '24px',
          width: '100%',
          maxWidth: '480px',
          padding: '0 24px',
        }}
      >
        {/* Combo name */}
        <h1
          style={{
            fontSize: '28px',
            fontWeight: 700,
            color: '#F8FAFC',
            textAlign: 'center',
            margin: 0,
          }}
        >
          🎵 {song.title} × 📋 {dataset.label}
        </h1>

        {/* Progress bar */}
        <div style={{ width: '60%', position: 'relative' }}>
          <div
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            style={{
              width: '100%',
              height: '8px',
              borderRadius: '999px',
              background: 'rgba(255,255,255,0.1)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                borderRadius: '999px',
                background: 'linear-gradient(90deg, #7C3AED, #2563EB)',
                width: `${progress}%`,
                transition: 'width 100ms linear',
              }}
            />
          </div>
        </div>

        {/* Flavor text */}
        <p
          style={{
            fontStyle: 'italic',
            color: '#94A3B8',
            fontSize: '16px',
            textAlign: 'center',
            margin: 0,
            opacity: flavorOpacity,
            transition: 'opacity 300ms ease',
          }}
        >
          {FLAVOR_TEXTS[flavorIndex]}
        </p>
      </div>
    </div>
  );
}
