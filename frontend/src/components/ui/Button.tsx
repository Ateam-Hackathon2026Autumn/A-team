import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "outline";
  block?: boolean;
};

export default function Button({
  variant = "primary",
  block = false,
  className = "",
  type = "button",
  children,
  ...props
}: Props) {
  const appearance =
    variant === "outline"
      ? "bg-transparent text-marche-green hover:bg-marche-sage"
      : "bg-marche-green text-white hover:bg-marche-green-dark";

  return (
    <button
      {...props}
      type={type}
      className={[
        "inline-flex min-h-12 items-center justify-center gap-2",
        "rounded-full border border-marche-green px-6 py-3",
        "text-sm font-bold transition-colors",
        "disabled:border-gray-200 disabled:bg-gray-200 disabled:text-gray-500",
        appearance,
        block ? "mt-6 w-full" : "",
        className,
      ].join(" ")}
    >
      {children}
    </button>
  );
}