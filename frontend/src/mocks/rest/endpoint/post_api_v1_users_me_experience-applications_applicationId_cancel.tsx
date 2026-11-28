import { daysFromNow, hoursFromNow } from '../../helpers';
import type { RestMock } from '../../types';
import { cancelMockExperienceApplication } from './get_api_v1_users_me_experience-applications';

// 体験予約キャンセルAPI POST /api/v1/users/me/experience-applications/:applicationId/cancel

// リクエスト本文なし。確定済み・締め切り前の予約をキャンセルし、申込状況の1件と同じ形で返す。
// 締め切り後・確定済み以外（409 CANCEL_NOT_ALLOWED）:
//   { errorCode: 'CANCEL_NOT_ALLOWED', errorMsg: 'キャンセルの受付期間が過ぎたか、キャンセルできない予約です。主催者にメッセージでご連絡ください。' }
const myExperienceApplicationCancel: RestMock = {
  method: 'POST',
  path: '/api/v1/users/me/experience-applications/:applicationId/cancel',
  status: 200,
  body: {
    id: 102,
    reservationNo: 'RSV-000102',
    experience: {
      id: 4,
      title: '牧場で乳しぼり＆手づくりバター',
      isPublic: true,
    },
    slot: {
      id: 41,
      startAt: `${daysFromNow(24)}T13:00:00+09:00`,
      durationMin: 120,
      status: 'open',
    },
    adultCount: 2,
    childCount: 1,
    infantCount: 0,
    totalAmount: 7400,
    status: 'canceled',
    cancellable: false,
    cancelDeadlineAt: `${daysFromNow(23)}T13:00:00+09:00`,
    createdAt: hoursFromNow(-24 * 3),
  },
  handler: (url) => cancelMockExperienceApplication(url),
};

export { myExperienceApplicationCancel };
