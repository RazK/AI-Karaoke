export interface Song {
  id: string;
  title: string;
  artist: string;
  youtubeId: string;
  durationSeconds: number;
  lineCount: number;
}

export interface Dataset {
  id: string;
  label: string;
  description: string;
}

export interface LrcLine {
  startMs: number;
  text: string;
}

export interface GeneratedWord {
  word: string;
  syllables: number;
}

export interface LyricLine {
  lineIndex: number;
  startMs: number;
  syllableCount: number;
  original: GeneratedWord[];
  generated: GeneratedWord[];
}

export type Screen = 'picker' | 'generating' | 'karaoke';
