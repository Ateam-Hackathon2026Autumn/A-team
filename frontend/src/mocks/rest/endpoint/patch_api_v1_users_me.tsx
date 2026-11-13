import type { RestMock } from '../../types';

// 本人情報更新API PATCH /api/v1/users/me
//
// 更新後の本人情報を返す（ここでは interests を更新した想定）
//
// 入力不正（400）:
//   {
//     errorCode: 'VALIDATION_ERROR',
//     errorMsg: '入力内容に誤りがあります。',
//     details: { lastName: ['姓を入力してください。'] },
//   }
//
// 未ログイン（401）:
//   { errorCode: 'NOT_AUTHENTICATED', errorMsg: 'ログインしてください。' }
const usersMeUpdate: RestMock = {
  method: 'PATCH',
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
      interests: ['fruits', 'vegetables', 'experiences', 'farming'],
    },
  },
};

export { usersMeUpdate };
