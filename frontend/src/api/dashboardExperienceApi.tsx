import type {
  DashboardExperience,
  DashboardExperienceList,
  ExperienceApplicationList,
  ExperienceApplicationStatus,
  ExperienceInput,
  ExperiencePublishStatus,
  ExperienceSlot,
  ExperienceSlotInput,
  ExperienceSlotList,
  ExperienceSlotUpdateInput,
  ExperienceWriteResult,
} from '../types/dashboardExperience';
import { toApiError } from './apiError';
import { getCsrfToken } from './authApi';
import { apiFetch } from './client';

const BASE_PATH = '/api/v1/dashboard/experiences';

// 体験の ETag はレスポンスヘッダー（ETag）で返る。本文には含まれない
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
// 体験
// ---------------------------------------------------------------------------

// 本人の体験一覧（作成の新しい順）。publishStatus を省略すると全件
async function getDashboardExperiences(
  page: number,
  publishStatus?: ExperiencePublishStatus,
): Promise<DashboardExperienceList> {
  const params = new URLSearchParams({ page: String(page) });

  if (publishStatus !== undefined) {
    params.set('publishStatus', publishStatus);
  }

  const response = await apiFetch(`${BASE_PATH}?${params.toString()}`);

  if (response.ok) {
    return (await response.json()) as DashboardExperienceList;
  }

  throw await toApiError(response, '体験の一覧を取得できませんでした');
}

// 本人の体験を1件取得（編集画面用。予約枠は含まない）
async function getDashboardExperience(
  experienceId: number,
): Promise<WithEtag<DashboardExperience>> {
  const response = await apiFetch(`${BASE_PATH}/${experienceId}`);

  if (response.ok) {
    return {
      data: (await response.json()) as DashboardExperience,
      etag: readEtag(response),
    };
  }

  throw await toApiError(response, '体験を取得できませんでした');
}

// 体験を登録（予約枠は登録後に予約枠登録APIで追加する）
async function createExperience(
  input: ExperienceInput,
  idempotencyKey: string,
): Promise<WithEtag<ExperienceWriteResult>> {
  const response = await sendRequest(BASE_PATH, 'POST', {
    body: input,
    idempotencyKey,
  });

  if (response.ok) {
    return {
      data: (await response.json()) as ExperienceWriteResult,
      etag: readEtag(response),
    };
  }

  throw await toApiError(response, '体験を登録できませんでした');
}

// 体験を更新（送った項目だけ更新。images は送った内容で置き換わる）
async function updateExperience(
  experienceId: number,
  input: Partial<ExperienceInput>,
  etag: string | null,
): Promise<WithEtag<ExperienceWriteResult>> {
  const response = await sendRequest(`${BASE_PATH}/${experienceId}`, 'PATCH', {
    body: input,
    etag,
  });

  if (response.ok) {
    return {
      data: (await response.json()) as ExperienceWriteResult,
      etag: readEtag(response),
    };
  }

  throw await toApiError(response, '体験を保存できませんでした');
}

// 体験を削除（申込中・確定の予約が残っている体験は削除できない）
async function deleteExperience(
  experienceId: number,
  etag: string | null,
): Promise<void> {
  const response = await sendRequest(`${BASE_PATH}/${experienceId}`, 'DELETE', {
    etag,
  });

  if (!response.ok) {
    throw await toApiError(response, '体験を削除できませんでした');
  }
}

// ---------------------------------------------------------------------------
// 予約枠
// ---------------------------------------------------------------------------

// 体験の予約枠一覧（開始日時の早い順。過去・満席・中止の枠も含む）
async function getExperienceSlots(
  experienceId: number,
  page = 1,
): Promise<ExperienceSlotList> {
  const response = await apiFetch(
    `${BASE_PATH}/${experienceId}/slots?page=${page}&pageSize=100`,
  );

  if (response.ok) {
    return (await response.json()) as ExperienceSlotList;
  }

  throw await toApiError(response, '予約枠を取得できませんでした');
}

// 予約枠を追加
async function createExperienceSlot(
  experienceId: number,
  input: ExperienceSlotInput,
  idempotencyKey: string,
): Promise<ExperienceSlot> {
  const response = await sendRequest(`${BASE_PATH}/${experienceId}/slots`, 'POST', {
    body: input,
    idempotencyKey,
  });

  if (response.ok) {
    return (await response.json()) as ExperienceSlot;
  }

  throw await toApiError(response, '予約枠を追加できませんでした');
}

// 予約枠を更新（If-Match には予約枠の etag を渡す）
async function updateExperienceSlot(
  experienceId: number,
  slot: ExperienceSlot,
  input: ExperienceSlotUpdateInput,
): Promise<ExperienceSlot> {
  const response = await sendRequest(
    `${BASE_PATH}/${experienceId}/slots/${slot.id}`,
    'PATCH',
    { body: input, etag: slot.etag },
  );

  if (response.ok) {
    return (await response.json()) as ExperienceSlot;
  }

  throw await toApiError(response, '予約枠を変更できませんでした');
}

// 予約枠を削除（申込中・確定の予約がある枠は削除できない）
async function deleteExperienceSlot(
  experienceId: number,
  slot: ExperienceSlot,
): Promise<void> {
  const response = await sendRequest(
    `${BASE_PATH}/${experienceId}/slots/${slot.id}`,
    'DELETE',
    { etag: slot.etag },
  );

  if (!response.ok) {
    throw await toApiError(response, '予約枠を削除できませんでした');
  }
}

// ---------------------------------------------------------------------------
// 申込者
// ---------------------------------------------------------------------------

// 体験の予約一覧（申込の新しい順）。予約枠・状態で絞り込める
async function getExperienceApplications(
  experienceId: number,
  options: {
    page: number;
    slotId?: number;
    status?: ExperienceApplicationStatus;
  },
): Promise<ExperienceApplicationList> {
  const params = new URLSearchParams({ page: String(options.page) });

  if (options.slotId !== undefined) {
    params.set('slotId', String(options.slotId));
  }

  if (options.status !== undefined) {
    params.set('status', options.status);
  }

  const response = await apiFetch(
    `${BASE_PATH}/${experienceId}/applications?${params.toString()}`,
  );

  if (response.ok) {
    return (await response.json()) as ExperienceApplicationList;
  }

  throw await toApiError(response, '申込者を取得できませんでした');
}

export {
  createExperience,
  createExperienceSlot,
  deleteExperience,
  deleteExperienceSlot,
  getDashboardExperience,
  getDashboardExperiences,
  getExperienceApplications,
  getExperienceSlots,
  newIdempotencyKey,
  updateExperience,
  updateExperienceSlot,
};
