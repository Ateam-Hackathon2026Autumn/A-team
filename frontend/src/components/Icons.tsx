import type { ReactNode } from "react";

type IconProps = { className?: string };

function Icon({ className, children }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className ?? "size-5"}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function CheckIcon(props: IconProps) {
  return <Icon {...props}><path d="m5 12 4 4L19 6" /></Icon>;
}

export function StarIcon(props: IconProps) {
  return <Icon {...props}><path fill="currentColor" d="m12 3 2.8 5.8 6.2.9-4.5 4.4 1.1 6.2-5.6-2.9-5.6 2.9 1.1-6.2L3 9.7l6.2-.9L12 3Z" /></Icon>;
}

export function PlayIcon(props: IconProps) {
  return <Icon {...props}><path d="m8 5 11 7-11 7V5Z" /></Icon>;
}

export function PauseIcon(props: IconProps) {
  return <Icon {...props}><path d="M8 5v14m8-14v14" /></Icon>;
}
