import type { RestMock } from '../../types';
import { getExperience } from '../store/dashboardExperiences';

// 体験詳細取得API GET /api/v1/dashboard/experiences/:experienceId
//
// 編集画面用に全項目と画像（S3 キーと表示用 URL）を返す。予約枠は予約枠一覧取得APIで取得する
// ETag はレスポンスヘッダーで返す（更新・削除の If-Match に使う。予約枠を変えると変わる）
//
// 自分の体験ではない・存在しない・削除済みの場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '対象の体験が見つかりません。' }
const dashboardExperienceDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/experiences/:experienceId',
  status: 200,
  handler: (url) => getExperience(url),
};

export { dashboardExperienceDetail };
