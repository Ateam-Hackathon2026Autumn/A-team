export type StoryProducer = {
  id: number; businessName: string; prefectureName: string; city: string;
  coverImageUrl: string | null; acceptsExperience: boolean; recruiting: boolean;
};
export type Story = {
  id: number; producerId: number; category: { id: number; name: string };
  title: string; method: string | null; process: string | null; environment: string | null;
  reason: string | null; goal: string | null; updatedAt: string;
};
export type StoryArticle = Story & { producer: StoryProducer };
