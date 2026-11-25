import type { RestMock } from '../../types';
import { updateSlot } from '../store/dashboardExperiences';

// 体験予約枠更新API PATCH /api/v1/dashboard/experiences/:experienceId/slots/:slotId
//
// 送信した項目だけを更新し、更新後の予約枠を返す
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
  handler: (url, init) => updateSlot(url, init),
};

export { dashboardExperienceSlotUpdate };
