import type { JobApplication } from '../types/job';
import { hoursFromNow } from './helpers';
import { getMockJob } from './rest/endpoint/get_api_v1_jobs_jobId';

// 初期応募と追加応募を、一覧と重複チェックの両方から参照する。
// 初期応募の日付・IDは求人詳細と同じ開催日から取得する。
export const initialJobApplications: JobApplication[] = [
  { id: 4, jobId: 3, status: 'applied', hoursAgo: -5 },
  { id: 5, jobId: 4, status: 'screening', hoursAgo: -24 * 10 },
].flatMap(seed => {
  const job = getMockJob(seed.jobId);
  // 求人一覧を空にした表示テストでもモックの初期化を失敗させない。
  if (!job) return [];
  return [{
    id: seed.id, job: { id: job.id, title: job.title, isPublic: true },
    workDates: seed.status === 'applied' ? job.workDates.items.slice(0, 1).map(day => ({ id: day.id, workDate: day.workDate })) : [],
    status: seed.status, createdAt: hoursFromNow(seed.hoursAgo),
  }];
});
export const demoJobApplications: JobApplication[] = [];
export const getAllJobApplications = () => [...demoJobApplications, ...initialJobApplications];
