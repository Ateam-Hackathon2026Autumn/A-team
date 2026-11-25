import type { StoryProducer } from './story';

export type ProducerSummary = StoryProducer & {
  prefectureId?: number;
  genre: string;
  productionItems: string;
  profileImageUrl: string | null;
  careerStartYear: number | null;
  foundedYear?: number | null;
  badges: string[];
  hasPublicStory?: boolean;
  isFavorited?: boolean;
};

export type ProducerProfile = ProducerSummary & {
  foundedYear: number | null;
  representativeName: string;
  intro: string;
  images: { id: number; url: string; sortOrder: number }[];
  hasPublicStory: boolean;
  isFavorited?: boolean;
  craft?: string | null;
  reason?: string | null;
  goal?: string | null;
};
