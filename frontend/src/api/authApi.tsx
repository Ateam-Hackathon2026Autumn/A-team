import type { UserInfo } from '../types/user';
import ApiError from './apiError';
import { apiFetch } from './client';

// ログインチェックAPIのレスポンス（未ログインでも 200 で authenticated: false）
type SessionResponse =
  | { authenticated: true; user: UserInfo }
  | { authenticated: false; user: null };

// 現在のログイン状況とログインユーザーの情報を確認
async function checkSession(): Promise<SessionResponse> {
  const response = await apiFetch('/api/v1/auth/session');

  if (response.ok) {
    return (await response.json()) as SessionResponse;
  }

  throw new ApiError(response.status, 'ログイン状態の確認に失敗しました');
}

export { checkSession };
export type { SessionResponse };
