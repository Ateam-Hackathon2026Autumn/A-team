import type {
  DashboardJob,
  DashboardJobApplication,
  DashboardJobApplicationList,
  DashboardJobList,
  JobApplicationStatus,
  JobDecisionStatus,
  JobInput,
  JobPublishStatus,
  JobWriteResult,
} from '../types/dashboardJob';
import { toApiError } from './apiError';
import { getCsrfToken } from './authApi';
import { apiFetch } from './client';

const BASE_PATH = '/api/v1/dashboard/jobs';

// 求人の ETag はレスポンスヘッダー（ETag）で返る。本文には含まれない
// ※ ヘッダーがない場合は null になる（その場合 If-Match は送らない）
type WithEtag<T> = { data: T; etag: string | null };

function readEtag(response: Response): string | null {
  return response.headers.get('ETag');
}

// 二重送信を防ぐ Idempotency-Key（登録APIで必須）
function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

// 変更系API共通（CSRF トークン、競合検知の If-Match、二重送信防止キーを付けて送る）
async function sendRequest(
  path: string,
  method: 'POST' | 'PATCH' | 'DELETE',
  options: { body?: unknown; etag?: string | null; idempotencyKey?: string } = {},
): Promise<Response> {
  const csrfToken = await getCsrfToken();
  const headers: Record<string, string> = { 'X-CSRFToken': csrfToken };

  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  if (options.etag !== undefined && options.etag !== null) {
    headers['If-Match'] = options.etag;
  }

  if (options.idempotencyKey !== undefined) {
    headers['Idempotency-Key'] = options.idempotencyKey;
  }

  return apiFetch(path, {
    method,
    headers,
    ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
  });
}

// ---------------------------------------------------------------------------
// 求人
// ---------------------------------------------------------------------------

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

// 本人の求人を1件取得（編集画面用。全勤務日と採用人数を含む）
async function getDashboardJob(jobId: number): Promise<WithEtag<DashboardJob>> {
  const response = await apiFetch(`${BASE_PATH}/${jobId}`);

  if (response.ok) {
    return { data: (await response.json()) as DashboardJob, etag: readEtag(response) };
  }

  throw await toApiError(response, '求人を取得できませんでした');
}

// 求人を登録（勤務日もまとめて登録する）
async function createJob(
  input: JobInput,
  idempotencyKey: string,
): Promise<WithEtag<JobWriteResult>> {
  const response = await sendRequest(BASE_PATH, 'POST', { body: input, idempotencyKey });

  if (response.ok) {
    return { data: (await response.json()) as JobWriteResult, etag: readEtag(response) };
  }

  throw await toApiError(response, '求人を登録できませんでした');
}

// 求人を更新（送った項目だけ更新。workDates は送った内容で置き換わる）
// 応募がある求人は publishStatus と slots だけ送る
async function updateJob(
  jobId: number,
  input: Partial<JobInput>,
  etag: string | null,
): Promise<WithEtag<JobWriteResult>> {
  const response = await sendRequest(`${BASE_PATH}/${jobId}`, 'PATCH', { body: input, etag });

  if (response.ok) {
    return { data: (await response.json()) as JobWriteResult, etag: readEtag(response) };
  }

  throw await toApiError(response, '求人を保存できませんでした');
}

// 求人を削除（新着・選考中・採用の応募が残っている求人は削除できない）
async function deleteJob(jobId: number, etag: string | null): Promise<void> {
  const response = await sendRequest(`${BASE_PATH}/${jobId}`, 'DELETE', { etag });

  if (!response.ok) {
    throw await toApiError(response, '求人を削除できませんでした');
  }
}

// ---------------------------------------------------------------------------
// 応募者
// ---------------------------------------------------------------------------

// 求人の応募者一覧（応募の新しい順）。状態で絞り込める
async function getJobApplications(
  jobId: number,
  options: { page: number; status?: JobApplicationStatus },
): Promise<DashboardJobApplicationList> {
  const params = new URLSearchParams({ page: String(options.page) });

  if (options.status !== undefined) {
    params.set('status', options.status);
  }

  const response = await apiFetch(`${BASE_PATH}/${jobId}/applications?${params.toString()}`);

  if (response.ok) {
    return (await response.json()) as DashboardJobApplicationList;
  }

  throw await toApiError(response, '応募者を取得できませんでした');
}

// 応募を選考中・採用・不採用にする（If-Match には応募の etag を渡す）
async function updateJobApplication(
  application: DashboardJobApplication,
  status: JobDecisionStatus,
): Promise<DashboardJobApplication> {
  const response = await sendRequest(
    `${BASE_PATH}/${application.jobId}/applications/${application.id}`,
    'PATCH',
    { body: { status }, etag: application.etag },
  );

  if (response.ok) {
    return (await response.json()) as DashboardJobApplication;
  }

  throw await toApiError(response, '応募の状態を変更できませんでした');
}

export {
  createJob,
  deleteJob,
  getDashboardJob,
  getDashboardJobs,
  getJobApplications,
  newIdempotencyKey,
  updateJob,
  updateJobApplication,
};
