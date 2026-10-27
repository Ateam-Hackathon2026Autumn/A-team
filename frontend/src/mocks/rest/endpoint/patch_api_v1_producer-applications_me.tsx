import { hoursFromNow } from '../../helpers';
import type { RestMock } from '../../types';

// 生産者申請修正・再申請API（差し戻し時） PATCH /api/v1/producer-applications/me
//
// 差し戻された申請 1 を修正して再申請し、新しい申請 2（pending）が作られた想定
// 再申請の時点では isProducer は false のまま
//
// 最新申請 ID の不一致（409）:
//   { errorCode: 'APPLICATION_CONFLICT', errorMsg: '申請情報が更新されました。再取得してください。' }
//
// 差し戻し以外の状態（409）:
//   { errorCode: 'APPLICATION_NOT_RETURNED', errorMsg: '差し戻し中の申請のみ再申請できます。' }
//
// 本人の申請が存在しない（404）:
//   { errorCode: 'APPLICATION_NOT_FOUND', errorMsg: '生産者登録申請はありません。' }
const producerApplicationResubmit: RestMock = {
  method: 'PATCH',
  path: '/api/v1/producer-applications/me',
  status: 200,
  body: {
    message: '修正内容を保存し、再申請を受け付けました。',
    producerId: 1,
    applicationId: 2,
    approvalStatus: 'pending',
    applicationStatus: 'pending',
    publishStatus: 'draft',
    isProducer: false,
    submittedAt: hoursFromNow(0),
  },
};

export { producerApplicationResubmit };
