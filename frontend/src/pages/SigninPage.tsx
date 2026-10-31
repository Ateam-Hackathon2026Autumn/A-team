import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router";

import Button from "../components/ui/Button";
import FormField from "../components/ui/FormField";
import { validateSignin } from "../utils/authValidation";

export default function SigninPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{
    email?: string;
    password?: string;
  }>({});
  const [message, setMessage] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const found = validateSignin(email, password);
    setErrors(found);
    setMessage("");

    if (found.email || found.password) return;

    setPassword("");
    setMessage(
      "入力チェックに成功しました（デモ）。API未接続のためログインは行っていません。",
    );
  }

  return (
    <>
      <p className="text-xs font-bold tracking-widest text-marche-green">
        SIGN IN
      </p>
      <h1 className="mt-2 text-3xl font-bold">ログイン</h1>
      <p className="mt-3 text-sm text-marche-muted">
        つながるマルシェへようこそ。
      </p>

      <form noValidate onSubmit={handleSubmit}>
        {(errors.email || errors.password) && (
          <p
            role="alert"
            className="mt-5 rounded-lg bg-red-50 p-3 text-sm text-red-800"
          >
            入力内容をご確認ください。
          </p>
        )}

        {message && (
          <p
            role="status"
            className="mt-5 rounded-xl bg-marche-sage p-4 text-sm"
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
          maxLength={255}
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

        <Button block type="submit">
          ログイン →
        </Button>
      </form>

      <div className="my-6 border-t border-marche-line" />
      <p className="text-center text-sm text-marche-muted">
        アカウントをお持ちでない方
      </p>

      <Link
        to="/signup"
        className="mt-4 flex min-h-12 items-center justify-center rounded-full border border-marche-green px-6 py-3 text-sm font-bold text-marche-green hover:bg-marche-sage"
      >
        新規登録
      </Link>
    </>
  );
}