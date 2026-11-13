import type { RestMock } from '../../types';

// 共通ユーザー新規登録API POST /api/v1/users
//
// 登録成功で自動ログインする（メール未認証のため emailVerified は false）
//
// メールアドレス重複（409）:
//   { errorCode: 'EMAIL_ALREADY_EXISTS', errorMsg: 'このメールアドレスは既に登録されています。' }
//
// 既にログイン済み（409）:
//   { errorCode: 'ALREADY_AUTHENTICATED', errorMsg: '既にログインしています。' }
//
// 入力不正（400）:
//   {
//     errorCode: 'VALIDATION_ERROR',
//     errorMsg: '入力内容に誤りがあります。',
//     details: { lastName: ['姓を入力してください。'] },
//   }
const usersCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/users',
  status: 201,
  body: {
    message: '登録が完了しました。確認メールの配送を受け付けました。',
    authenticated: true,
    user: {
      id: 9,
      email: 'nakamura@example.com',
      lastName: '中村',
      firstName: '葵',
      isProducer: false,
      producerApplicationStatus: 'not_applied',
      producerAccountStatus: null,
      emailVerified: false,
    },
  },
};

export { usersCreate };
