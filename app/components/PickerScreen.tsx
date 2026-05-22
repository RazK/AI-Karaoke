'use client';

import { useState, useMemo } from 'react';
import { Song, Dataset } from '@/app/types';
import songsData from '@/data/songs.json';
import datasetsData from '@/data/datasets.json';

const songs: Song[] = songsData as Song[];
const datasets: Dataset[] = datasetsData as Dataset[];

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

interface PickerScreenProps {
  onGenerate: (song: Song, dataset: Dataset) => void;
}

export default function PickerScreen({ onGenerate }: PickerScreenProps) {
  const [selectedSong, setSelectedSong] = useState<Song | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [songSearch, setSongSearch] = useState('');
  const [datasetSearch, setDatasetSearch] = useState('');

  const filteredSongs = useMemo(() => {
    const q = songSearch.toLowerCase();
    if (!q) return songs;
    return songs.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.artist.toLowerCase().includes(q)
    );
  }, [songSearch]);

  const filteredDatasets = useMemo(() => {
    const q = datasetSearch.toLowerCase();
    if (!q) return datasets;
    return datasets.filter(
      (d) =>
        d.label.toLowerCase().includes(q) ||
        d.description.toLowerCase().includes(q)
    );
  }, [datasetSearch]);

  const canGenerate = selectedSong !== null && selectedDataset !== null;

  const handleGenerate = () => {
    if (selectedSong && selectedDataset) {
      onGenerate(selectedSong, selectedDataset);
    }
  };

  return (
    <div
      style={{
        height: '100svh',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        zIndex: 1,
      }}
    >
      {/* Two-column layout */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Songs column */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            padding: '24px 16px 0 24px',
            overflow: 'hidden',
            borderRight: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <h2
            style={{
              fontSize: '20px',
              fontWeight: 700,
              color: '#F8FAFC',
              marginBottom: '12px',
              flexShrink: 0,
            }}
          >
            🎵 Songs
          </h2>

          {/* Search */}
          <input
            type="text"
            placeholder="Search songs..."
            value={songSearch}
            onChange={(e) => setSongSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.08)',
              background: 'rgba(255,255,255,0.05)',
              color: '#F8FAFC',
              fontSize: '14px',
              outline: 'none',
              marginBottom: '12px',
              flexShrink: 0,
            }}
          />

          {/* Card list */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              overflowY: 'auto',
              flex: 1,
              paddingBottom: '16px',
            }}
          >
            {filteredSongs.length === 0 ? (
              <p style={{ color: '#94A3B8', fontSize: '14px', textAlign: 'center', marginTop: '24px' }}>
                No matches
              </p>
            ) : (
              filteredSongs.map((song) => {
                const isSelected = selectedSong?.id === song.id;
                return (
                  <button
                    key={song.id}
                    onClick={() => setSelectedSong(song)}
                    style={{
                      width: '100%',
                      padding: '16px',
                      borderRadius: '16px',
                      border: isSelected
                        ? '1px solid rgba(124,58,237,0.6)'
                        : '1px solid rgba(255,255,255,0.08)',
                      background: isSelected
                        ? 'rgba(124,58,237,0.08)'
                        : 'rgba(255,255,255,0.05)',
                      backdropFilter: 'blur(12px)',
                      boxShadow: isSelected ? '0 0 20px rgba(124,58,237,0.3)' : 'none',
                      cursor: 'pointer',
                      textAlign: 'left',
                      transform: isSelected ? 'scale(1.02)' : 'scale(1)',
                      transition: 'transform 120ms ease-out, border 120ms ease-out, background 120ms ease-out, box-shadow 120ms ease-out',
                      minHeight: '48px',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '18px',
                        fontWeight: 600,
                        color: '#F8FAFC',
                        marginBottom: '4px',
                      }}
                    >
                      {song.title}
                    </div>
                    <div style={{ fontSize: '14px', color: '#94A3B8' }}>
                      {song.artist} · {formatDuration(song.durationSeconds)}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Datasets column */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            padding: '24px 24px 0 16px',
            overflow: 'hidden',
          }}
        >
          <h2
            style={{
              fontSize: '20px',
              fontWeight: 700,
              color: '#F8FAFC',
              marginBottom: '12px',
              flexShrink: 0,
            }}
          >
            📋 Datasets
          </h2>

          {/* Search */}
          <input
            type="text"
            placeholder="Search datasets..."
            value={datasetSearch}
            onChange={(e) => setDatasetSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.08)',
              background: 'rgba(255,255,255,0.05)',
              color: '#F8FAFC',
              fontSize: '14px',
              outline: 'none',
              marginBottom: '12px',
              flexShrink: 0,
            }}
          />

          {/* Card list */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              overflowY: 'auto',
              flex: 1,
              paddingBottom: '16px',
            }}
          >
            {filteredDatasets.length === 0 ? (
              <p style={{ color: '#94A3B8', fontSize: '14px', textAlign: 'center', marginTop: '24px' }}>
                No matches
              </p>
            ) : (
              filteredDatasets.map((dataset) => {
                const isSelected = selectedDataset?.id === dataset.id;
                return (
                  <button
                    key={dataset.id}
                    onClick={() => setSelectedDataset(dataset)}
                    style={{
                      width: '100%',
                      padding: '16px',
                      borderRadius: '16px',
                      border: isSelected
                        ? '1px solid rgba(6,182,212,0.6)'
                        : '1px solid rgba(255,255,255,0.08)',
                      background: isSelected
                        ? 'rgba(6,182,212,0.08)'
                        : 'rgba(255,255,255,0.05)',
                      backdropFilter: 'blur(12px)',
                      boxShadow: isSelected ? '0 0 20px rgba(6,182,212,0.3)' : 'none',
                      cursor: 'pointer',
                      textAlign: 'left',
                      transform: isSelected ? 'scale(1.02)' : 'scale(1)',
                      transition: 'transform 120ms ease-out, border 120ms ease-out, background 120ms ease-out, box-shadow 120ms ease-out',
                      minHeight: '48px',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '18px',
                        fontWeight: 600,
                        color: '#F8FAFC',
                        marginBottom: '4px',
                      }}
                    >
                      {dataset.label}
                    </div>
                    <div style={{ fontSize: '14px', color: '#94A3B8' }}>
                      {dataset.description}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Generate button pinned to bottom */}
      <div style={{ padding: '16px 24px', flexShrink: 0 }}>
        <button
          onClick={handleGenerate}
          disabled={!canGenerate}
          style={{
            width: '100%',
            height: '56px',
            borderRadius: '12px',
            border: 'none',
            background: canGenerate
              ? 'linear-gradient(135deg, #7C3AED, #2563EB)'
              : 'linear-gradient(135deg, #7C3AED, #2563EB)',
            color: '#F8FAFC',
            fontSize: '15px',
            fontWeight: 500,
            cursor: canGenerate ? 'pointer' : 'not-allowed',
            opacity: canGenerate ? 1 : 0.4,
            pointerEvents: canGenerate ? 'auto' : 'none',
            transition: 'filter 100ms ease, transform 100ms ease',
          }}
          onMouseEnter={(e) => {
            if (canGenerate) {
              (e.currentTarget as HTMLButtonElement).style.filter = 'brightness(1.1)';
              (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-1px)';
            }
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.filter = 'brightness(1)';
            (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)';
          }}
        >
          {canGenerate
            ? `Generate: ${selectedSong!.title} × ${selectedDataset!.label}`
            : 'Select a song and dataset to generate'}
        </button>
      </div>
    </div>
  );
}
