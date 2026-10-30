import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router";
import Button from "../components/ui/Button";
import FormField from "../components/ui/FormField";
import { validateSignin } from "../utils/authValidation";
import "./SigninPage.css";

export default function SigninPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [message, setMessage] = useState("");

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const found = validateSignin(email, password);
    setErrors(found);
    if (found.email || found.password) {
      setMessage("");
      return;
    }
    setPassword(""); // API未接続なのでログイン情報を保持しない
    setMessage("入力チェックに成功しました（デモ）。API未接続のためログインは行っていません。");
  }
  return (
    <>
      <p className="eyebrow">SIGN IN</p>
      <h1>ログイン</h1>
      <p className="muted">つながるマルシェへようこそ。</p>
      <form noValidate onSubmit={handleSubmit}>
        {Boolean(errors.email || errors.password) && (
          <div className="summary" role="alert">
            入力内容をご確認ください。
          </div>
        )}
        {message && (
          <div className="notice" role="status">
            {message}
          </div>
        )}
        <FormField
          name="email"
          label="メールアドレス"
          type="email"
          value={email}
          onChange={(v) => {
            setEmail(v);
            setErrors((e) => ({ ...e, email: undefined }));
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
          onChange={(v) => {
            setPassword(v);
            setErrors((e) => ({ ...e, password: undefined }));
            setMessage("");
          }}
          error={errors.password}
          autoComplete="current-password"
        />
        <Button block type="submit">
          ログイン →
        </Button>
      </form>
      <div className="separator" />
      <p className="center muted signup-invite">アカウントをお持ちでない方</p>
      <Link className="btn outline block" to="/signup">
        新規登録
      </Link>
    </>
  );
}
