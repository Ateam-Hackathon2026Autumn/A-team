import type {
  DashboardJob,
  DashboardJobApplication,
  DashboardJobApplicationList,
  DashboardJobList,
  JobApplicationStatus,
  JobApplicationUpdateResult,
  JobDecisionStatus,
  JobInput,
  JobPublishStatus,
} from '../types/dashboardJob';
import { toApiError } from './apiError';
import { apiFetch } from './client';

const BASE_PATH = '/api/v1/dashboard/jobs';
// 応募者一覧の1ページあたりの最大件数（API の上限）
const MAX_PAGE_SIZE = 100;

// 変更系API共通（CSRF トークンを付けて送る）
async function sendRequest(
  path: string,
  method: 'POST' | 'PATCH' | 'DELETE',
  body?: unknown,
): Promise<Response> {
  const headers: Record<string, string> = {};

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  return apiFetch(path, {
    method,
    headers,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

// 求人

// 本人の求人一覧（作成の新しい順）。publishStatus を省略すると全件
async function getDashboardJobs(
  page: number,
  publishStatus?: JobPublishStatus,
): Promise<DashboardJobList> {
  const params = new URLSearchParams({ page: String(page) });

  if (publishStatus !== undefined) {
    params.set('publishStatus', publishStatus);
  }

  const response = await apiFetch(`${BASE_PATH}?${params.toString()}`);

  if (response.ok) {
    return (await response.json()) as DashboardJobList;
  }

  throw await toApiError(response, '求人の一覧を取得できませんでした');
}

// 本人の求人を1件取得（編集画面用。勤務日を含む）
async function getDashboardJob(jobId: number): Promise<DashboardJob> {
  const response = await apiFetch(`${BASE_PATH}/${jobId}`);

  if (response.ok) {
    return (await response.json()) as DashboardJob;
  }

  throw await toApiError(response, '求人を取得できませんでした');
}

// 求人を登録（勤務日もまとめて登録する）。登録後の詳細が返る
async function createJob(input: JobInput): Promise<DashboardJob> {
  const response = await sendRequest(BASE_PATH, 'POST', input);

  if (response.ok) {
    return (await response.json()) as DashboardJob;
  }

  throw await toApiError(response, '求人を登録できませんでした');
}

// 求人を更新（送った項目だけ更新）。更新後の詳細が返る
// workDates を送ると、id 付きは更新・id なしは追加・送らなかった勤務日は削除になる
// （応募者が希望している勤務日の削除・日付変更は 409）
async function updateJob(
  jobId: number,
  input: Partial<JobInput>,
): Promise<DashboardJob> {
  const response = await sendRequest(`${BASE_PATH}/${jobId}`, 'PATCH', input);

  if (response.ok) {
    return (await response.json()) as DashboardJob;
  }

  throw await toApiError(response, '求人を保存できませんでした');
}

// 求人を削除（応募されたことがある求人は 409。その場合は非公開にしてもらう）
async function deleteJob(jobId: number): Promise<void> {
  const response = await sendRequest(`${BASE_PATH}/${jobId}`, 'DELETE');

  if (!response.ok) {
    throw await toApiError(response, '求人を削除できませんでした');
  }
}
// 応募者

// 求人の応募者一覧（応募の新しい順）。状態で絞り込める
async function getJobApplications(
  jobId: number,
  options: { page: number; pageSize?: number; status?: JobApplicationStatus },
): Promise<DashboardJobApplicationList> {
  const params = new URLSearchParams({ page: String(options.page) });

  if (options.pageSize !== undefined) {
    params.set('pageSize', String(options.pageSize));
  }

  if (options.status !== undefined) {
    params.set('status', options.status);
  }

  const response = await apiFetch(
    `${BASE_PATH}/${jobId}/applications?${params.toString()}`,
  );

  if (response.ok) {
    return (await response.json()) as DashboardJobApplicationList;
  }

  throw await toApiError(response, '応募者を取得できませんでした');
}

// 求人のすべての応募を取得する（編集画面で、希望者がいる勤務日と応募件数を知るために使う）
async function getAllJobApplications(
  jobId: number,
): Promise<DashboardJobApplication[]> {
  const items: DashboardJobApplication[] = [];

  for (let page = 1; ; page += 1) {
    const data = await getJobApplications(jobId, {
      page,
      pageSize: MAX_PAGE_SIZE,
    });
    items.push(...data.items);

    if (page >= data.totalPages) {
      return items;
    }
  }
}

// 応募を選考中・採用・不採用・勤務完了にする
// レスポンスは更新結果（状態・決定日時・採用人数）だけで、応募者データ全体ではない
async function updateJobApplication(
  jobId: number,
  applicationId: number,
  status: JobDecisionStatus,
): Promise<JobApplicationUpdateResult> {
  const response = await sendRequest(
    `${BASE_PATH}/${jobId}/applications/${applicationId}`,
    'PATCH',
    {
      status,
    },
  );

  if (response.ok) {
    return (await response.json()) as JobApplicationUpdateResult;
  }

  throw await toApiError(response, '応募の状態を変更できませんでした');
}

export {
  createJob,
  deleteJob,
  getAllJobApplications,
  getDashboardJob,
  getDashboardJobs,
  getJobApplications,
  updateJob,
  updateJobApplication,
};
