import type { DashboardStory, StoryInput } from '../types/dashboardStory';
import { toApiError } from './apiError';
import { apiFetch } from './client';

// 生産者ストーリー（学ぶページ）の取得・保存
// 実API: backend/api/views/dashboard/story.py（ETag・If-Match は使わない）

// 本人のストーリーを取得（下書き・非公開・掲載停止中も取得できる。未保存なら空の内容）
async function getDashboardStory(
  signal?: AbortSignal,
): Promise<DashboardStory> {
  const response = await apiFetch('/api/v1/dashboard/story', { signal });

  if (response.ok) {
    return (await response.json()) as DashboardStory;
  }

  throw await toApiError(response, 'ストーリーを取得できませんでした。');
}

// ストーリーを保存（7項目すべて送って置き換える。初回も 200）
// 400: 項目ごとの入力エラー（公開に本文が足りないときは details.publishStatus）
// 409: PRODUCER_SUSPENDED（生産者が掲載停止中）／STORY_SUSPENDED（ストーリーが掲載停止中）
async function updateDashboardStory(
  input: StoryInput,
): Promise<DashboardStory> {
  const response = await apiFetch('/api/v1/dashboard/story', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });

  if (response.ok) {
    return (await response.json()) as DashboardStory;
  }

  throw await toApiError(response, 'ストーリーを保存できませんでした。');
}

export { getDashboardStory, updateDashboardStory };
