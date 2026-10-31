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

export default function FormField({
  name,
  label,
  value,
  onChange,
  type = "text",
  error,
  required = true,
  ...rest
}: Props) {
  const [visible, setVisible] = useState(false);
  const isPassword = type === "password";

  return (
    <div className="mt-5">
      <label htmlFor={name} className="block text-sm font-bold">
        {label}
        <span
          className={`ml-2 text-xs font-normal ${
            required ? "text-red-800" : "text-marche-muted"
          }`}
        >
          {required ? "必須" : "任意"}
        </span>
      </label>

      <div className="relative mt-2">
        <input
          {...rest}
          id={name}
          name={name}
          type={isPassword && visible ? "text" : type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          required={required}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${name}-error` : undefined}
          className={[
            "block h-12 w-full min-w-0 rounded-lg border bg-white px-3",
            "text-base text-marche-ink",
            error ? "border-red-700" : "border-[#b8c3b5]",
            isPassword ? "pr-16" : "",
          ].join(" ")}
        />

        {isPassword && (
          <button
            type="button"
            aria-label={visible ? "パスワードを隠す" : "パスワードを表示"}
            aria-pressed={visible}
            onClick={() => setVisible((current) => !current)}
            className="absolute inset-y-0 right-1 my-auto min-h-10 border-0 bg-transparent px-3 text-xs font-bold text-marche-green"
          >
            {visible ? "隠す" : "表示"}
          </button>
        )}
      </div>

      {error && (
        <p
          id={`${name}-error`}
          role="alert"
          className="mt-1 text-xs text-red-800"
        >
          {error}
        </p>
      )}
    </div>
  );
}