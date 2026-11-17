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
      <rect width="48" height="48" rx="14" fill="#1d1d1f" />
      <circle
        cx="24"
        cy="24"
        r="14"
        stroke="#2997ff"
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
      <circle cx="31" cy="18" r="2" fill="#2997ff" />
      <circle cx="24" cy="24" r="3" fill="#ffffff" />
    </svg>
  );
}

export function LogoWordmark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <LogoMark size={36} />
      <div className="flex min-w-0 flex-col">
        <span className="font-headline-sm text-[20px] font-semibold leading-tight tracking-tight text-on-surface">
          PlanWise AI
        </span>
        {!compact && (
          <span className="truncate font-body-sm text-body-sm text-on-surface-variant">
            Financial planning prototype
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
      className="flex shrink-0 items-center justify-center rounded-full bg-surface-container-high font-title-md text-title-md font-semibold text-on-surface"
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
