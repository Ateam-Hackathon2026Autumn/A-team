import type { SignupErrors, SignupFormValues } from "../../types/auth";

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const passwordPattern = /^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[!-/:-@\[-`{-~])[\x21-\x7E]{8,30}$/;
export const todayJst = () => new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());

export function validateEmail(email: string): string | undefined {
  if (!emailPattern.test(email.trim()) || email.trim().length > 255) return "メールアドレスを正しく入力してください。";
}
export function validateSignin(email: string, password: string) {
  return {
    email: validateEmail(email),
    password: !password ? "パスワードを入力してください。" : password.length > 128 ? "128文字以内で入力してください。" : undefined,
  };
}
export function validateSignup(values: SignupFormValues): SignupErrors {
  const errors: SignupErrors = {};
  for (const key of ["lastName", "firstName"] as const) {
    const s = values[key].trim();
    if (s.length < 1 || [...s].length > 10) errors[key] = "1〜10文字で入力してください。";
  }
  errors.email = validateEmail(values.email);
  if (!passwordPattern.test(values.password)) errors.password = "8〜30文字の半角英数字・記号で、英大文字・英小文字・数字・記号を各1文字以上含めてください。";
  const phone = values.phone.trim();
  if (!/^\+?[0-9() -]{7,50}$/.test(phone) || phone.replace(/\D/g, "").length < 7) errors.phone = "電話番号を正しく入力してください。";
  const date = values.birthDate;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(Date.parse(date)) || new Date(date).toISOString().slice(0, 10) !== date || date > todayJst()) errors.birthDate = "過去または今日の実在する日付を入力してください。";
  if (!values.agreedToTerms) errors.agreedToTerms = "利用規約への同意が必要です。";
  if (!values.agreedToPrivacyPolicy) errors.agreedToPrivacyPolicy = "プライバシーポリシーへの同意が必要です。";
  for (const key of Object.keys(errors) as (keyof SignupFormValues)[]) if (!errors[key]) delete errors[key];
  return errors;
}
