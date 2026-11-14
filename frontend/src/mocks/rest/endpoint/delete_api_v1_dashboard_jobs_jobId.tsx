import type { RestMock } from '../../types';
import { deleteJob } from '../store/dashboardJobs';

// 【生産者】求人削除API DELETE /api/v1/dashboard/jobs/{jobId}
//
// 論理削除に成功すると 204（本文なし）。If-Match に詳細取得の ETag が必要
// データは store/dashboardJobs.tsx（削除した求人は一覧から消える）
//
// 新着・選考中・採用の応募が残っている（status: 409）:
//   { errorCode: 'ACTIVE_APPLICATIONS_EXIST', errorMsg: '対応中の応募があるため削除できません。' }
// 他者の求人・削除済み（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '求人が見つかりません。' }
// 他の人が先に更新していた（status: 412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '他の操作で更新されています。再読み込みしてください。' }
const dashboardJobDelete: RestMock = {
  method: 'DELETE',
  path: '/api/v1/dashboard/jobs/:jobId',
  status: 204,
  handler: (url, init) => deleteJob(url, init),
};

export { dashboardJobDelete };
