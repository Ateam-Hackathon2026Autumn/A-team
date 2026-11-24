import { getMockExperience } from './get_api_v1_experiences_experienceId';
import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 体験申込API POST /api/v1/experiences/{experienceId}/applications
//
// 体験1・枠1 に 大人2名・子供1名で申し込んだ結果を返す
// totalAmount = 大人料金 3,500 × 2 + 子供料金 2,000 × 1（未就学児は無料）
// status は confirmed（予約確定）
//
// エラーにしたい場合は status と body を下記に書き換える
//
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
  if (!item) return { status: 404, body: { errorMsg: '体験が見つかりません。' } };
  let input: Record<string, unknown>;
  try { input = JSON.parse(String(init?.body)); } catch { return { status: 400, body: { errorMsg: '申込内容を確認してください。' } }; }
  if (!input || typeof input !== 'object' || Array.isArray(input)) return { status: 400, body: { errorCode: 'VALIDATION_ERROR', errorMsg: '申込内容を確認してください。' } };
  const slot = item.slots.items.find(slot => slot.id === input.slotId);
  const allowed = ['slotId', 'adultCount', 'childCount', 'infantCount', 'lastName', 'firstName', 'phone', 'message', 'agreedToCancelPolicy', 'eligibilityConfirmed', 'expectedTotalAmount'];
  if (Object.keys(input).some(key => !allowed.includes(key))) return { status: 400, body: { errorCode: 'VALIDATION_ERROR', errorMsg: '申込内容を確認してください。' } };
  const adult = input.adultCount, child = input.childCount, infant = input.infantCount;
  if (!slot) return { status: 404, body: { errorCode: 'NOT_FOUND', errorMsg: '開催枠が見つかりません。' } };
  if (![adult, child, infant].every(Number.isSafeInteger) || (adult as number) < 1 || (child as number) < 0 || (infant as number) < 0 || (adult as number) + (child as number) + (infant as number) > 99 || (item.priceChild === null && (child as number) > 0) || (!item.familyOk && ((child as number) > 0 || (infant as number) > 0)) || !String(input.lastName ?? '').trim() || !String(input.firstName ?? '').trim() || !String(input.phone ?? '').trim() || input.agreedToCancelPolicy !== true || input.eligibilityConfirmed !== true) return { status: 400, body: { errorCode: 'VALIDATION_ERROR', errorMsg: '人数・代表者情報・同意内容を確認してください。' } };
  const total = (adult as number) * item.priceAdult + (child as number) * (item.priceChild ?? 0);
  if (input.expectedTotalAmount !== total) return { status: 409, body: { errorCode: 'QUOTE_CHANGED', errorMsg: '料金が変わりました。内容を確認して再度お申し込みください。' } };
  if (!slot.bookable || (adult as number) + (child as number) + (infant as number) > slot.remainingCapacity) return { status: 409, body: { errorCode: 'CAPACITY_EXCEEDED', errorMsg: '定員に達したため申し込めません。' } };
  return { status: 201, body: { id: 103, reservationNo: 'DEMO-RSV-000103', experienceId, slotId: slot.id, adultCount: adult, childCount: child, infantCount: infant, representativeName: `${String(input.lastName).trim()} ${String(input.firstName).trim()}`, phone: input.phone, message: input.message || null, totalAmount: total, status: 'confirmed', policyAgreedAt: hoursFromNow(0), createdAt: hoursFromNow(0) } };
};
