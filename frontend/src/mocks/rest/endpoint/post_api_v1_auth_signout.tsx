import type { RestMock } from '../../types';

// ログアウトAPI POST /api/v1/auth/signout
//
// 未ログイン・期限切れでも 200 を返す
//
// CSRF 検証失敗（403）:
//   { errorCode: 'CSRF_FAILED', errorMsg: 'リクエストを確認できませんでした。再度お試しください。' }
const authSignout: RestMock = {
  method: 'POST',
  path: '/api/v1/auth/signout',
  status: 200,
  body: {
    message: 'ログアウトしました。',
  },
};

export { authSignout };
