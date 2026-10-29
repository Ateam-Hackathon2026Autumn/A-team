import { useState } from "react";
import type { HTMLInputTypeAttribute } from "react";

type Props = {
  name: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: HTMLInputTypeAttribute;
  error?: string;
  placeholder?: string;
  autoComplete?: string;
  maxLength?: number;
  max?: string;
  required?: boolean;
};

/** 共通入力欄。label、入力値、エラーメッセージを親から受け取ります。 */
export default function FormField({ name, label, value, onChange, type = "text", error, required = true, ...rest }: Props) {
  const [visible, setVisible] = useState(false);
  const isPassword = type === "password";
  const inputType = isPassword && visible ? "text" : type;
  return (
    <div className="field">
      <label htmlFor={name}>{label}{required ? <span className="req">必須</span> : <span className="optional">任意</span>}</label>
      <div className={isPassword ? "password" : undefined}>
        <input
          id={name}
          name={name}
          type={inputType}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${name}-error` : undefined}
          required={required}
          {...rest}
        />
        {isPassword && (
          <button className="reveal" type="button" aria-label={visible ? "パスワードを隠す" : "パスワードを表示"} onClick={() => setVisible((current) => !current)}>
            {visible ? "隠す" : "表示"}
          </button>
        )}
      </div>
      <span id={`${name}-error`} className="error" role={error ? "alert" : undefined}>{error}</span>
    </div>
  );
}
