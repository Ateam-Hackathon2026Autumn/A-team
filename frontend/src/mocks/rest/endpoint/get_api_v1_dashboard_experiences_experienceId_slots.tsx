import type { RestMock } from '../../types';
import { listSlots } from '../store/dashboardExperiences';

// 体験予約枠一覧取得API GET /api/v1/dashboard/experiences/:experienceId/slots?page=&pageSize=
//
// 指定した体験の予約枠を開始日時の早い順で返す（過去枠・満席・中止も含む）
// reservedCount は申込中・確定・参加済みの人数、remainingCapacity = max(capacity - reservedCount, 0)
// etag は枠ごとの ETag。予約枠の更新・削除のとき If-Match にそのまま渡す（体験の ETag とは別）
//
// 予約枠が0件の場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
//
// 自分の体験ではない・存在しない・削除済みの場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '対象の体験が見つかりません。' }
const dashboardExperienceSlotsList: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/experiences/:experienceId/slots',
  status: 200,
  handler: (url) => listSlots(url),
};

export { dashboardExperienceSlotsList };
