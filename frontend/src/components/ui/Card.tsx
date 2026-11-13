import { Icon } from "./Icon";

export function Card({
  children,
  className = "",
  as: Tag = "section",
}: {
  children: React.ReactNode;
  className?: string;
  as?: "section" | "div" | "article" | "aside";
}) {
  return (
    <Tag
      className={`rounded-[24px] border border-surface-container-high bg-surface-container-lowest p-6 md:p-8 ${className}`}
    >
      {children}
    </Tag>
  );
}

export function CardHeader({
  title,
  subtitle,
  icon,
  action,
  badge,
  className = "",
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: string;
  action?: React.ReactNode;
  badge?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between ${className}`}>
      <div className="flex items-start gap-3">
        {icon && (
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-container-low text-tertiary-accent">
            <Icon name={icon} className="text-[20px]" />
          </span>
        )}
        <div className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-headline-sm text-headline-sm text-on-surface">
              {title}
            </h2>
            {badge}
          </div>
          {subtitle && (
            <p className="max-w-2xl font-body-sm text-body-sm text-on-surface-variant">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {action}
    </div>
  );
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="block font-body-sm text-body-sm font-medium text-on-surface-variant">
      {children}
    </span>
  );
}
