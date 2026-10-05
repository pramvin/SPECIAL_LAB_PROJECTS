import { Icon } from "./Icon";

type Tone = "neutral" | "success" | "info" | "warning" | "danger";

const TONES: Record<Tone, string> = {
  neutral:
    "bg-surface-container-low text-on-surface-variant border-outline-variant",
  success:
    "bg-provenance-input-bg text-provenance-input-text border-provenance-input-border",
  info: "bg-provenance-ai-bg text-provenance-ai-text border-provenance-ai-border",
  warning:
    "bg-provenance-warning-bg text-provenance-warning-text border-provenance-warning-border",
  danger:
    "bg-provenance-warning-bg text-provenance-warning-text border-provenance-warning-border",
};

export function Badge({
  children,
  tone = "neutral",
  icon,
  className = "",
}: {
  children: React.ReactNode;
  tone?: Tone;
  icon?: string;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-label-code text-label-code uppercase tracking-wide ${TONES[tone]} ${className}`}
    >
      {icon && <Icon name={icon} className="text-[12px]" />}
      {children}
    </span>
  );
}
