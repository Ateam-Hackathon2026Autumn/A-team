import type { RestMock } from '../../types';

// ログインチェックAPI GET /api/v1/auth/session
//
// VITE_MOCK_LOGGED_OUT=true で未ログインに切り替える。
//
// 生産者の状態（user の isProducer / producerApplicationStatus / producerAccountStatus）:
//   一般ユーザー（未申請）: false / 'not_applied' / null
//   申請中（審査中）      : false / 'pending'     / null
//   却下                  : false / 'rejected'    / null
//   承認済みの生産者      : true  / 'approved'    / 'active'
//   利用停止中の生産者    : false / 'approved'    / 'suspended'

const authSession: RestMock = {
  method: 'GET',
  path: '/api/v1/auth/session',
  status: 200,
  body: import.meta.env.VITE_MOCK_LOGGED_OUT === 'true' ? {
    authenticated: false,
    user: null,
  } : {
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

export { authSession };
