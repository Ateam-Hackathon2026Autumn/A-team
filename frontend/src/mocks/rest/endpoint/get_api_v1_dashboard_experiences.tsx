import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 体験一覧取得API GET /api/v1/dashboard/experiences
//
// ログイン中の生産者（山本農園）が登録した体験だけを created_at の新しい順で返す
// slotCount は未削除の全枠数、applicationCount は全状態（キャンセル含む）の予約件数
//
// 体験が0件の場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
//
// 未ログインの場合（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
//
// 生産者でない・利用停止中の場合（status: 403）:
//   { errorCode: 'FORBIDDEN', errorMsg: 'この操作を行う権限がありません。' }
const dashboardExperiencesList: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/experiences',
  status: 200,
  body: {
    items: [
      {
        id: 2,
        title: '冬の剪定見学とりんご農家の昼ごはん',
        publishStatus: 'public',
        prefectureId: 20,
        priceAdult: 2500,
        priceChild: null,
        slotCount: 1,
        applicationCount: 2,
        nextStartAt: `${daysFromNow(90)}T10:00:00+09:00`,
        createdAt: hoursFromNow(-24 * 7),
        updatedAt: hoursFromNow(-24 * 2),
      },
      {
        id: 1,
        title: '蜜入りりんごの収穫体験とアップルパイづくり',
        publishStatus: 'public',
        prefectureId: 20,
        priceAdult: 3500,
        priceChild: 2000,
        slotCount: 2,
        applicationCount: 7,
        nextStartAt: `${daysFromNow(10)}T10:00:00+09:00`,
        createdAt: hoursFromNow(-24 * 30),
        updatedAt: hoursFromNow(-3),
      },
    ],
    total: 2,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { dashboardExperiencesList };
