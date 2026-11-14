import type { RestMock } from '../../types';
import { listJobs } from '../store/dashboardJobs';

// 【生産者】求人一覧取得API GET /api/v1/dashboard/jobs?publishStatus=&page=
//
// ログイン中の生産者（山本農園）の求人一覧を作成の新しい順で返す（20件ずつ）。下書き・非公開も含む
// publishStatus: draft=下書き / public=公開 / private=非公開 / suspended=運営による掲載停止
// applicationCount は全状態の応募数、hiredCount は採用（hired / completed）人数
// データは store/dashboardJobs.tsx。登録・更新・削除・採用の結果がそのまま反映される
//
// 求人なしの場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
// 生産者ではない・停止中の場合（status: 403）:
//   { errorCode: 'FORBIDDEN', errorMsg: 'この操作を行う権限がありません。' }
const dashboardJobsList: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/jobs',
  status: 200,
  handler: (url) => listJobs(url),
};

export { dashboardJobsList };
