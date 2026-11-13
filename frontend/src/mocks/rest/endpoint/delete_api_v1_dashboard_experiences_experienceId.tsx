import type { RestMock } from '../../types';

// 体験削除API DELETE /api/v1/dashboard/experiences/:experienceId
//
// 成功時は本文なし（204）。If-Match に詳細取得の ETag が必要
//
// 申込中・確定済みの予約が残っている場合（status: 409）:
//   {
//     errorCode: 'ACTIVE_RESERVATIONS_EXIST',
//     errorMsg: '予約が残っているため削除できません。',
//   }
//
// 自分の体験ではない・存在しない・削除済みの場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '対象の体験が見つかりません。' }
const dashboardExperienceDelete: RestMock = {
  method: 'DELETE',
  path: '/api/v1/dashboard/experiences/:experienceId',
  status: 204,
};

export { dashboardExperienceDelete };
