import { USE_MOCK, VITE_API_URL } from '../config/env';
import { mockFetch } from '../mocks/mockFetch';

// API 呼び出しの共通処理（セッション Cookie を送るため credentials: 'include'）
// モック有効時はバックエンドへ接続せず、src/mocks の内容を返却
async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const url = `${VITE_API_URL}${path}`;
  const options: RequestInit = { ...init, credentials: 'include' };

  return USE_MOCK ? mockFetch(url, options) : fetch(url, options);
}

export { apiFetch };
