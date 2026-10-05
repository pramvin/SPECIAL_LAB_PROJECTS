import { Icon } from "./Icon";

type Tone = "info" | "neutral" | "warning";

const TONES: Record<Tone, string> = {
  info: "bg-secondary-fixed/60 text-on-secondary-fixed",
  neutral: "bg-surface-container-low text-on-surface",
  warning: "bg-provenance-warning-bg text-provenance-warning-text",
};

export function NoticeBanner({
  icon = "info",
  title,
  children,
  action,
  tone = "info",
  className = "",
}: {
  icon?: string;
  title?: React.ReactNode;
  children?: React.ReactNode;
  action?: React.ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <div
      className={`flex flex-col gap-space-sm rounded-lg p-space-lg md:flex-row md:items-center md:justify-between ${TONES[tone]} ${className}`}
    >
      <div className="flex items-start gap-space-sm">
        <Icon name={icon} className="mt-0.5 text-[20px]" />
        <div className="flex flex-col">
          {title && (
            <span className="font-title-md text-title-md">{title}</span>
          )}
          {children && (
            <div className="font-body-sm text-body-sm opacity-90">
              {children}
            </div>
          )}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
