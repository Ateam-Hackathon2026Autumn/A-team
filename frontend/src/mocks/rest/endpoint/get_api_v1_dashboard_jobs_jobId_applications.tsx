import type { RestMock } from '../../types';
import { listApplications } from '../store/dashboardJobs';

// 【生産者】求人応募者一覧取得API GET /api/v1/dashboard/jobs/{jobId}/applications?status=&page=
//
// 求人の応募者を応募の新しい順で返す（20件ずつ）。status を指定するとその状態だけに絞り込む
// items[].etag は採用・不採用更新API の If-Match に渡す値（求人の ETag とは別）
// 退会した応募者は applicant が { id, lastName: null, firstName: null, email: null, phone: null, isActive: false } になる
// データは store/dashboardJobs.tsx（求人1に新着2件・辞退1件、求人2に選考中1件）
//
// 応募なしの場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
// 他者の求人・存在しない場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '求人が見つかりません。' }
const dashboardJobApplicationsList: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/jobs/:jobId/applications',
  status: 200,
  handler: (url) => listApplications(url),
};

export { dashboardJobApplicationsList };
