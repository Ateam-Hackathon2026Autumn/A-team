import type { RestMock } from '../../types';

// 確認メール再送API POST /api/v1/auth/email-verification/resend
//
// 既に認証済みでも同じ 202 を返す（その場合は配送しない）
//
// 回数制限（429。最低60秒間隔・1時間5回まで）:
//   { errorCode: 'RATE_LIMITED', errorMsg: '時間をおいて再度お試しください。' }
//
// 未ログイン（401）:
//   { errorCode: 'NOT_AUTHENTICATED', errorMsg: 'ログインしてください。' }
const emailVerificationResend: RestMock = {
  method: 'POST',
  path: '/api/v1/auth/email-verification/resend',
  status: 202,
  body: {
    message: '必要な場合、確認メールの配送を受け付けました。',
  },
};

export { emailVerificationResend };
