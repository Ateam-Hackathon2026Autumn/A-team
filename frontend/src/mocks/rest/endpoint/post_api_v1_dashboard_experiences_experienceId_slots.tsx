import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 体験予約枠登録API POST /api/v1/dashboard/experiences/:experienceId/slots
//
// 作成した予約枠を返す（予約数0、etag は以後の更新・削除の If-Match に使う）
//
// 同じ開始日時の枠がすでにある場合（status: 409）:
//   { errorCode: 'DUPLICATE_SLOT', errorMsg: '同じ開始日時の予約枠がすでにあります。' }
//
// 開始日時が過去・入力内容に誤りがある場合（status: 400）:
//   {
//     errorCode: 'VALIDATION_ERROR',
//     errorMsg: '入力内容に誤りがあります。',
//     details: { startAt: ['現在より後の日時を指定してください。'] },
//   }
const dashboardExperienceSlotCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/dashboard/experiences/:experienceId/slots',
  status: 201,
  body: {
    id: 10,
    experienceId: 1,
    startAt: `${daysFromNow(24)}T10:00:00+09:00`,
    durationMin: 180,
    capacity: 20,
    status: 'open',
    reservedCount: 0,
    remainingCapacity: 20,
    etag: '"slot-10-v1"',
    createdAt: hoursFromNow(0),
    updatedAt: hoursFromNow(0),
  },
};

export { dashboardExperienceSlotCreate };
