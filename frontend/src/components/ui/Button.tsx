import type { ButtonHTMLAttributes } from "react";
import { Icon } from "./Icon";

type Variant = "primary" | "secondary" | "ghost" | "subtle";
type Size = "sm" | "md";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-primary-container text-on-primary hover:bg-primary-hover active:scale-[0.98]",
  secondary:
    "bg-surface-container-low text-on-surface hover:bg-surface-container-high active:scale-[0.98]",
  ghost:
    "bg-transparent text-tertiary-accent hover:bg-primary-fixed",
  subtle:
    "bg-primary-fixed text-on-primary-fixed hover:bg-tertiary-fixed-dim",
};

const SIZES: Record<Size, string> = {
  sm: "h-9 px-4 text-body-sm gap-1.5",
  md: "h-11 px-6 text-[15px] gap-2",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: string;
  iconClassName?: string;
  trailingIcon?: string;
}

export function Button({
  variant = "primary",
  size = "md",
  icon,
  iconClassName = "",
  trailingIcon,
  className = "",
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center rounded-full font-medium transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-40 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {icon && <Icon name={icon} className={`text-[18px] ${iconClassName}`} />}
      {children}
      {trailingIcon && <Icon name={trailingIcon} className="text-[18px]" />}
    </button>
  );
}
