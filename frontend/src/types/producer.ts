import type { StoryProducer } from './story';

export type ProducerSummary = StoryProducer & {
  genre: string;
  productionItems: string;
  profileImageUrl: string | null;
  careerStartYear: number;
  badges: string[];
};
