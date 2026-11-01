"use client";

import { usePathname } from "next/navigation";
import { LogoMark } from "@/components/brand/Logo";
import { Icon } from "@/components/ui/Icon";
import { NAV_ITEMS } from "@/lib/nav";

export function MobileTopBar() {
  const pathname = usePathname();
  const current =
    NAV_ITEMS.find((item) =>
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
    ) ?? NAV_ITEMS[0];

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between gap-space-sm border-b border-surface-container-high bg-surface px-space-md lg:hidden">
      <div className="flex items-center gap-space-sm">
        <LogoMark size={36} />
        <div className="flex min-w-0 flex-col">
          <span className="font-headline-sm text-headline-sm font-bold leading-tight tracking-tight text-primary">
            PlanWise
          </span>
          <span className="truncate font-label-code text-label-code text-on-surface-variant">
            {current.label}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-space-xs">
        <span className="hidden items-center gap-space-xs rounded-full bg-surface-container-low px-2.5 py-1 font-label-code text-label-code uppercase text-on-surface-variant sm:inline-flex">
          Draft Prototype
        </span>
        <span className="inline-flex items-center gap-space-xs rounded-full bg-secondary-fixed px-2.5 py-1 font-label-code text-label-code uppercase text-on-secondary-fixed">
          <Icon name="lock" className="text-[12px]" />
          Private
        </span>
      </div>
    </header>
  );
}
