import { apiFetch } from './client';
import { toApiError } from './apiError';
import { fetchWithCsrf } from './authApi';
import type { PageResult } from '../types/experience';

export async function contentJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await apiFetch(path, { signal });
  if (!response.ok) throw await toApiError(response, '情報を取得できませんでした。');
  return response.json() as Promise<T>;
}

// 絞り込み条件をサーバーに渡し、その条件に一致する全ページを取得する。
export async function contentItems<T>(path: string, signal?: AbortSignal, query: Record<string, string | number> = {}): Promise<T[]> {
  const params = new URLSearchParams({ page: '1', pageSize: '20' });
  for (const [key, value] of Object.entries(query)) params.set(key, String(value));
  const first = await contentJson<PageResult<T>>(`${path}?${params}`, signal);
  const items = [...first.items];
  for (let page = 2; page <= first.totalPages; page++) {
    params.set('page', String(page));
    items.push(...(await contentJson<PageResult<T>>(`${path}?${params}`, signal)).items);
  }
  return items;
}

export async function submitContent<T>(path: string, input: unknown): Promise<T> {
  const response = await fetchWithCsrf(path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  });
  if (!response.ok) throw await toApiError(response, '送信できませんでした。内容を確認して再度お試しください。');
  return response.json() as Promise<T>;
}
