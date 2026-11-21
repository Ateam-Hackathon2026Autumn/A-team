import type { UserInfo } from '../types/user';
import ApiError, { toApiError } from './apiError';
import type { SignupFormValues } from '../types/authForm';
import { apiFetch } from './client';

// チーム合意：バックエンドの初期版番号と同じ固定値を送信する。
const TERMS_VERSION = '2026-10-01';
const PRIVACY_POLICY_VERSION = '2026-10-01';

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

// 更新系APIの X-CSRFToken ヘッダーに使うトークンを取得
async function getCsrfToken(): Promise<string> {
  const response = await apiFetch('/api/v1/auth/csrf');

  if (response.ok) {
    const { csrfToken } = (await response.json()) as { csrfToken: string };
    if (typeof csrfToken !== 'string' || !csrfToken) {
      throw new ApiError(response.status, 'CSRFトークンを確認できませんでした。');
    }
    return csrfToken;
  }

  throw new ApiError(response.status, 'CSRFトークンの取得に失敗しました');
}

type AuthResponse = { message: string; authenticated: true; user: UserInfo };
type AuthResult = AuthResponse & { csrfRefreshFailed: boolean };

async function authenticate(path: string, body: unknown, expectedStatus: number): Promise<AuthResult> {
  const csrfToken = await getCsrfToken();
  const response = await apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw await toApiError(response, '認証処理に失敗しました。');
  const result = (await response.json()) as AuthResponse;
  if (response.status !== expectedStatus || result.authenticated !== true || !result.user) {
    throw new ApiError(response.status, '認証結果を確認できませんでした。ログイン状態を確認してください。');
  }
  // POST 成功後の再取得失敗を認証失敗にしない。登録を再送すると重複する。
  let csrfRefreshFailed = false;
  try {
    await getCsrfToken();
  } catch {
    csrfRefreshFailed = true;
  }
  return { ...result, csrfRefreshFailed };
}

function signin(email: string, password: string): Promise<AuthResult> {
  return authenticate('/api/v1/auth/signin', { email: email.trim(), password }, 200);
}

function signup(values: SignupFormValues): Promise<AuthResult> {
  return authenticate('/api/v1/users', {
    ...values,
    lastName: values.lastName.trim(), firstName: values.firstName.trim(),
    email: values.email.trim(), phone: values.phone.trim(),
    prefectureId: values.prefectureId === '' ? null : Number(values.prefectureId),
    termsVersion: TERMS_VERSION, privacyPolicyVersion: PRIVACY_POLICY_VERSION,
  }, 201);
}

export { checkSession, getCsrfToken, signin, signup };
export type { SessionResponse };
