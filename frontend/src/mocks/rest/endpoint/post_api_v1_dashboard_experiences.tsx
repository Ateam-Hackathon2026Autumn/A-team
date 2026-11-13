import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 体験登録API POST /api/v1/dashboard/experiences
//
// 作成された体験の ID と公開状態だけを返す（予約枠は予約枠登録APIで別途作成する）
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
  body: {
    id: 5,
    producerId: 1,
    publishStatus: 'draft',
    createdAt: hoursFromNow(0),
    updatedAt: hoursFromNow(0),
  },
};

export { dashboardExperienceCreate };
