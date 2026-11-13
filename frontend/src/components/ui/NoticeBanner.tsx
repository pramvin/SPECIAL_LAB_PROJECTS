import { Icon } from "./Icon";

type Tone = "info" | "neutral" | "warning";

const TONES: Record<Tone, string> = {
  info: "bg-primary-fixed text-on-primary-fixed",
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
      className={`flex flex-col gap-3 rounded-[20px] p-4 md:flex-row md:items-center md:justify-between md:p-5 ${TONES[tone]} ${className}`}
    >
      <div className="flex items-start gap-3">
        <Icon name={icon} className="mt-0.5 text-[20px] opacity-80" />
        <div className="flex flex-col gap-1">
          {title && (
            <span className="font-title-md text-title-md">{title}</span>
          )}
          {children && (
            <div className="max-w-3xl font-body-sm text-body-sm opacity-80">
              {children}
            </div>
          )}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
