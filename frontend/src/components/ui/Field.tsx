import type { InputHTMLAttributes, SelectHTMLAttributes } from "react";

const FIELD =
  "h-10 w-full rounded-md border border-outline-variant bg-surface-container-lowest px-space-md font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant/60 focus:border-tertiary-accent focus:outline-none focus:ring-2 focus:ring-tertiary-accent/20";

export function Field({
  label,
  required,
  hint,
  error,
  children,
  htmlFor,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  children: React.ReactNode;
  htmlFor?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={htmlFor}
        className="flex items-center justify-between font-label-caps text-label-caps uppercase tracking-wide text-on-surface-variant"
      >
        <span>{label}</span>
        {required && <span className="text-on-surface-variant">Required</span>}
      </label>
      {children}
      {hint && !error && (
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          {hint}
        </span>
      )}
      {error && (
        <span className="font-body-sm text-body-sm text-error">{error}</span>
      )}
    </div>
  );
}

export function TextInput({
  invalid,
  className = "",
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  return (
    <input
      aria-invalid={invalid || undefined}
      className={`${FIELD} ${invalid ? "border-error focus:border-error focus:ring-error/20" : ""} ${className}`}
      {...rest}
    />
  );
}

export function SelectInput({
  invalid,
  className = "",
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean }) {
  return (
    <select
      aria-invalid={invalid || undefined}
      className={`${FIELD} appearance-none pr-9 ${invalid ? "border-error" : ""} ${className}`}
      {...rest}
    >
      {children}
    </select>
  );
}
