import type { RestMock } from '../../types';

// 本人情報取得API GET /api/v1/users/me
//
// 未ログイン（401）:
//   { errorCode: 'NOT_AUTHENTICATED', errorMsg: 'ログインしてください。' }
const usersMe: RestMock = {
  method: 'GET',
  path: '/api/v1/users/me',
  status: 200,
  body: {
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
    profile: {
      phone: '09012345678',
      birthDate: '1988-04-12',
      // 長野県
      prefectureId: 20,
      // vegetables / fruits / seafood / experiences / short_term_jobs / farming
      interests: ['fruits', 'experiences', 'farming'],
    },
  },
};

export { usersMe };
