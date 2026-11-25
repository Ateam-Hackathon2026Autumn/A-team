import { apiFetch, type ApiFetchOptions } from './client';
import ApiError, { toApiError } from './apiError';
import type { PageResult } from '../types/experience';

export async function contentJson<T>(path: string, signal?: AbortSignal, options?: ApiFetchOptions): Promise<T> {
  const response = await apiFetch(path, { signal }, options);
  if (!response.ok) throw await toApiError(response, '情報を取得できませんでした。');
  return response.json() as Promise<T>;
}

// 絞り込み条件をサーバーに渡し、その条件に一致する全ページを取得する。
export async function contentItems<T>(path: string, signal?: AbortSignal, query: Record<string, string | number> = {}, options?: ApiFetchOptions): Promise<T[]> {
  const params = new URLSearchParams({ page: '1', pageSize: '20' });
  for (const [key, value] of Object.entries(query)) params.set(key, String(value));
  const first = await contentJson<PageResult<T>>(`${path}?${params}`, signal, options);
  const items = [...first.items];
  for (let page = 2; page <= first.totalPages; page++) {
    params.set('page', String(page));
    items.push(...(await contentJson<PageResult<T>>(`${path}?${params}`, signal, options)).items);
  }
  return items;
}

export async function submitContent<T>(path: string, input: unknown, expectedStatus = 201): Promise<T> {
  const response = await apiFetch(path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  });
  if (!response.ok) throw await toApiError(response, '送信できませんでした。内容を確認して再度お試しください。');
  if (response.status !== expectedStatus) throw new ApiError(response.status, '送信結果を確認できませんでした。再送する前にマイページで状況を確認してください。');
  try { return await response.json() as T; }
  catch { throw new ApiError(response.status, '送信結果を確認できませんでした。再送する前にマイページで状況を確認してください。'); }
}
