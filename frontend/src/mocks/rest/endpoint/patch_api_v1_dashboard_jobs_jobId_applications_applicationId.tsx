import type { RestMock } from '../../types';
import { updateApplication } from '../store/dashboardJobs';

// 【生産者】応募者の採用・不採用更新API PATCH /api/v1/dashboard/jobs/{jobId}/applications/{applicationId}
//
// リクエストの status は screening（選考中）/ hired（採用）/ rejected（不採用）のどれか
// If-Match に応募者一覧の items[].etag が必要。更新後の応募（新しい etag 付き）を返す
// 変更できるのは applied → screening / hired / rejected、screening → hired / rejected だけ
// データは store/dashboardJobs.tsx（採用すると求人の採用人数・勤務日の残り枠に反映される）
//
// 採用枠が埋まっている（status: 409）:
//   { errorCode: 'CAPACITY_CONFLICT', errorMsg: '募集人数に達しているため採用できません。' }
// 採用・不採用が決まった後に変更しようとした（status: 409）:
//   { errorCode: 'INVALID_TRANSITION', errorMsg: 'この応募の状態は変更できません。' }
// 他の人が先に更新していた（status: 412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '応募が更新されています。再読み込みしてください。' }
const dashboardJobApplicationUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/jobs/:jobId/applications/:applicationId',
  status: 200,
  handler: (url, init) => updateApplication(url, init),
};

export { dashboardJobApplicationUpdate };
