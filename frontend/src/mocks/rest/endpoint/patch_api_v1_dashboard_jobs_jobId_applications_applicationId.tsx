import type { RestMock } from '../../types';
import { updateApplication } from '../store/dashboardJobs';

// 【生産者】応募者の採用・不採用更新API PATCH /api/v1/dashboard/jobs/{jobId}/applications/{applicationId}
//
// リクエストの status は screening（選考中）/ hired（採用）/ rejected（不採用）/ completed（勤務完了）のどれか
// 変更できるのは applied → screening / hired / rejected、screening → hired / rejected、長期の求人の hired → completed
// 募集人数を超えても採用できる。レスポンスは更新結果だけ（応募者データ全体ではない）:
//   { id, status, decidedAt, hiredCount, slots, isOverCapacity }
// データは store/dashboardJobs.tsx
//
// 今の状態から変えられない（status: 409）:
//   { errorCode: 'INVALID_APPLICATION_STATUS_TRANSITION', errorMsg: '現在の応募状態から指定された状態には変更できません。' }
// 応募が見つからない（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '応募者が見つかりません。' }
const dashboardJobApplicationUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/jobs/:jobId/applications/:applicationId',
  status: 200,
  handler: (url, init) => updateApplication(url, init),
};

export { dashboardJobApplicationUpdate };
