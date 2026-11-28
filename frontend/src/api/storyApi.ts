import ApiError from './apiError';
import type { ApiFetchOptions } from './client';
import { contentItems, contentJson } from './publicContentApi';
import type { Story, StoryArticle, StoryProducer } from '../types/story';

// 公開ストーリーの一覧APIがないため、生産者ごとの公開APIから取得する。
// 生産者一覧は hasStory=true（公開中のストーリーがある生産者だけ）で取り、むだな 404 を出さない。
// /learn/:storyId は story.id で照合し、producerId と同一とは仮定しない。
export async function getStories(
  signal?: AbortSignal,
  options?: ApiFetchOptions,
): Promise<StoryArticle[]> {
  const producers = await contentItems<StoryProducer>(
    '/api/v1/producers',
    signal,
    { hasStory: 'true', pageSize: 100 },
    options,
  );
  const stories = await Promise.all(
    producers.map(async (producer) => {
      try {
        const story = await contentJson<Story>(
          `/api/v1/producers/${producer.id}/story`,
          signal,
          options,
        );
        return { ...story, producer };
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    }),
  );
  return stories.filter((story): story is StoryArticle => story !== null);
}
// カードや見出しの下に出す紹介文。こだわり → 仕事を選んだ理由 → 方法の順で、入力のあるもの
export function storyLead(story: Story): string | null {
  return story.craft ?? story.reason ?? story.method;
}

export async function getStory(
  id: number,
  signal?: AbortSignal,
  options?: ApiFetchOptions,
) {
  const story = (await getStories(signal, options)).find(
    (item) => item.id === id,
  );
  if (!story) throw new ApiError(404, 'ストーリーが見つかりません。');
  return story;
}
