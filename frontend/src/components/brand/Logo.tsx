import { Icon } from "@/components/ui/Icon";

/**
 * PlanWise AI mark. SVG traced from images/planwise_ai_mark/code.html
 * so the brand renders crisply without an external asset request.
 */
export function LogoMark({ size = 40 }: { size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 48 48"
      width={size}
      height={size}
      fill="none"
      role="img"
      aria-label="PlanWise AI"
      className="shrink-0"
    >
      <rect width="48" height="48" rx="12" fill="#1b4332" />
      <circle
        cx="24"
        cy="24"
        r="14"
        stroke="#a3e635"
        strokeWidth="2.5"
        strokeDasharray="4 3"
      />
      <path
        d="M18 27L23 20L27 25L31 18"
        stroke="#ffffff"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="31" cy="18" r="2" fill="#a3e635" />
      <circle cx="24" cy="24" r="3" fill="#ffffff" />
    </svg>
  );
}

export function LogoWordmark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-space-sm">
      <LogoMark size={40} />
      <div className="flex min-w-0 flex-col">
        <span className="font-headline-sm text-headline-sm font-bold leading-tight tracking-tight text-primary">
          PlanWise AI
        </span>
        {!compact && (
          <span className="truncate font-label-code text-label-code text-on-surface-variant">
            Financial Planning Prototype • Draft
          </span>
        )}
      </div>
    </div>
  );
}

export function MaskedAvatar({
  name,
  size = 36,
}: {
  name: string;
  size?: number;
}) {
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("");
  return (
    <span
      aria-hidden
      className="flex shrink-0 items-center justify-center rounded-full bg-primary-fixed font-title-md text-title-md font-semibold text-on-primary-fixed"
      style={{ width: size, height: size }}
    >
      {initials}
    </span>
  );
}

export function IconLabel({
  icon,
  children,
  className = "",
}: {
  icon: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      <Icon name={icon} className="text-body-sm" />
      <span>{children}</span>
    </span>
  );
}
