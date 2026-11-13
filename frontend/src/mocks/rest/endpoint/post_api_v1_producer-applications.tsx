import { hoursFromNow } from '../../helpers';
import type { RestMock } from '../../types';

// 生産者登録API POST /api/v1/producer-applications
//
// 初回申請専用。未申請のユーザーが申請した想定（新しい生産者 7 / 申請 7 を作成）
// 申請受付の時点では isProducer は false のまま
//
// 既に審査中（409）:
//   { errorCode: 'APPLICATION_ALREADY_PENDING', errorMsg: '生産者登録申請は審査中です。' }
//
// 既に生産者として登録済み（409。ログイン中の山本さんはこちらになる）:
//   { errorCode: 'PRODUCER_ALREADY_APPROVED', errorMsg: '生産者として登録済みです。' }
//
// 入力不正（400）:
//   {
//     errorCode: 'VALIDATION_ERROR',
//     errorMsg: '入力内容に誤りがあります。',
//     details: { businessName: ['事業者名を入力してください。'] },
//   }
const producerApplicationCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/producer-applications',
  status: 201,
  body: {
    message: '生産者登録申請を受け付けました。',
    producerId: 7,
    applicationId: 7,
    approvalStatus: 'pending',
    applicationStatus: 'pending',
    publishStatus: 'draft',
    isProducer: false,
    submittedAt: hoursFromNow(0),
  },
};

export { producerApplicationCreate };
