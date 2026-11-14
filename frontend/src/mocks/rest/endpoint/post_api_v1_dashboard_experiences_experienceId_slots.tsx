import type { RestMock } from '../../types';
import { createSlot } from '../store/dashboardExperiences';

// 体験予約枠登録API POST /api/v1/dashboard/experiences/:experienceId/slots
//
// 送った日時・定員で作成した予約枠を返す（予約数0、etag は以後の更新・削除の If-Match に使う）
// 同じ Idempotency-Key で同じ内容を再送した場合は、前回作成した枠を返す
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
  handler: (url, init) => createSlot(url, init),
};

export { dashboardExperienceSlotCreate };
