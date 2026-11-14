import type { RestMock } from '../../types';
import { updateJob } from '../store/dashboardJobs';

// 【生産者】求人更新API PATCH /api/v1/dashboard/jobs/{jobId}
//
// 送った項目だけを更新し、ID と公開状態を返す（If-Match に詳細取得の ETag。新しい ETag はヘッダー）
// workDates を送ると全勤務日を置き換える（既存の日は id 付き、新しい日は id なし）
// ※ 応募が1件でもある求人は publishStatus と slots 以外を変更できない（同じ値を送っても 409）
// データは store/dashboardJobs.tsx
//
// 応募があるのに募集条件を変えようとした（status: 409）:
//   { errorCode: 'CONFLICT', errorMsg: '応募がある求人は公開状態と募集人数以外を変更できません。' }
// 採用済み人数より募集人数を減らそうとした（status: 409）:
//   { errorCode: 'CAPACITY_CONFLICT', errorMsg: '採用済みの人数より少なくはできません。' }
// 他の人が先に更新していた（status: 412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '他の操作で更新されています。再読み込みしてください。' }
// 掲載停止中の求人（status: 403）:
//   { errorCode: 'FORBIDDEN', errorMsg: '掲載停止中の求人は変更できません。' }
const dashboardJobUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/jobs/:jobId',
  status: 200,
  handler: (url, init) => updateJob(url, init),
};

export { dashboardJobUpdate };
