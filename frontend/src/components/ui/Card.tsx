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
      className={`rounded-lg border border-surface-container-high bg-surface-container-lowest p-space-lg ${className}`}
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
    <div className={`flex items-start justify-between gap-space-md ${className}`}>
      <div className="flex items-start gap-space-sm">
        {icon && (
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-surface-container-low text-primary">
            <Icon name={icon} className="text-[20px]" />
          </span>
        )}
        <div className="flex flex-col">
          <div className="flex flex-wrap items-center gap-space-xs">
            <h2 className="font-headline-sm text-headline-sm text-on-surface">
              {title}
            </h2>
            {badge}
          </div>
          {subtitle && (
            <p className="font-body-sm text-body-sm text-on-surface-variant">
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
    <span className="block font-label-caps text-label-caps uppercase tracking-wider text-on-surface-variant">
      {children}
    </span>
  );
}
