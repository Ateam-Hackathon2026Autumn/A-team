import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 体験予約枠一覧取得API GET /api/v1/dashboard/experiences/:experienceId/slots
//
// どの experienceId でも体験1の予約枠を開始日時の早い順で返す（過去枠・満席も含む）
// remainingCapacity = max(capacity - reservedCount, 0)
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
  body: {
    items: [
      {
        id: 1,
        experienceId: 1,
        startAt: `${daysFromNow(10)}T10:00:00+09:00`,
        durationMin: 180,
        capacity: 20,
        status: 'open',
        reservedCount: 16,
        remainingCapacity: 4,
        etag: '"slot-1-v8"',
        createdAt: hoursFromNow(-24 * 30),
        updatedAt: hoursFromNow(-3),
      },
      {
        id: 2,
        experienceId: 1,
        startAt: `${daysFromNow(17)}T10:00:00+09:00`,
        durationMin: 180,
        capacity: 20,
        status: 'open',
        reservedCount: 3,
        remainingCapacity: 17,
        etag: '"slot-2-v2"',
        createdAt: hoursFromNow(-24 * 14),
        updatedAt: hoursFromNow(-24 * 2),
      },
    ],
    total: 2,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { dashboardExperienceSlotsList };
