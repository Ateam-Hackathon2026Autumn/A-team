import ApiError from './apiError';
import { contentItems, contentJson } from './publicContentApi';
import type { Story, StoryArticle, StoryProducer } from '../types/story';

// 公開ストーリーの一覧APIがないため、生産者ごとの公開APIから取得する。
// /learn/:storyId は story.id で照合し、producerId と同一とは仮定しない。
export async function getStories(signal?: AbortSignal): Promise<StoryArticle[]> {
  const producers = await contentItems<StoryProducer>('/api/v1/producers', signal);
  const stories = await Promise.all(producers.map(async producer => {
    try {
      const story = await contentJson<Story>(`/api/v1/producers/${producer.id}/story`, signal);
      return { ...story, producer };
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  }));
  return stories.filter((story): story is StoryArticle => story !== null);
}
export async function getStory(id: number, signal?: AbortSignal) {
  const story = (await getStories(signal)).find(item => item.id === id);
  if (!story) throw new Error('ストーリーが見つかりません。');
  return story;
}
