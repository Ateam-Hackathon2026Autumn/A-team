import type { RestMock } from '../../types';
import { getJob } from '../store/dashboardJobs';

// 【生産者】求人詳細取得API GET /api/v1/dashboard/jobs/{jobId}
//
// 求人の編集用データを返す。ETag はレスポンスヘッダー（更新・削除時の If-Match に使う）
// workDates は過去日も含む全勤務日（日付の早い順）。hiredCount は採用済み人数、remainingCount は残り枠
// データは store/dashboardJobs.tsx
//
// 他者の求人・存在しない場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '求人が見つかりません。' }
const dashboardJobDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/jobs/:jobId',
  status: 200,
  handler: (url) => getJob(url),
};

export { dashboardJobDetail };
