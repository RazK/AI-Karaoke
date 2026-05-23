'use client';

import { useState } from 'react';
import { Song, Dataset, LyricLine, Screen } from '@/app/types';
import PickerScreen from '@/app/components/PickerScreen';
import GeneratingScreen from '@/app/components/GeneratingScreen';
import KaraokeScreen from '@/app/components/KaraokeScreen';

type AppState = {
  screen: Screen;
  selectedSong: Song | null;
  selectedDataset: Dataset | null;
  lyrics: LyricLine[] | null;
};

export default function Home() {
  const [state, setState] = useState<AppState>({
    screen: 'picker',
    selectedSong: null,
    selectedDataset: null,
    lyrics: null,
  });

  const handleGenerate = (song: Song, dataset: Dataset) => {
    setState({
      screen: 'generating',
      selectedSong: song,
      selectedDataset: dataset,
      lyrics: null,
    });
  };

  const handleGenerateDone = (lyrics: LyricLine[]) => {
    setState((prev) => ({
      ...prev,
      screen: 'karaoke',
      lyrics,
    }));
  };

  const handleRegenerate = () => {
    setState((prev) => ({
      ...prev,
      screen: 'generating',
      lyrics: null,
    }));
  };

  const handleNewCombo = () => {
    setState({
      screen: 'picker',
      selectedSong: null,
      selectedDataset: null,
      lyrics: null,
    });
  };

  if (state.screen === 'picker') {
    return <PickerScreen onGenerate={handleGenerate} />;
  }

  if (state.screen === 'generating' && state.selectedSong && state.selectedDataset) {
    return (
      <GeneratingScreen
        song={state.selectedSong}
        dataset={state.selectedDataset}
        onDone={handleGenerateDone}
      />
    );
  }

  if (state.screen === 'karaoke' && state.selectedSong && state.selectedDataset && state.lyrics) {
    return (
      <KaraokeScreen
        song={state.selectedSong}
        dataset={state.selectedDataset}
        lyrics={state.lyrics}
        onRegenerate={handleRegenerate}
        onNewCombo={handleNewCombo}
      />
    );
  }

  // Fallback
  return <PickerScreen onGenerate={handleGenerate} />;
}
