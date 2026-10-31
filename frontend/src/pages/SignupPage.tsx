import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useSearchParams } from "react-router";

import PurposeStep from "../components/signup/PurposeStep";
import AccountStep from "../components/signup/AccountStep";
import CompleteStep from "../components/signup/CompleteStep";
import { initialSignupValues } from "../types/authForm";
import type {
  Purpose,
  SignupErrors,
  SignupFormValues,
} from "../types/authForm";
import { validateSignup } from "../utils/authValidation";

export default function SignupPage() {
  const [params] = useSearchParams();
  const [purpose, setPurpose] = useState<Purpose | "">(
    params.get("purpose") === "producer" ? "producer" : "",
  );
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [values, setValues] = useState<SignupFormValues>({
    ...initialSignupValues,
  });
  const [errors, setErrors] = useState<SignupErrors>({});

  function update<K extends keyof SignupFormValues>(
    key: K,
    value: SignupFormValues[K],
  ) {
    setValues((previous) => ({ ...previous, [key]: value }));
    setErrors((previous) => ({ ...previous, [key]: undefined }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const found = validateSignup(values);
    setErrors(found);

    if (Object.keys(found).length > 0) {
      const firstKey = Object.keys(found)[0];
      event.currentTarget
        .querySelector<HTMLInputElement>(`[name="${firstKey}"]`)
        ?.focus();
      return;
    }

    // この段階ではAPI通信を行わず、入力検証のみ。
    setValues({ ...initialSignupValues });
    setStep(3);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const stepTitles = ["利用目的", "アカウント情報", "完了"];

  return (
    <>
      <ol
        aria-label="登録の進行状況"
        className="mb-8 flex list-none justify-between gap-2 p-0"
      >
        {stepTitles.map((title, index) => {
          const number = index + 1;
          const current = step === number;
          const completed = step > number;

          return (
            <li
              key={title}
              aria-current={current ? "step" : undefined}
              className={`flex items-center gap-1.5 text-[11px] sm:text-xs ${
                current
                  ? "font-bold text-marche-green"
                  : "text-marche-muted"
              }`}
            >
              <span
                className={`grid size-6 shrink-0 place-items-center rounded-full border ${
                  current || completed
                    ? "border-marche-green bg-marche-green text-white"
                    : "border-marche-line"
                }`}
              >
                {completed ? "✓" : number}
              </span>
              {title}
            </li>
          );
        })}
      </ol>

      {step === 1 && (
        <PurposeStep
          purpose={purpose}
          onChange={setPurpose}
          onNext={() => setStep(2)}
        />
      )}

      {step === 2 && purpose && (
        <AccountStep
          purpose={purpose}
          values={values}
          errors={errors}
          onChange={update}
          onBack={() => setStep(1)}
          onSubmit={handleSubmit}
        />
      )}

      {step === 3 && purpose && <CompleteStep purpose={purpose} />}

      {step !== 3 && (
        <p className="mt-6 text-center text-sm">
          アカウントをお持ちの方は{" "}
          <Link to="/signin" className="text-marche-green underline">
            ログイン
          </Link>
        </p>
      )}
    </>
  );
}