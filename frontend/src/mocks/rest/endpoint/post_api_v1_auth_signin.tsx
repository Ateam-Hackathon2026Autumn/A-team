import type { RestMock } from '../../types';

// ログインAPI POST /api/v1/auth/signin
//
// 成功後はフロントで CSRF トークンを再取得する
//
// 認証失敗（401。未登録・停止・削除も同じ文言）:
//   { errorCode: 'INVALID_CREDENTIALS', errorMsg: 'メールアドレスまたはパスワードが正しくありません。' }
//
// 既にログイン済み（409）:
//   { errorCode: 'ALREADY_AUTHENTICATED', errorMsg: '既にログインしています。' }
const authSignin: RestMock = {
  method: 'POST',
  path: '/api/v1/auth/signin',
  status: 200,
  body: {
    message: 'ログインしました。',
    authenticated: true,
    user: {
      id: 1,
      email: 'yamamoto@example.com',
      lastName: '山本',
      firstName: '健太',
      isProducer: true,
      producerApplicationStatus: 'approved',
      producerAccountStatus: 'active',
      emailVerified: true,
    },
  },
};

export { authSignin };
