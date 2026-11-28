import type { UserInfo } from '../types/user';
import ApiError, { toApiError } from './apiError';
import type { SignupFormValues } from '../types/authForm';
import { apiFetch, getCsrfToken, clearCsrfToken } from './client';

type Policies = { termsVersion: string; privacyPolicyVersion: string };

async function getPolicies(): Promise<Policies> {
  const response = await apiFetch('/api/v1/policies');
  if (!response.ok)
    throw await toApiError(response, '利用規約の情報を取得できませんでした。');
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiError(
      response.status,
      '利用規約の情報を確認できませんでした。',
    );
  }
  if (
    !body ||
    typeof body !== 'object' ||
    !('termsVersion' in body) ||
    typeof body.termsVersion !== 'string' ||
    !body.termsVersion.trim() ||
    !('privacyPolicyVersion' in body) ||
    typeof body.privacyPolicyVersion !== 'string' ||
    !body.privacyPolicyVersion.trim()
  ) {
    throw new ApiError(
      response.status,
      '利用規約の情報を確認できませんでした。',
    );
  }
  return {
    termsVersion: body.termsVersion,
    privacyPolicyVersion: body.privacyPolicyVersion,
  };
}

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

type AuthResponse = { message: string; authenticated: true; user: UserInfo };
type AuthResult = AuthResponse & { csrfRefreshFailed: boolean };

async function authenticate(
  path: string,
  body: unknown,
  expectedStatus: number,
): Promise<AuthResult> {
  const response = await apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok)
    throw await toApiError(response, '認証処理に失敗しました。');
  // Django はログイン・登録時に CSRF を更新するため、成功後は再取得する
  clearCsrfToken();
  const result = (await response.json()) as AuthResponse;
  if (
    response.status !== expectedStatus ||
    result.authenticated !== true ||
    !result.user
  ) {
    throw new ApiError(
      response.status,
      '認証結果を確認できませんでした。ログイン状態を確認してください。',
    );
  }
  // POST 成功後の CSRF 再取得失敗は認証失敗にしない（登録を再送すると重複する）
  let csrfRefreshFailed = false;
  try {
    await getCsrfToken();
  } catch {
    csrfRefreshFailed = true;
  }
  return { ...result, csrfRefreshFailed };
}

function signin(email: string, password: string): Promise<AuthResult> {
  return authenticate(
    '/api/v1/auth/signin',
    { email: email.trim(), password },
    200,
  );
}

function signup(
  values: SignupFormValues,
  policies: Policies,
): Promise<AuthResult> {
  return authenticate(
    '/api/v1/users',
    {
      ...values,
      lastName: values.lastName.trim(),
      firstName: values.firstName.trim(),
      email: values.email.trim(),
      phone: values.phone.trim(),
      prefectureId:
        values.prefectureId === '' ? null : Number(values.prefectureId),
      termsVersion: policies.termsVersion,
      privacyPolicyVersion: policies.privacyPolicyVersion,
    },
    201,
  );
}

async function confirmPasswordReset(
  uid: string,
  token: string,
  newPassword: string,
): Promise<void> {
  const response = await apiFetch('/api/v1/auth/password-reset/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ uid, token, newPassword }),
  });
  if (!response.ok)
    throw await toApiError(response, 'パスワードを再設定できませんでした。');
}

export {
  checkSession,
  getCsrfToken,
  getPolicies,
  signin,
  signup,
  confirmPasswordReset,
};
export type { SessionResponse, Policies };
