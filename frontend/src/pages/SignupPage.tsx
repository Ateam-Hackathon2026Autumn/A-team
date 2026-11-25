import { startTransition, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { flushSync } from "react-dom";
import { Link, useNavigate, useSearchParams } from "react-router";

import PurposeStep from "../components/signup/PurposeStep";
import { CheckIcon } from "../components/Icons";
import AccountStep from "../components/signup/AccountStep";
import { useSetAtom } from "jotai";
import { signup, checkSession, getPolicies } from "../api/authApi";
import type { Policies } from "../api/authApi";
import ApiError from "../api/apiError";
import { authenticatedNavigationAtom } from "../stores/userAtom";
import { initialSignupValues } from "../types/authForm";
import type {
  Purpose,
  SignupErrors,
  SignupFormValues,
} from "../types/authForm";
import { validateSignup } from "../utils/authValidation";

export default function SignupPage() {
  const navigate = useNavigate();
  const setAuthenticated = useSetAtom(authenticatedNavigationAtom);
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
  const [policies, setPolicies] = useState<Policies | null>(null);
  const [policiesStatus, setPoliciesStatus] = useState<"loading" | "ready" | "error">("loading");
  const mounted = useRef(false);
  const policiesRequest = useRef(0);

  async function loadPolicies() {
    if (!mounted.current) return;
    const request = ++policiesRequest.current;
    setPolicies(null);
    setPoliciesStatus("loading");
    try {
      const next = await getPolicies();
      if (mounted.current && request === policiesRequest.current) {
        setPolicies(next);
        setPoliciesStatus("ready");
      }
    } catch {
      if (mounted.current && request === policiesRequest.current) setPoliciesStatus("error");
    }
  }

  useEffect(() => {
    mounted.current = true;
    void loadPolicies();
    return () => { mounted.current = false; policiesRequest.current++; };
  }, []);

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
    if (policiesStatus !== "ready" || !policies) return;
    const form = event.currentTarget;
    setMessage("");

    const found = validateSignup(values);
    setErrors(found);

    if (Object.keys(found).length > 0) {
      const firstKey = Object.keys(found)[0];
      form
        .querySelector<HTMLInputElement>(`[name="${firstKey}"]`)
        ?.focus();
      return;
    }

    submitting.current = true;
    setIsSubmitting(true);
    try {
      const result = await signup(values, policies);
      if (!mounted.current) return;
      setValues({ ...initialSignupValues });
      const navigation = {
        to: "/signup/complete",
        state: { purpose, csrfRefreshFailed: result.csrfRefreshFailed, registered: true },
      };
      startTransition(() => {
        setAuthenticated({ user: result.user, navigation });
        navigate(navigation.to, { replace: true, state: navigation.state });
      });
    } catch (error) {
      if (!mounted.current) return;
      if (error instanceof ApiError && error.errorCode === "ALREADY_AUTHENTICATED") {
        try {
          const session = await checkSession();
          if (!mounted.current) return;
          if (session.authenticated) {
            startTransition(() => {
              setAuthenticated({ user: session.user, navigation: { to: "/" } });
              navigate("/", { replace: true });
            });
            return;
          }
        } catch { /* 以下の案内を表示 */ }
        if (!mounted.current) return;
        setMessage("ログイン状態を確認できませんでした。もう一度お試しください。");
      } else if (error instanceof ApiError) {
        const fieldErrors: SignupErrors = {};
        for (const key of Object.keys(initialSignupValues) as (keyof SignupFormValues)[]) {
          if (error.details[key]) fieldErrors[key] = error.details[key].join(" ");
        }
        if (error.errorCode === "EMAIL_ALREADY_EXISTS") fieldErrors.email = error.message;
        if (error.errorCode === "POLICY_VERSION_MISMATCH") {
          flushSync(() => {
            setIsSubmitting(false);
            setErrors(fieldErrors);
            setValues((previous) => ({ ...previous, agreedToTerms: false, agreedToPrivacyPolicy: false }));
          });
          setMessage("利用規約・プライバシーポリシーが更新されました。内容をご確認のうえ、もう一度同意してください。");
          await loadPolicies();
          if (mounted.current) form.querySelector<HTMLInputElement>('[name="agreedToTerms"]')?.focus();
        } else if (error.status === 400 || error.errorCode === "EMAIL_ALREADY_EXISTS") {
          flushSync(() => {
            setIsSubmitting(false);
            setErrors(fieldErrors);
          });
          const firstKey = Object.keys(fieldErrors)[0];
          if (firstKey) form.querySelector<HTMLInputElement>(`[name="${firstKey}"]`)?.focus();
          setMessage(error.message);
        } else {
          setErrors(fieldErrors);
          if (error.status === 429) setMessage("登録の試行回数が上限に達しました。時間を置いてから再度お試しください。");
          else setMessage(error.message);
        }
      } else setMessage("通信に失敗しました。登録結果が不明な場合は、先にログインをお試しください。");
    } finally {
      submitting.current = false;
      if (mounted.current) setIsSubmitting(false);
    }
  }

  const stepTitles = ["利用目的", "アカウント情報"];

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
                {completed ? <><span className="sr-only">完了: </span><CheckIcon className="size-4" /></> : number}
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
          policiesReady={policiesStatus === "ready"}
          policiesError={policiesStatus === "error"}
          onReloadPolicies={() => { void loadPolicies(); }}
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
