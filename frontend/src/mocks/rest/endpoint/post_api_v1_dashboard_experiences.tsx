import type { RestMock } from '../../types';
import { createExperience } from '../store/dashboardExperiences';

// 体験登録API POST /api/v1/dashboard/experiences
//
// 作成された体験の ID と公開状態だけを返す（ETag はヘッダー。予約枠は予約枠登録APIで別途作成する）
// 同じ Idempotency-Key で同じ内容を再送した場合は、前回作成した体験を返す（二重登録しない）
//
// 入力内容に誤りがある場合（status: 400）:
//   {
//     errorCode: 'VALIDATION_ERROR',
//     errorMsg: '入力内容に誤りがあります。',
//     details: { title: ['タイトルを入力してください。'] },
//   }
//
// 公開条件を満たしていない・同じ Idempotency-Key で異なる内容を送った場合（status: 409）:
//   { errorCode: 'CONFLICT', errorMsg: '公開に必要な項目が不足しています。' }
const dashboardExperienceCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/dashboard/experiences',
  status: 201,
  handler: (_url, init) => createExperience(init),
};

export { dashboardExperienceCreate };
