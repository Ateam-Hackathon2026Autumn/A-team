import type { RestMock } from '../../types';

// CSRFトークン取得API GET /api/v1/auth/csrf
//
// 未ログインでも呼び出せる。登録・ログイン成功後はフロントで再取得する
//
// 回数制限（429）:
//   { errorCode: 'RATE_LIMITED', errorMsg: '時間をおいて再度お試しください。' }
const authCsrf: RestMock = {
  method: 'GET',
  path: '/api/v1/auth/csrf',
  status: 200,
  body: {
    csrfToken: 'mock-csrf-token',
  },
};

export { authCsrf };
