import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 体験申込API POST /api/v1/experiences/{experienceId}/applications
//
// 体験1・枠1 に 大人2名・子供1名で申し込んだ結果を返す
// totalAmount = 大人料金 3,500 × 2 + 子供料金 2,000 × 1（未就学児は無料）
// status は applied（申込済み。支払い済みという意味ではない）
//
// エラーにしたい場合は status と body を下記に書き換える
//
// 未ログイン（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
// 定員不足・受付終了（status: 409）:
//   { errorCode: 'CONFLICT', errorMsg: '定員に達したため申し込めません。' }
// 料金・枠が変わっていた（status: 409）:
//   { errorCode: 'QUOTE_CHANGED', errorMsg: '料金または開催枠が変更されました。内容を確認して再度お申し込みください。' }
// 同じ枠に申込済み（status: 409）:
//   { errorCode: 'ALREADY_APPLIED', errorMsg: 'この開催枠には申込済みです。' }
const experienceApply: RestMock = {
  method: 'POST',
  path: '/api/v1/experiences/:experienceId/applications',
  status: 201,
  body: {
    id: 103,
    reservationNo: 'RSV-000103',
    experienceId: 1,
    slotId: 1,
    adultCount: 2,
    childCount: 1,
    infantCount: 0,
    representativeName: '山本 健太',
    phone: '090-1234-5678',
    message: '子どもと一緒に参加します。よろしくお願いします。',
    totalAmount: 9000,
    status: 'applied',
    policyAgreedAt: hoursFromNow(0),
    createdAt: hoursFromNow(0),
  },
};

export { experienceApply };
