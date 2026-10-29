import type { FormEvent } from "react";
import Button from "../../../components/ui/Button";
import FormField from "../../../components/ui/FormField";
import { INTERESTS } from "../../../types/auth";
import type { Interest, SignupErrors, SignupFormValues } from "../../../types/auth";
import { todayJst } from "../validation";

const PREFECTURES = "北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県".split(" ");

type Props = {
  values: SignupFormValues;
  errors: SignupErrors;
  purpose: "consumer" | "producer";
  onChange: <K extends keyof SignupFormValues>(key: K, value: SignupFormValues[K]) => void;
  onBack: () => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
};

export default function AccountStep({ values, errors, purpose, onChange, onBack, onSubmit }: Props) {
  const toggleInterest = (interest: Interest) => onChange("interests", values.interests.includes(interest) ? values.interests.filter((v) => v !== interest) : [...values.interests, interest]);
  return (
    <>
      <p className="eyebrow">YOUR INFORMATION</p><h1>アカウント情報</h1>
      <p className="muted">{purpose === "producer" ? "生産者申請の前に、共通アカウントを作成します。" : "あなたと産地の、新しいつながりを。"}</p>
      <button className="plain" type="button" onClick={onBack}>← 利用目的を選び直す</button>
      <form noValidate onSubmit={onSubmit}>
        {Object.values(errors).some(Boolean) && <div className="summary" role="alert">入力内容をご確認ください。</div>}
        <div className="field-row">
          <FormField name="lastName" label="姓" value={values.lastName} onChange={(v) => onChange("lastName", v)} error={errors.lastName} maxLength={10} autoComplete="family-name" placeholder="山田" />
          <FormField name="firstName" label="名" value={values.firstName} onChange={(v) => onChange("firstName", v)} error={errors.firstName} maxLength={10} autoComplete="given-name" placeholder="太郎" />
        </div>
        <FormField name="email" label="メールアドレス" type="email" value={values.email} onChange={(v) => onChange("email", v)} error={errors.email} maxLength={255} autoComplete="email" placeholder="example@example.com" />
        <FormField name="password" label="パスワード" type="password" value={values.password} onChange={(v) => onChange("password", v)} error={errors.password} autoComplete="new-password" placeholder="8〜30文字・英大小数字記号を含む" maxLength={30} />
        <FormField name="phone" label="電話番号" type="tel" value={values.phone} onChange={(v) => onChange("phone", v)} error={errors.phone} maxLength={50} autoComplete="tel" placeholder="09012345678" />
        <p className="hint">ハイフン付きでも入力できます。</p>
        <FormField name="birthDate" label="生年月日" type="date" value={values.birthDate} onChange={(v) => onChange("birthDate", v)} error={errors.birthDate} max={todayJst()} autoComplete="bday" />
        <div className="field"><label htmlFor="prefectureId">都道府県<span className="optional">任意</span></label>
          <select id="prefectureId" name="prefectureId" value={values.prefectureId} onChange={(e) => onChange("prefectureId", e.target.value)}><option value="">選択してください</option>{PREFECTURES.map((p, i) => <option key={p} value={String(i + 1)}>{p}</option>)}</select>
        </div>
        <fieldset className="interests-fieldset"><legend>興味のあること <span className="optional">任意・複数選択可</span></legend>
          <div className="interests">{INTERESTS.map(({ value, label }) => <label className="chip" key={value}><input type="checkbox" checked={values.interests.includes(value)} onChange={() => toggleInterest(value)} />{label}</label>)}</div>
        </fieldset>
        <label className="check"><input type="checkbox" name="agreedToTerms" aria-invalid={Boolean(errors.agreedToTerms)} checked={values.agreedToTerms} onChange={(e) => onChange("agreedToTerms", e.target.checked)} />利用規約に同意する<span className="req">必須</span></label><span className="error" role={errors.agreedToTerms ? "alert" : undefined}>{errors.agreedToTerms}</span>
        <label className="check"><input type="checkbox" name="agreedToPrivacyPolicy" aria-invalid={Boolean(errors.agreedToPrivacyPolicy)} checked={values.agreedToPrivacyPolicy} onChange={(e) => onChange("agreedToPrivacyPolicy", e.target.checked)} />プライバシーポリシーに同意する<span className="req">必須</span></label><span className="error" role={errors.agreedToPrivacyPolicy ? "alert" : undefined}>{errors.agreedToPrivacyPolicy}</span>
        <p className="hint">※ 規約本文・正式な版番号の取得は今後の実装です。現在は画面動作のデモです。</p>
        <Button block type="submit">入力内容を確認 →</Button>
      </form>
    </>
  );
}
