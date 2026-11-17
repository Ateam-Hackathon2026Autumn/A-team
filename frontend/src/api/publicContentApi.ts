import { apiFetch } from './client';
import { toApiError } from './apiError';
import { USE_MOCK } from '../config/env';
import type { PageResult } from '../types/experience';

export async function contentJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await apiFetch(path, { signal });
  if (!response.ok) throw await toApiError(response, '情報を取得できませんでした。');
  return response.json() as Promise<T>;
}

// 一覧APIの全ページを取得。絞り込みは取得済みデータに対して行う。
export async function contentItems<T>(path: string, signal?: AbortSignal): Promise<T[]> {
  const first = await contentJson<PageResult<T>>(`${path}?page=1&pageSize=20`, signal);
  const items = [...first.items];
  for (let page = 2; page <= first.totalPages; page++) {
    items.push(...(await contentJson<PageResult<T>>(`${path}?page=${page}&pageSize=20`, signal)).items);
  }
  return items;
}

export async function submitContent<T>(path: string, input: unknown): Promise<T> {
  if (!USE_MOCK) throw new Error('実際の送信は認証・CSRF連携の接続確認後に利用できます。');
  const response = await apiFetch(path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  });
  if (!response.ok) throw await toApiError(response, '送信できませんでした。内容を確認して再度お試しください。');
  return response.json() as Promise<T>;
}
