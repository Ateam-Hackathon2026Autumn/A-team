import type { RestMock } from '../../types';

// メール認証完了API POST /api/v1/auth/email-verification/confirm
//
// ログイン不要。自動ログインはしない
//
// トークンが無効・期限切れ・使用済み（400）:
//   {
//     errorCode: 'INVALID_OR_EXPIRED_TOKEN',
//     errorMsg: '認証リンクが無効、または有効期限が切れています。確認メールを再送してください。',
//   }
const emailVerificationConfirm: RestMock = {
  method: 'POST',
  path: '/api/v1/auth/email-verification/confirm',
  status: 200,
  body: {
    message: 'メール認証が完了しました。',
    emailVerified: true,
  },
};

export { emailVerificationConfirm };
