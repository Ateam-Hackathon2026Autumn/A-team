import type { FormEvent } from "react";
import { TERMS_URL, PRIVACY_POLICY_URL, TERMS_VERSION, PRIVACY_POLICY_VERSION, SIGNUP_POLICY_CONFIGURED } from "../../config/env";
import Button from "../ui/Button";
import FormField from "../ui/FormField";
import { INTERESTS } from "../../types/authForm";
import type {
  Interest,
  Purpose,
  SignupErrors,
  SignupFormValues,
} from "../../types/authForm";
import { MIN_BIRTH_DATE, todayJst } from "../../utils/authValidation";

const PREFECTURES =
  "北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県".split(
    " ",
  );

type Props = {
  isSubmitting: boolean;
  message: string;
  values: SignupFormValues;
  errors: SignupErrors;
  purpose: Purpose;
  onChange: <K extends keyof SignupFormValues>(
    key: K,
    value: SignupFormValues[K],
  ) => void;
  onBack: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export default function AccountStep({
  isSubmitting,
  message,
  values,
  errors,
  purpose,
  onChange,
  onBack,
  onSubmit,
}: Props) {
  function toggleInterest(interest: Interest) {
    const next = values.interests.includes(interest)
      ? values.interests.filter((value) => value !== interest)
      : [...values.interests, interest];

    onChange("interests", next);
  }

  const agreements = [
    { key: "agreedToTerms", label: "利用規約に同意する" },
    {
      key: "agreedToPrivacyPolicy",
      label: "プライバシーポリシーに同意する",
    },
  ] as const;

  return (
    <>
      <p className="m-0 text-xs font-bold tracking-widest text-marche-green">
        YOUR INFORMATION
      </p>
      <h1 className="m-0 font-serif mt-2 text-3xl font-bold">アカウント情報</h1>
      <p className="m-0 mt-3 text-sm text-marche-muted">
        {purpose === "producer"
          ? "生産者申請の前に、共通アカウントを作成します。"
          : "あなたと産地の、新しいつながりを。"}
      </p>

      <button
        type="button"
        onClick={onBack}
        disabled={isSubmitting}
        className="font-sans cursor-pointer disabled:cursor-not-allowed mt-3 border-0 bg-transparent p-0 py-2 text-sm text-marche-green hover:underline"
      >
        ← 利用目的を選び直す
      </button>

      <form noValidate onSubmit={onSubmit} aria-busy={isSubmitting}>
        {message && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800">{message}</p>}
        {!SIGNUP_POLICY_CONFIGURED && <p role="alert" className="mt-4 text-sm text-red-800">利用規約の設定が完了していないため、現在は登録できません。</p>}
        <fieldset disabled={isSubmitting} className="m-0 min-w-0 border-0 p-0">
          {Object.values(errors).some(Boolean) && (
            <p
              role="alert"
              className="m-0 mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800"
            >
              入力内容をご確認ください。
            </p>
          )}

          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <FormField
              name="lastName"
              label="姓"
              value={values.lastName}
              onChange={(value) => onChange("lastName", value)}
              error={errors.lastName}
              maxLength={10}
              autoComplete="family-name"
              placeholder="山田"
            />
            <FormField
              name="firstName"
              label="名"
              value={values.firstName}
              onChange={(value) => onChange("firstName", value)}
              error={errors.firstName}
              maxLength={10}
              autoComplete="given-name"
              placeholder="太郎"
            />
          </div>

          <FormField
            name="email"
            label="メールアドレス"
            type="email"
            value={values.email}
            onChange={(value) => onChange("email", value)}
            error={errors.email}
            maxLength={254}
            autoComplete="email"
            placeholder="example@example.com"
          />

          <FormField
            name="password"
            label="パスワード"
            type="password"
            value={values.password}
            onChange={(value) => onChange("password", value)}
            error={errors.password}
            maxLength={30}
            autoComplete="new-password"
            placeholder="8〜30文字・英大小数字記号を含む"
          />

          <FormField
            name="phone"
            label="電話番号"
            type="tel"
            value={values.phone}
            onChange={(value) => onChange("phone", value)}
            error={errors.phone}
            maxLength={50}
            autoComplete="tel"
            placeholder="09012345678"
          />
          <p className="m-0 mt-1 text-xs text-marche-muted">
            ハイフン付きでも入力できます。
          </p>

          <FormField
            name="birthDate"
            label="生年月日"
            type="date"
            value={values.birthDate}
            onChange={(value) => onChange("birthDate", value)}
            error={errors.birthDate}
            max={todayJst()}
            min={MIN_BIRTH_DATE}
            autoComplete="bday"
          />

          <div className="mt-5">
            <label htmlFor="prefectureId" className="text-sm font-bold">
              都道府県
              <span className="ml-2 text-xs font-normal text-marche-muted">
                任意
              </span>
            </label>

            <select
              id="prefectureId"
              name="prefectureId"
              value={values.prefectureId}
              aria-invalid={Boolean(errors.prefectureId)}
              aria-describedby={errors.prefectureId ? 'prefectureId-error' : undefined}
              onChange={(event) => onChange("prefectureId", event.target.value)}
              className="font-sans mt-2 block h-12 w-full rounded-lg border border-[#b8c3b5] bg-white px-3 text-base"
            >
              <option value="">選択してください</option>
              {PREFECTURES.map((prefecture, index) => (
                <option key={prefecture} value={String(index + 1)}>
                  {prefecture}
                </option>
              ))}
            </select>
            {errors.prefectureId && <p id="prefectureId-error" role="alert" className="mt-1 text-xs text-red-800">{errors.prefectureId}</p>}
          </div>

          <fieldset className="m-0 mt-5 min-w-0 border-0 p-0">
            <legend className="text-sm font-bold">
              興味のあること
              <span className="ml-2 text-xs font-normal text-marche-muted">
                任意・複数選択可
              </span>
            </legend>

            <div className="mt-2 flex flex-wrap gap-2">
              {INTERESTS.map(({ value, label }) => {
                const checked = values.interests.includes(value);

                return (
                  <label
                    key={value}
                    className={`flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-xs ${
                      checked
                        ? "border-marche-green bg-marche-green text-white"
                        : "border-marche-line bg-white"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleInterest(value)}
                      className="font-sans accent-marche-green"
                    />
                    {label}
                  </label>
                );
              })}
            </div>
            {errors.interests && <p role="alert" className="mt-1 text-xs text-red-800">{errors.interests}</p>}
          </fieldset>

          {agreements.map(({ key, label }) => (
            <div key={key} className="mt-4">
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  name={key}
                  checked={values[key]}
                  onChange={(event) => onChange(key, event.target.checked)}
                  aria-invalid={Boolean(errors[key])}
                  aria-describedby={errors[key] ? `${key}-error` : undefined}
                  className="font-sans mt-1.5 size-4 shrink-0 accent-marche-green"
                />
                <span>
                  {label}
                  <span className="ml-2 text-xs text-red-800">必須</span>
                </span>
              </label>

              {errors[key] && (
                <p
                  id={`${key}-error`}
                  role="alert"
                  className="m-0 mt-1 text-xs text-red-800"
                >
                  {errors[key]}
                </p>
              )}
            </div>
          ))}

          {SIGNUP_POLICY_CONFIGURED && (
            <p className="m-0 mt-3 text-xs leading-6 text-marche-muted">
              <a href={TERMS_URL} target="_blank" rel="noopener noreferrer">利用規約（{TERMS_VERSION}）</a>
              ・<a href={PRIVACY_POLICY_URL} target="_blank" rel="noopener noreferrer">プライバシーポリシー（{PRIVACY_POLICY_VERSION}）</a>
              を確認して同意してください。
            </p>
          )}
          <Button block type="submit" disabled={isSubmitting || !SIGNUP_POLICY_CONFIGURED}>
            {isSubmitting ? "登録中…" : "登録する →"}
          </Button>
        </fieldset>
      </form>
    </>
  );
}
