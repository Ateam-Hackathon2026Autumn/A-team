import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import PurposeStep from "../components/signup/PurposeStep";
import AccountStep from "../components/signup/AccountStep";
import { useSetAtom } from "jotai";
import { signup, checkSession } from "../api/authApi";
import ApiError from "../api/apiError";
import { SIGNUP_POLICY_CONFIGURED } from "../config/env";
import { loginStatusAtom, userInfoAtom } from "../stores/userAtom";
import { initialSignupValues } from "../types/authForm";
import type {
  Purpose,
  SignupErrors,
  SignupFormValues,
} from "../types/authForm";
import { validateSignup } from "../utils/authValidation";

export default function SignupPage() {
  const navigate = useNavigate();
  const setUserInfo = useSetAtom(userInfoAtom);
  const setLoginStatus = useSetAtom(loginStatusAtom);
  const submitting = useRef(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [params] = useSearchParams();
  const [purpose, setPurpose] = useState<Purpose | "">(
    params.get("purpose") === "producer" ? "producer" : "",
  );
  const [step, setStep] = useState<1 | 2>(1);
  const [values, setValues] = useState<SignupFormValues>({
    ...initialSignupValues,
  });
  const [errors, setErrors] = useState<SignupErrors>({});

  function update<K extends keyof SignupFormValues>(
    key: K,
    value: SignupFormValues[K],
  ) {
    setMessage("");
    setValues((previous) => ({ ...previous, [key]: value }));
    setErrors((previous) => ({ ...previous, [key]: undefined }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    setMessage("");
    if (!SIGNUP_POLICY_CONFIGURED) {
      setMessage("利用規約の設定が完了していないため、現在は登録できません。");
      return;
    }

    const found = validateSignup(values);
    setErrors(found);

    if (Object.keys(found).length > 0) {
      const firstKey = Object.keys(found)[0];
      event.currentTarget
        .querySelector<HTMLInputElement>(`[name="${firstKey}"]`)
        ?.focus();
      return;
    }

    submitting.current = true;
    setIsSubmitting(true);
    try {
      const result = await signup(values);
      setValues({ ...initialSignupValues });
      setUserInfo(result.user);
      setLoginStatus("loggedIn");
      navigate("/signup/complete", { replace: true, state: { purpose, csrfRefreshFailed: result.csrfRefreshFailed, registered: true } });
    } catch (error) {
      if (error instanceof ApiError && error.errorCode === "ALREADY_AUTHENTICATED") {
        try {
          const session = await checkSession();
          if (session.authenticated) {
            setUserInfo(session.user);
            setLoginStatus("loggedIn");
            navigate("/", { replace: true });
            return;
          }
        } catch { /* 以下の案内を表示 */ }
        setMessage("ログイン状態を確認できませんでした。もう一度お試しください。");
      } else if (error instanceof ApiError) {
        const fieldErrors: SignupErrors = {};
        for (const key of Object.keys(initialSignupValues) as (keyof SignupFormValues)[]) {
          if (error.details[key]) fieldErrors[key] = error.details[key].join(" ");
        }
        if (error.errorCode === "EMAIL_ALREADY_EXISTS") fieldErrors.email = error.message;
        setErrors(fieldErrors);
        if (error.errorCode === "POLICY_VERSION_MISMATCH") {
          setValues((previous) => ({ ...previous, agreedToTerms: false, agreedToPrivacyPolicy: false }));
          setMessage("規約が更新されています。ページを再読み込みして最新の内容をご確認ください。解消しない場合は運営へお問い合わせください。");
        } else if (error.status === 429) setMessage("登録の試行回数が上限に達しました。時間を置いてから再度お試しください。");
        else setMessage(error.message);
      } else setMessage("通信に失敗しました。登録結果が不明な場合は、先にログインをお試しください。");
    } finally {
      submitting.current = false;
      setIsSubmitting(false);
    }
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
          isSubmitting={isSubmitting}
          message={message}
          values={values}
          errors={errors}
          onChange={update}
          onBack={() => setStep(1)}
          onSubmit={handleSubmit}
        />
      )}

      <p className="m-0 mt-6 text-center text-sm">
          アカウントをお持ちの方は{" "}
          <Link to="/signin" className="no-underline text-marche-green underline">
            ログイン
          </Link>
      </p>
    </>
  );
}
