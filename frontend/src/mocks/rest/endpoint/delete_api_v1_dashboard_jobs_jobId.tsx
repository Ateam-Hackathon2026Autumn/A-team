import type { RestMock } from '../../types';
import { deleteJob } from '../store/dashboardJobs';

// 【生産者】求人削除API DELETE /api/v1/dashboard/jobs/{jobId}
//
// 削除に成功すると 204（本文なし）。応募されたことがある求人は削除できない（非公開にしてもらう）
// データは store/dashboardJobs.tsx（削除した求人は一覧から消える）
//
// 応募されたことがある（status: 409）:
//   { errorCode: 'JOB_HAS_APPLICATIONS', errorMsg: '応募履歴がある求人は削除できません。非公開にしてください。' }
// 他者の求人・削除済み（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '求人が見つかりません。' }
const dashboardJobDelete: RestMock = {
  method: 'DELETE',
  path: '/api/v1/dashboard/jobs/:jobId',
  status: 204,
  handler: (url) => deleteJob(url),
};

export { dashboardJobDelete };
