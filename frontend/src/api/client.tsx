import { USE_MOCK, VITE_API_URL } from "../config/env";
import ApiError from './apiError';

// CSRF取得自身はこの通信処理を使い、apiFetchへの再帰を避ける。
async function rawFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const url = `${VITE_API_URL}${path}`;
  const options: RequestInit = { ...init, credentials: "include" };
  if (USE_MOCK) {
    const { mockFetch } = await import("../mocks/mockFetch");
    return mockFetch(url, options);
  }
  return fetch(url, options);
}

let csrfToken: string | null = null;
let csrfPending: Promise<string> | null = null;
let csrfVersion = 0;

function clearCsrfToken(): void {
  csrfVersion++;
  csrfToken = null;
  csrfPending = null;
}

function getCsrfToken(): Promise<string> {
  if (csrfToken !== null) return Promise.resolve(csrfToken);
  if (csrfPending !== null) return csrfPending;
  const version = csrfVersion;
  const request = (async () => {
    const response = await rawFetch('/api/v1/auth/csrf');
    if (!response.ok) throw new ApiError(response.status, 'CSRFトークンの取得に失敗しました');
    let body: unknown;
    try { body = await response.json(); } catch { throw new ApiError(response.status, 'CSRFトークンを確認できませんでした。'); }
    if (!body || typeof body !== 'object' || !('csrfToken' in body)
        || typeof body.csrfToken !== 'string' || !body.csrfToken.trim()) {
      throw new ApiError(response.status, 'CSRFトークンを確認できませんでした。');
    }
    // 認証などで無効化された古い取得結果はキャッシュへ戻さない。
    if (version !== csrfVersion) return getCsrfToken();
    csrfToken = body.csrfToken;
    return csrfToken;
  })().finally(() => { if (csrfPending === request) csrfPending = null; });
  csrfPending = request;
  return request;
}

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  init.signal?.throwIfAborted();
  const method = (init.method ?? 'GET').toUpperCase();
  if (['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) return rawFetch(path, init);
  const send = (token: string) => {
    init.signal?.throwIfAborted();
    const headers = new Headers(init.headers);
    headers.set('X-CSRFToken', token);
    return rawFetch(path, { ...init, method, headers });
  };
  const token = await getCsrfToken();
  const response = await send(token);
  if (response.status !== 403) return response;
  // 本文は各APIのエラー処理へ残す。CSRF拒否以外の403は再送しない。
  let csrfFailed = false;
  try { csrfFailed = (await response.clone().json()).errorCode === 'CSRF_FAILED'; } catch { /* JSONでない403 */ }
  if (!csrfFailed) return response;
  init.signal?.throwIfAborted();
  // 別の同時リクエストがすでに更新したトークンを再度無効化しない。
  if (csrfToken === token) clearCsrfToken();
  // ストリーム本文はすでに消費され得るため再送しない（既存APIはJSON／FormData）。
  if (init.body && typeof init.body === 'object' && 'getReader' in init.body) return response;
  const renewed = await getCsrfToken();
  return send(renewed); // ここで返し、二度目のCSRF拒否は再送しない。
}
export { apiFetch, getCsrfToken, clearCsrfToken };
