import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import type { FormEvent } from "react";
import type { Purpose, SignupErrors, SignupFormValues } from "../../types/auth";
import { initialSignupValues } from "../../types/auth";
import { validateSignup } from "./validation";
import PurposeStep from "./components/PurposeStep";
import AccountStep from "./components/AccountStep";
import CompleteStep from "./components/CompleteStep";
import "./SignupPage.css";

export default function SignupPage() {
  const [params] = useSearchParams();
  const [purpose, setPurpose] = useState<Purpose | "">(params.get("purpose") === "producer" ? "producer" : "");
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [values, setValues] = useState<SignupFormValues>({ ...initialSignupValues });
  const [errors, setErrors] = useState<SignupErrors>({});

  function update<K extends keyof SignupFormValues>(key: K, value: SignupFormValues[K]) {
    setValues((previous) => ({ ...previous, [key]: value }));
    setErrors((previous) => ({ ...previous, [key]: undefined }));
  }
  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const found = validateSignup(values);
    setErrors(found);
    if (Object.keys(found).length > 0) {
      const firstName = Object.keys(found)[0];
      document.querySelector<HTMLInputElement>(`[name="${firstName}"]`)?.focus();
      return;
    }
    // API通信は担当B。passwordや個人情報をLocalStorage等に保存しない。
    setValues({ ...initialSignupValues });
    setStep(3);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  const stepTitles = ["利用目的", "アカウント情報", "完了"];
  return (
    <>
      <ol className="steps" aria-label="登録の進行状況">{stepTitles.map((title, index) => {
        const n = (index + 1) as 1 | 2 | 3;
        return <li key={title} className={step === n ? "active" : step > n ? "done" : ""} aria-current={step === n ? "step" : undefined}><span>{step > n ? "✓" : n}</span>{title}</li>;
      })}</ol>
      {step === 1 && <PurposeStep purpose={purpose} onChange={setPurpose} onNext={() => setStep(2)} />}
      {step === 2 && purpose && <AccountStep purpose={purpose} values={values} errors={errors} onChange={update} onBack={() => setStep(1)} onSubmit={handleSubmit} />}
      {step === 3 && purpose && <CompleteStep purpose={purpose} />}
      {step !== 3 && <p className="center signin-invite">アカウントをお持ちの方は <Link to="/signin">ログイン</Link></p>}
    </>
  );
}
