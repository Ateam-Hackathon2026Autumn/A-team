import type { PublicExperienceSlot } from '../types/experience';

export function validateExperienceApply(input: {
  adult: string; child: string; infant: string; lastName: string; firstName: string;
  phone: string; agreed: boolean; eligibilityConfirmed: boolean;
  childAllowed: boolean; infantAllowed: boolean; selected?: PublicExperienceSlot;
}): Record<string, string> {
  const errors: Record<string, string> = {};
  const adult = Number(input.adult), child = Number(input.child), infant = Number(input.infant);
  if (!input.selected) errors.slot = '開催日を選択してください。';
  if (!input.adult.trim() || !Number.isSafeInteger(adult) || adult < 1) errors.adult = '大人は1名以上の整数で入力してください。';
  if (!input.child.trim() || !Number.isSafeInteger(child) || child < 0 || (!input.childAllowed && child > 0)) errors.child = '子どもの人数を確認してください。';
  if (!input.infant.trim() || !Number.isSafeInteger(infant) || infant < 0 || (!input.infantAllowed && infant > 0)) errors.infant = '乳幼児の人数を確認してください。';
  if (!errors.adult && !errors.child && !errors.infant && adult + child + infant > 99) errors.capacity = '参加人数は合計99名までです。';
  if (!errors.adult && !errors.child && !errors.infant && input.selected && adult + child + infant > input.selected.remainingCapacity) {
    errors.capacity = `残り枠（${input.selected.remainingCapacity}名）を超えています。人数を減らしてください。`;
  }
  if (!input.lastName.trim() || input.lastName.trim().length > 50) errors.lastName = '代表者の姓を50文字以内で入力してください。';
  if (!input.firstName.trim() || input.firstName.trim().length > 50) errors.firstName = '代表者の名を50文字以内で入力してください。';
  if (input.lastName.trim().length + input.firstName.trim().length + 1 > 100) errors.firstName = '姓と名を合わせて99文字以内で入力してください。';
  const normalizedPhone = input.phone.replace(/-/g, '');
  if (!/^[0-9-]+$/.test(input.phone) || !/^0[0-9]{9,10}$/.test(normalizedPhone)) errors.phone = '電話番号は0から始まる半角数字10〜11桁で入力してください（ハイフン可）。';
  if (!input.agreed) errors.agreed = 'キャンセルポリシーと注意事項への同意が必要です。';
  if (!input.eligibilityConfirmed) errors.eligibilityConfirmed = '参加条件の確認が必要です。';
  return errors;
}
