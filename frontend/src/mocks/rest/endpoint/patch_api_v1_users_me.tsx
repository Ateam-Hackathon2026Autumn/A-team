import { usersMe } from './get_api_v1_users_me';
import type {
  ConsumerAccount,
  ConsumerProfileInput,
} from '../../../types/consumerAccount';
import type { RestMock } from '../../types';

// 本人情報更新API PATCH /api/v1/users/me

// 更新後の本人情報を返す（ここでは interests を更新した想定）

// 入力不正（400）:
//   {
//     errorCode: 'VALIDATION_ERROR',
//     errorMsg: '入力内容に誤りがあります。',
//     details: { lastName: ['姓を入力してください。'] },
//   }

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

usersMeUpdate.handler = (_url, init) => {
  let input: ConsumerProfileInput;
  try {
    input = JSON.parse(String(init?.body)) as ConsumerProfileInput;
  } catch {
    return { status: 400, body: { errorMsg: '入力内容を確認してください。' } };
  }
  if (
    !input ||
    typeof input.lastName !== 'string' ||
    typeof input.firstName !== 'string' ||
    typeof input.phone !== 'string' ||
    !input.lastName?.trim() ||
    !input.firstName?.trim() ||
    !input.phone ||
    !/^0[0-9]{9,10}$/.test(input.phone) ||
    !input.birthDate ||
    !Array.isArray(input.interests)
  )
    return {
      status: 400,
      body: { errorMsg: 'プロフィールの入力内容を確認してください。' },
    };
  if (
    [...input.lastName.trim()].length > 10 ||
    [...input.firstName.trim()].length > 10
  )
    return {
      status: 400,
      body: { errorMsg: '姓と名はそれぞれ10文字以内で入力してください。' },
    };
  const current = usersMe.body as ConsumerAccount;
  const { lastName, firstName, ...profile } = input;
  const account: ConsumerAccount = {
    user: { ...current.user, lastName, firstName },
    profile,
  };
  usersMe.body = account;
  return { status: 200, body: account };
};
