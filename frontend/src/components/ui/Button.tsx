import type { ButtonHTMLAttributes } from "react";
import { Icon } from "./Icon";

type Variant = "primary" | "secondary" | "ghost" | "subtle";
type Size = "sm" | "md";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-primary-container text-on-primary hover:bg-primary-hover shadow-sm",
  secondary:
    "bg-transparent text-secondary border border-outline-variant hover:bg-surface-container-low",
  ghost:
    "bg-transparent text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface",
  subtle: "bg-surface-container-low text-primary hover:bg-surface-container-high",
};

const SIZES: Record<Size, string> = {
  sm: "h-8 px-space-md text-body-sm gap-1.5",
  md: "h-10 px-space-lg text-body-sm gap-2",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: string;
  trailingIcon?: string;
}

export function Button({
  variant = "primary",
  size = "md",
  icon,
  trailingIcon,
  className = "",
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {icon && <Icon name={icon} className="text-[18px]" />}
      {children}
      {trailingIcon && <Icon name={trailingIcon} className="text-[18px]" />}
    </button>
  );
}
