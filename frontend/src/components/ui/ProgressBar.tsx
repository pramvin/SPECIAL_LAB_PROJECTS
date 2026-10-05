export function ProgressBar({
  value,
  tone = "primary",
  size = "md",
  label,
  className = "",
}: {
  value: number; // 0..100
  tone?: "primary" | "secondary";
  size?: "sm" | "md";
  label?: string;
  className?: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      className={`w-full overflow-hidden rounded-full bg-surface-container-high ${
        size === "sm" ? "h-1.5" : "h-3"
      } ${className}`}
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <div
        className={`h-full rounded-full transition-all ${
          tone === "secondary" ? "bg-secondary" : "bg-primary-container"
        }`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
