import type { RestMock } from '../../types';

// 体験予約枠削除API DELETE /api/v1/dashboard/experiences/:experienceId/slots/:slotId
//
// 成功時は本文なし（204）。If-Match には予約枠一覧の etag を渡す
//
// 申込中・確定済みの予約が残っている場合（status: 409）:
//   {
//     errorCode: 'ACTIVE_RESERVATIONS_EXIST',
//     errorMsg: '予約が残っているため削除できません。',
//   }
//
// 他の体験の枠・存在しない・削除済みの場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '対象の予約枠が見つかりません。' }
const dashboardExperienceSlotDelete: RestMock = {
  method: 'DELETE',
  path: '/api/v1/dashboard/experiences/:experienceId/slots/:slotId',
  status: 204,
};

export { dashboardExperienceSlotDelete };
