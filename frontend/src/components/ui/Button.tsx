import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "outline"; block?: boolean };
export default function Button({ variant = "primary", block = false, className = "", children, ...props }: Props) {
  return <button className={["btn", variant === "outline" && "outline", block && "block", className].filter(Boolean).join(" ")} {...props}>{children}</button>;
}
