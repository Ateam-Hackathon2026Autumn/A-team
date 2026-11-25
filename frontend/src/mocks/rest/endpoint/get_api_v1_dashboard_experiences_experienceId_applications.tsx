import type { RestMock } from '../../types';
import { listApplications } from '../store/dashboardExperiences';

// 体験申込者一覧取得API GET /api/v1/dashboard/experiences/:experienceId/applications?slotId=&status=&page=
//
// 指定した体験の予約を created_at の新しい順で返す。slotId・status（applied / confirmed / canceled / attended）で絞り込める
// status: 'applied' が新着（未確認）の申込
//
// 退会済み会員の予約は user の氏名と representativeName / phone / message が null になる:
//   user: { id: 9, lastName: null, firstName: null, isActive: false }
//
// 自分の体験ではない・存在しない・削除済みの場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '対象の体験が見つかりません。' }
const dashboardExperienceApplicationsList: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/experiences/:experienceId/applications',
  status: 200,
  handler: (url) => listApplications(url),
};

export { dashboardExperienceApplicationsList };
