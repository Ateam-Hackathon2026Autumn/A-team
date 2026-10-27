import type { RestMock } from '../../types';

// ログインチェックAPI GET /api/v1/auth/session
//
// 状態を切り替えたい場合は body を下記のコメントの値に書き換える
//
// 未ログイン:
//   { authenticated: false, user: null }
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
  body: {
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
