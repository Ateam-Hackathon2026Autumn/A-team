import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 体験予約枠更新API PATCH /api/v1/dashboard/experiences/:experienceId/slots/:slotId
//
// 送信した項目だけを更新し、更新後の予約枠を返す（ここでは枠1の定員を 20 → 24 に変更した例）
// If-Match には予約枠一覧の etag を渡す。返却された etag が次回の If-Match になる
//
// 予約がある枠の開始日時・所要時間を変えようとした場合（status: 409）:
//   {
//     errorCode: 'HAS_RESERVATION_HISTORY',
//     errorMsg: '予約がある枠の日時は変更できません。',
//   }
//
// 定員を予約人数より少なくしようとした場合（status: 409）:
//   { errorCode: 'CAPACITY_CONFLICT', errorMsg: '定員は予約人数以上にしてください。' }
//
// 他の画面で先に更新されていた場合（status: 412）:
//   {
//     errorCode: 'PRECONDITION_FAILED',
//     errorMsg: '他の操作で更新されています。再読み込みしてください。',
//   }
const dashboardExperienceSlotUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/experiences/:experienceId/slots/:slotId',
  status: 200,
  body: {
    id: 1,
    experienceId: 1,
    startAt: `${daysFromNow(10)}T10:00:00+09:00`,
    durationMin: 180,
    capacity: 24,
    status: 'open',
    reservedCount: 16,
    remainingCapacity: 8,
    etag: '"slot-1-v9"',
    createdAt: hoursFromNow(-24 * 30),
    updatedAt: hoursFromNow(0),
  },
};

export { dashboardExperienceSlotUpdate };
