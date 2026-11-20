import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router";

import { useSetAtom } from "jotai";
import { signin, checkSession } from "../api/authApi";
import ApiError from "../api/apiError";
import { loginStatusAtom, userInfoAtom } from "../stores/userAtom";
import Button from "../components/ui/Button";
import FormField from "../components/ui/FormField";
import { validateSignin } from "../utils/authValidation";

export default function SigninPage() {
  const navigate = useNavigate();
  const setLoginStatus = useSetAtom(loginStatusAtom);
  const setUserInfo = useSetAtom(userInfoAtom);
  const submitting = useRef(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{
    email?: string;
    password?: string;
  }>({});
  const [message, setMessage] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;

    const found = validateSignin(email, password);
    setErrors(found);
    setMessage("");

    if (found.email || found.password) return;

    submitting.current = true;
    setIsSubmitting(true);
    try {
      const result = await signin(email, password);
      setPassword("");
      setUserInfo(result.user);
      setLoginStatus("loggedIn");
      navigate("/", { replace: true });
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
        } catch { /* 以下の再試行案内を表示 */ }
        setMessage("ログイン状態を確認できませんでした。もう一度お試しください。");
      } else if (error instanceof ApiError) {
        if (error.status === 401) setMessage("メールアドレスまたはパスワードが正しくありません。");
        else if (error.status === 429) setMessage("ログインの試行回数が上限に達しました。時間を置いてから再度お試しください。");
        else {
          setErrors({ email: error.details.email?.join(" "), password: error.details.password?.join(" ") });
          setMessage(error.message);
        }
      } else setMessage("通信に失敗しました。接続を確認して再度お試しください。");
    } finally {
      submitting.current = false;
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <p className="m-0 text-xs font-bold tracking-widest text-marche-green">
        SIGN IN
      </p>
      <h1 className="m-0 font-serif mt-2 text-3xl font-bold">ログイン</h1>
      <p className="m-0 mt-3 text-sm text-marche-muted">
        つながるマルシェへようこそ。
      </p>

      <form noValidate onSubmit={handleSubmit} aria-busy={isSubmitting}>
        <fieldset disabled={isSubmitting} className="m-0 min-w-0 border-0 p-0">
          {(errors.email || errors.password) && (
            <p
              role="alert"
              className="m-0 mt-5 rounded-lg bg-red-50 p-3 text-sm text-red-800"
            >
              入力内容をご確認ください。
            </p>
          )}

          {message && (
            <p
              role="alert"
              className="m-0 mt-5 rounded-xl bg-marche-sage p-4 text-sm"
            >
              {message}
            </p>
          )}

          <FormField
            name="email"
            label="メールアドレス"
            type="email"
            value={email}
            onChange={(value) => {
              setEmail(value);
              setErrors((previous) => ({ ...previous, email: undefined }));
              setMessage("");
            }}
            error={errors.email}
            maxLength={254}
            autoComplete="email"
            placeholder="example@example.com"
          />

          <FormField
            name="password"
            label="パスワード"
            type="password"
            value={password}
            onChange={(value) => {
              setPassword(value);
              setErrors((previous) => ({ ...previous, password: undefined }));
              setMessage("");
            }}
            error={errors.password}
            autoComplete="current-password"
          />

          <Button block type="submit" disabled={isSubmitting}>
            {isSubmitting ? "ログイン中…" : "ログイン →"}
          </Button>
        </fieldset>
      </form>

      <div className="my-6 border-t border-marche-line" />
      <p className="m-0 text-center text-sm text-marche-muted">
        アカウントをお持ちでない方
      </p>

      <Link
        to="/signup"
        className="no-underline mt-4 flex min-h-12 items-center justify-center rounded-full border border-marche-green px-6 py-3 text-sm font-bold text-marche-green hover:bg-marche-sage"
      >
        新規登録
      </Link>
    </>
  );
}
