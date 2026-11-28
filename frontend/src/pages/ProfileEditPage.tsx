import { useState, type FormEvent } from 'react';
import { useSetAtom } from 'jotai';
import {
  getConsumerAccount,
  updateConsumerProfile,
} from '../api/consumerAccountApi';
import { usePublicContent } from '../hooks/usePublicContent';
import { userInfoAtom } from '../stores/userAtom';
import type { ConsumerAccount } from '../types/consumerAccount';
import { PREFECTURES } from '../utils/prefectures';
import { ContentPage, ContentStatus } from '../components/ui/ContentPage';
import { fieldClass, panelClass } from '../components/ui/contentPageValues';
import Button from '../components/ui/Button';
import MyPageNavigation from '../components/mypage/MyPageNavigation';
import { profilePhoneField } from '../utils/profilePhone';
const interests = [
  ['vegetables', '野菜'],
  ['fruits', '果物'],
  ['seafood', '魚介'],
  ['experiences', '体験'],
  ['short_term_jobs', '短期のお仕事'],
  ['farming', '農業'],
];
function ProfileForm({ account }: { account: ConsumerAccount }) {
  const [values, setValues] = useState({
    lastName: account.user.lastName,
    firstName: account.user.firstName,
    phone: account.profile.phone ?? '',
    birthDate: account.profile.birthDate ?? '',
    prefectureId: account.profile.prefectureId?.toString() ?? '',
    interests: account.profile.interests,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const setUser = useSetAtom(userInfoAtom);
  const today = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Tokyo',
  }).format(new Date());
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    setError('');
    setNotice('');
    if (!values.lastName.trim() || !values.firstName.trim()) {
      setError('姓と名を入力してください。');
      return;
    }
    if (
      [...values.lastName.trim()].length > 10 ||
      [...values.firstName.trim()].length > 10
    ) {
      setError('姓と名はそれぞれ10文字以内で入力してください。');
      return;
    }
    if (!/^0\d{9,10}$/.test(values.phone.replace(/-/g, ''))) {
      setError('電話番号は0から始まる10〜11桁の半角数字で入力してください。');
      return;
    }
    if (
      !values.birthDate ||
      values.birthDate < '1900-01-01' ||
      values.birthDate > today
    ) {
      setError('生年月日は1900年1月1日から今日までの日付を入力してください。');
      return;
    }
    setBusy(true);
    try {
      const result = await updateConsumerProfile({
        ...values,
        ...profilePhoneField(values.phone),
        lastName: values.lastName.trim(),
        firstName: values.firstName.trim(),
        prefectureId: values.prefectureId ? Number(values.prefectureId) : null,
      });
      setUser(result.user);
      setNotice('プロフィールを保存しました。');
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : '保存できませんでした。',
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <form
      onSubmit={submit}
      className={`${panelClass} max-w-3xl`}
      aria-busy={busy}
    >
      <h2 className="mt-0 font-serif text-xl">基本情報</h2>
      <p className="text-sm text-marche-muted">
        メールアドレス：{account.user.email}
      </p>
      <fieldset disabled={busy} className="m-0 min-w-0 space-y-5 border-0 p-0">
        <legend className="sr-only">プロフィールの入力</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          {(['lastName', 'firstName'] as const).map((name, i) => (
            <label key={name} className="block text-sm font-bold">
              {i === 0 ? '姓' : '名'}（必須）
              <input
                autoComplete={i === 0 ? 'family-name' : 'given-name'}
                required
                maxLength={10}
                className={`${fieldClass} mt-2`}
                value={values[name]}
                onChange={(e) => {
                  setValues({ ...values, [name]: e.target.value });
                  setNotice('');
                }}
              />
            </label>
          ))}
        </div>
        <label className="block text-sm font-bold">
          電話番号（必須）
          <input
            type="tel"
            autoComplete="tel"
            required
            maxLength={20}
            className={`${fieldClass} mt-2`}
            value={values.phone}
            onChange={(e) => {
              setValues({ ...values, phone: e.target.value });
              setNotice('');
            }}
          />
        </label>
        <label className="block text-sm font-bold">
          生年月日（必須）
          <input
            type="date"
            required
            min="1900-01-01"
            max={today}
            className={`${fieldClass} mt-2`}
            value={values.birthDate}
            onChange={(e) => {
              setValues({ ...values, birthDate: e.target.value });
              setNotice('');
            }}
          />
        </label>
        <label className="block text-sm font-bold">
          お住まいの都道府県
          <select
            autoComplete="address-level1"
            className={`${fieldClass} mt-2`}
            value={values.prefectureId}
            onChange={(e) => {
              setValues({ ...values, prefectureId: e.target.value });
              setNotice('');
            }}
          >
            <option value="">未設定</option>
            {PREFECTURES.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <fieldset className="m-0 rounded-xl border border-solid border-marche-line p-4">
          <legend className="px-2 text-sm font-bold">興味のあること</legend>
          <div className="flex flex-wrap gap-4">
            {interests.map(([key, label]) => (
              <label
                key={key}
                className="inline-flex min-h-11 items-center gap-2 text-sm"
              >
                <input
                  type="checkbox"
                  checked={values.interests.includes(key)}
                  onChange={(e) => {
                    setValues({
                      ...values,
                      interests: e.target.checked
                        ? [...values.interests, key]
                        : values.interests.filter((i) => i !== key),
                    });
                    setNotice('');
                  }}
                  className="size-4 accent-marche-green"
                />
                {label}
              </label>
            ))}
          </div>
        </fieldset>
      </fieldset>
      {error && (
        <p role="alert" className="text-sm font-bold text-marche-red">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="text-sm font-bold text-marche-green">
          {notice}
        </p>
      )}
      <Button type="submit" disabled={busy} className="mt-6">
        {busy ? '保存中…' : '変更を保存する'}
      </Button>
    </form>
  );
}
export default function ProfileEditPage() {
  const state = usePublicContent(getConsumerAccount);
  return (
    <ContentPage
      eyebrow="PROFILE"
      title="プロフィール編集"
      intro="あなたのことを教えてください。"
    >
      <MyPageNavigation />
      <ContentStatus {...state} />
      {state.data && <ProfileForm account={state.data} />}
    </ContentPage>
  );
}
