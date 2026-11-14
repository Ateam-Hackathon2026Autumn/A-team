import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 【生産者】求人一覧取得API GET /api/v1/dashboard/jobs
//
// ログイン中の生産者（山本農園）の求人一覧。下書き・非公開も含む
// publishStatus: draft=下書き / public=公開 / private=非公開 / suspended=運営による掲載停止
// applicationCount は全状態の応募数、hiredCount は採用（hired / completed）人数
//
// 求人なしの場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
// 生産者ではない・停止中の場合（status: 403）:
//   { errorCode: 'FORBIDDEN', errorMsg: 'この操作を行う権限がありません。' }
const dashboardJobsList: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/jobs',
  status: 200,
  body: {
    items: [
      {
        id: 2,
        title: '冬の剪定作業補助',
        publishStatus: 'public',
        slots: 2,
        applicationCount: 1,
        hiredCount: 0,
        createdAt: hoursFromNow(-24 * 5),
        updatedAt: hoursFromNow(-24 * 2),
      },
      {
        id: 1,
        title: 'りんごの収穫・選果スタッフ',
        publishStatus: 'public',
        slots: 5,
        applicationCount: 2,
        hiredCount: 0,
        createdAt: hoursFromNow(-24 * 14),
        updatedAt: hoursFromNow(-24 * 1),
      },
    ],
    total: 2,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { dashboardJobsList };
