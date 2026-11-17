import type { PublicExperienceSlot } from '../types/experience';

export function validateExperienceApply(input: {
  adult: string; child: string; name: string; phone: string; agreed: boolean;
  childAllowed: boolean; selected?: PublicExperienceSlot;
}): Record<string, string> {
  const errors: Record<string, string> = {};
  const adult = Number(input.adult), child = Number(input.child);
  if (!input.selected) errors.slot = '開催日を選択してください。';
  if (!input.adult.trim() || !Number.isSafeInteger(adult) || adult < 1) errors.adult = '大人は1名以上の整数で入力してください。';
  if (!input.child.trim() || !Number.isSafeInteger(child) || child < 0 || (!input.childAllowed && child > 0)) errors.child = '子どもの人数を確認してください。';
  if (!errors.adult && !errors.child && input.selected && adult + child > input.selected.remainingCapacity) {
    errors.capacity = `残り枠（${input.selected.remainingCapacity}名）を超えています。人数を減らしてください。`;
  }
  if (!input.name.trim()) errors.name = '代表者氏名を入力してください。';
  const normalizedPhone = input.phone.normalize('NFKC').replace(/[() ー−-]/g, '');
  if (!/^\+?[0-9]{10,15}$/.test(normalizedPhone)) errors.phone = '電話番号を確認してください（数字10〜15桁、ハイフン可）。';
  if (!input.agreed) errors.agreed = 'キャンセルポリシーと注意事項への同意が必要です。';
  return errors;
}
