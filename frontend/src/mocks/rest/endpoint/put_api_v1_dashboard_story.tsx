import type { RestMock } from '../../types';
import { putStory } from '../store/dashboardStory';

// ストーリー保存API PUT /api/v1/dashboard/story

// 実API: backend/api/views/dashboard/story.py・serializers/dashboard/story.py
// 本文は7項目すべて必須で、全体を置き換える（ETag・If-Match は使わない。初回も 200）:
//   {craft, method, process, environment, reason, goal, publishStatus}
//   本文6項目は null か2,000文字までの文字列（前後の空白を除き、空なら null）
//   publishStatus は 'draft' | 'public' | 'private'
// 保存後のストーリーを GET と同じ形で返す。処理は store/dashboardStory.tsx

// 入力エラー（400）:
//   { errorCode: 'VALIDATION_ERROR', errorMsg: '入力内容に誤りがあります。',
//     details: { craft: ['この項目が2000文字より長くならないようにしてください。'] } }
//   公開に本文が足りない: details: { publishStatus: ['公開するには本文を1項目以上入力してください。'] }
// 生産者が掲載停止中（409）:
//   { errorCode: 'PRODUCER_SUSPENDED', errorMsg: '掲載停止中のため、この操作はできません。運営にお問い合わせください。' }
// 運営がストーリーを掲載停止中（409）:
//   { errorCode: 'STORY_SUSPENDED', errorMsg: 'このストーリーは運営により掲載停止中です。運営にお問い合わせください。' }
const dashboardStoryUpsert: RestMock = {
  method: 'PUT',
  path: '/api/v1/dashboard/story',
  status: 200,
  handler: (_url, init) => putStory(init),
};

export { dashboardStoryUpsert };
