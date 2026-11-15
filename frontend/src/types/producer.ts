import type { StoryProducer } from './story';

export type ProducerSummary = StoryProducer & {
  genre: string;
  productionItems: string;
  profileImageUrl: string | null;
  careerStartYear: number;
  badges: string[];
};

export type ProducerProfile = ProducerSummary & {
  foundedYear: number;
  representativeName: string;
  intro: string;
  images: { id: number; url: string; sortOrder: number }[];
  hasPublicStory: boolean;
};
