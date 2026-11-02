import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Link, type LinkProps } from 'react-router';

type CommonProps = {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md';
  className?: string;
  children: ReactNode;
};

type LinkButtonProps = CommonProps & Omit<LinkProps, 'className' | 'children'>;

type NativeButtonProps = CommonProps & { to?: undefined } & Omit<
    ButtonHTMLAttributes<HTMLButtonElement>,
    'className' | 'children'
  >;

type Props = LinkButtonProps | NativeButtonProps;

const baseClassName =
  'inline-flex items-center justify-center gap-2 rounded-full border font-bold transition-colors disabled:pointer-events-none disabled:opacity-50';

const variantClassNames = {
  primary: 'border-marche-green bg-marche-green text-white hover:bg-marche-green-dark',
  secondary: 'border-marche-line bg-white text-marche-green hover:bg-marche-canvas',
  danger: 'border-marche-red bg-white text-marche-red hover:bg-marche-red/10',
};

const sizeClassNames = {
  sm: 'px-4 py-1.5 text-xs',
  md: 'px-5 py-2 text-sm',
};

// 生産者管理画面の共通ボタン（to を渡すとリンクになる）
function DashboardButton({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...rest
}: Props) {
  const mergedClassName = `${baseClassName} ${variantClassNames[variant]} ${sizeClassNames[size]} ${className}`;

  if (rest.to !== undefined) {
    return (
      <Link {...rest} className={mergedClassName}>
        {children}
      </Link>
    );
  }

  const { type = 'button', ...buttonProps } = rest;

  return (
    <button {...buttonProps} type={type} className={mergedClassName}>
      {children}
    </button>
  );
}

export default DashboardButton;
