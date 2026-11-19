import type { RestMock } from '../../types';
import { getStory } from '../store/dashboardStory';

// ストーリー取得API GET /api/v1/dashboard/story
//
// ログイン中の生産者（山本農園）のストーリー（1生産者1件。ER図の producer_stories の形）
// 実API: backend/api/views/dashboard/story.py
//   {craft, method, process, environment, reason, goal, publishStatus, updatedAt}
//   本文はプレーンテキスト、未入力は null。掲載停止中（publishStatus: 'suspended'）でも取得できる
//   まだ保存していなくても 404 にならず、すべて null・draft・updatedAt null を返す
//
// 内容は store/dashboardStory.tsx が持つ（保存APIの結果がここに反映される）
// 未ログイン（401）: { errorCode: 'NOT_AUTHENTICATED', errorMsg: 'ログインしてください。' }
// 承認済みの生産者でない（403）: { errorCode: 'FORBIDDEN', errorMsg: 'この操作を行う権限がありません。' }
const dashboardStory: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/story',
  status: 200,
  handler: () => getStory(),
};

export { dashboardStory };
