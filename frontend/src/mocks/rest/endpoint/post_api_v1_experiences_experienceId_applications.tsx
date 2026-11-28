import { getMockExperience } from './get_api_v1_experiences_experienceId';
import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 体験申込API POST /api/v1/experiences/{experienceId}/applications

// 体験1・枠1 に 大人2名・子供1名で申し込んだ結果を返す
// totalAmount = 大人料金 3,500 × 2 + 子供料金 2,000 × 1（未就学児は無料）
// status は confirmed（予約確定。支払い済みという意味ではない）

// エラーにしたい場合は status と body を下記に書き換える

// 未ログイン（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
// 定員不足・受付終了（status: 409）:
//   { errorCode: 'CONFLICT', errorMsg: '定員に達したため申し込めません。' }
// 料金・枠が変わっていた（status: 409）:
//   { errorCode: 'QUOTE_CHANGED', errorMsg: '料金または開催枠が変更されました。内容を確認して再度お申し込みください。' }
// 同じ枠に申込済み（status: 409）:
//   { errorCode: 'ALREADY_APPLIED', errorMsg: 'この開催枠には申込済みです。' }
const experienceApply: RestMock = {
  method: 'POST',
  path: '/api/v1/experiences/:experienceId/applications',
  status: 201,
  body: {
    id: 103,
    reservationNo: 'RSV-000103',
    experienceId: 1,
    slotId: 1,
    adultCount: 2,
    childCount: 1,
    infantCount: 0,
    representativeName: '山本 健太',
    phone: '090-1234-5678',
    message: '子どもと一緒に参加します。よろしくお願いします。',
    totalAmount: 9000,
    status: 'confirmed',
    policyAgreedAt: hoursFromNow(0),
    createdAt: hoursFromNow(0),
  },
};

export { experienceApply };

// 入力値を反映するデモ応答。実際の予約・決済・永続保存はしない。
experienceApply.handler = (url, init) => {
  const experienceId = Number(url.pathname.split('/').at(-2));
  const item = getMockExperience(experienceId);
  if (!item)
    return {
      status: 404,
      body: {
        errorCode: 'EXPERIENCE_NOT_FOUND',
        errorMsg: '体験が見つかりません。',
      },
    };
  let input: Record<string, unknown>;
  try {
    input = JSON.parse(String(init?.body));
  } catch {
    return { status: 400, body: { errorMsg: '申込内容を確認してください。' } };
  }
  if (!input || typeof input !== 'object' || Array.isArray(input))
    return {
      status: 400,
      body: {
        errorCode: 'VALIDATION_ERROR',
        errorMsg: '申込内容を確認してください。',
      },
    };
  const fields = [
    'slotId',
    'adultCount',
    'childCount',
    'infantCount',
    'lastName',
    'firstName',
    'phone',
    'message',
    'agreedToCancelPolicy',
    'eligibilityConfirmed',
    'expectedTotalAmount',
  ];
  const details: Record<string, string[]> = {};
  for (const key of Object.keys(input))
    if (!fields.includes(key))
      details[key] = ['この項目は受け付けていません。'];
  for (const key of ['adultCount', 'childCount', 'infantCount']) {
    const value = input[key];
    if (
      typeof value !== 'number' ||
      !Number.isSafeInteger(value) ||
      value < (key === 'adultCount' ? 1 : 0) ||
      value > 99
    )
      details[key] = ['人数を確認してください。'];
  }
  const adult = Number(input.adultCount),
    child = Number(input.childCount),
    infant = Number(input.infantCount);
  if (adult + child + infant > 99)
    details.adultCount = ['人数は合わせて99人までです。'];
  for (const key of ['lastName', 'firstName']) {
    if (
      typeof input[key] !== 'string' ||
      !input[key].trim() ||
      Array.from(input[key].trim()).length > 50
    )
      details[key] = ['1〜50文字で入力してください。'];
  }
  if (
    typeof input.lastName === 'string' &&
    typeof input.firstName === 'string' &&
    Array.from(input.lastName.trim()).length +
      Array.from(input.firstName.trim()).length >
      99
  )
    details.firstName = ['姓と名は合わせて99文字以内で入力してください。'];
  if (
    typeof input.phone !== 'string' ||
    input.phone.trim().length > 20 ||
    !/^[0-9-]+$/.test(input.phone.trim()) ||
    !/^0[0-9]{9,10}$/.test(input.phone.trim().replace(/-/g, ''))
  )
    details.phone = ['電話番号を確認してください。'];
  if (
    input.message != null &&
    (typeof input.message !== 'string' ||
      Array.from(input.message.trim()).length > 2000)
  )
    details.message = ['2000文字以内で入力してください。'];
  if (input.agreedToCancelPolicy !== true)
    details.agreedToCancelPolicy = ['キャンセルポリシーへの同意が必要です。'];
  if (input.eligibilityConfirmed !== true)
    details.eligibilityConfirmed = ['参加条件の確認が必要です。'];
  if (
    typeof input.slotId !== 'number' ||
    !Number.isSafeInteger(input.slotId) ||
    input.slotId < 1
  )
    details.slotId = ['開催日を選択してください。'];
  if (
    typeof input.expectedTotalAmount !== 'number' ||
    !Number.isSafeInteger(input.expectedTotalAmount) ||
    input.expectedTotalAmount < 0 ||
    input.expectedTotalAmount > 2147483647
  )
    details.expectedTotalAmount = ['合計金額を確認してください。'];
  if (Object.keys(details).length)
    return {
      status: 400,
      body: {
        errorCode: 'VALIDATION_ERROR',
        errorMsg: '申込内容を確認してください。',
        details,
      },
    };
  const slot = item.slots.items.find((slot) => slot.id === input.slotId);
  if (!slot)
    return {
      status: 404,
      body: { errorCode: 'SLOT_NOT_FOUND', errorMsg: '日程が見つかりません。' },
    };
  if (
    new Date(slot.bookingDeadlineAt).getTime() <= Date.now() ||
    new Date(slot.startAt).getTime() <= Date.now()
  )
    return {
      status: 409,
      body: {
        errorCode: 'BOOKING_CLOSED',
        errorMsg: 'この日程の申込は締め切りました。',
      },
    };
  if (
    (child > 0 && item.priceChild === null) ||
    (!item.familyOk && child + infant > 0)
  )
    return {
      status: 400,
      body: {
        errorCode: 'VALIDATION_ERROR',
        errorMsg: '参加条件を確認してください。',
        details: {
          childCount: [
            'この体験では指定された子ども・未就学児の人数を受け付けていません。',
          ],
        },
      },
    };
  const totalAmount = adult * item.priceAdult + child * (item.priceChild ?? 0);
  if (input.expectedTotalAmount !== totalAmount)
    return {
      status: 409,
      body: {
        errorCode: 'QUOTE_CHANGED',
        errorMsg:
          '料金が変わりました。内容を確認してから、もう一度お申し込みください。',
      },
    };
  if (adult + child + infant > slot.remainingCapacity)
    return {
      status: 409,
      body: {
        errorCode: 'CAPACITY_EXCEEDED',
        errorMsg: `空きが足りません（残り${slot.remainingCapacity}名）。`,
      },
    };
  return {
    status: 201,
    body: {
      id: 103,
      reservationNo: 'DEMO-RSV-000103',
      experienceId,
      slotId: slot.id,
      adultCount: adult,
      childCount: child,
      infantCount: infant,
      representativeName: `${String(input.lastName).trim()} ${String(input.firstName).trim()}`,
      phone: String(input.phone).trim().replace(/-/g, ''),
      message:
        typeof input.message === 'string' ? input.message.trim() || null : null,
      totalAmount,
      status: 'confirmed',
      policyAgreedAt: hoursFromNow(0),
      createdAt: hoursFromNow(0),
    },
  };
};
