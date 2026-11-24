import type { PublicExperienceSlot } from '../types/experience';

export function isExperienceSlotBookable(slot: PublicExperienceSlot, now = Date.now()): boolean {
  return slot.bookable && slot.remainingCapacity > 0
    && new Date(slot.startAt).getTime() > now && new Date(slot.bookingDeadlineAt).getTime() > now;
}

export function validateExperienceApply(input: {
  adult: string; child: string; infant: string; lastName: string; firstName: string;
  phone: string; message: string; agreed: boolean; eligibilityConfirmed: boolean;
  familyOk: boolean; childAllowed: boolean; total: number; selected?: PublicExperienceSlot;
}): Record<string, string> {
  const errors: Record<string, string> = {};
  const adult = Number(input.adult), child = Number(input.child), infant = Number(input.infant);
  if (!input.selected || !isExperienceSlotBookable(input.selected)) errors.slot = '申込可能な開催日を選択してください。';
  if (!input.adult.trim() || !Number.isSafeInteger(adult) || adult < 1 || adult > 99) errors.adult = '大人は1〜99名の整数で入力してください。';
  if (!input.child.trim() || !Number.isSafeInteger(child) || child < 0 || child > 99
      || ((!input.familyOk || !input.childAllowed) && child > 0)) errors.child = '子どもの人数を確認してください。';
  if (!input.infant.trim() || !Number.isSafeInteger(infant) || infant < 0 || infant > 99
      || (!input.familyOk && infant > 0)) errors.infant = '未就学児の人数を確認してください。';
  if (!errors.adult && !errors.child && !errors.infant) {
    if (adult + child + infant > 99) errors.capacity = '人数は合わせて99名までです。';
    else if (input.selected && adult + child + infant > input.selected.remainingCapacity) {
      errors.capacity = `残り枠（${input.selected.remainingCapacity}名）を超えています。人数を減らしてください。`;
    }
  }
  for (const key of ['lastName', 'firstName'] as const) {
    const value = input[key].trim();
    if (!value || Array.from(value).length > 50) errors[key] = `${key === 'lastName' ? '姓' : '名'}は1〜50文字で入力してください。`;
  }
  if (Array.from(input.lastName.trim()).length + Array.from(input.firstName.trim()).length > 99) {
    errors.firstName = '姓と名は合わせて99文字以内で入力してください。';
  }
  const phone = input.phone.trim();
  if (!/^[0-9-]+$/.test(phone) || !/^0[0-9]{9,10}$/.test(phone.replace(/-/g, '')) || phone.length > 20) {
    errors.phone = '電話番号は0から始まる半角数字10〜11桁で入力してください（ハイフン可）。';
  }
  if (Array.from(input.message.trim()).length > 2000) errors.message = 'メッセージは2000文字以内で入力してください。';
  if (!input.agreed) errors.agreed = 'キャンセルポリシーと注意事項への同意が必要です。';
  if (!input.eligibilityConfirmed) errors.eligibilityConfirmed = '参加条件を確認してください。';
  if (!Number.isSafeInteger(input.total) || input.total < 0 || input.total > 2147483647) errors.total = '合計金額が申込可能な範囲を超えています。人数を確認してください。';
  return errors;
}
