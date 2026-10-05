"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/lib/nav";
import { Icon } from "@/components/ui/Icon";

export function NavList({ variant }: { variant: "sidebar" | "bottom" }) {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  if (variant === "bottom") {
    return (
      <nav
        aria-label="Primary"
        className="flex h-full items-stretch justify-around"
      >
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.id}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex flex-1 flex-col items-center justify-center gap-0.5 py-2 font-label-caps text-label-caps ${
                active ? "text-primary" : "text-on-surface-variant"
              }`}
            >
              <Icon
                name={item.icon}
                filled={active}
                className="text-[22px]"
              />
              <span>{item.shortLabel}</span>
            </Link>
          );
        })}
      </nav>
    );
  }

  return (
    <nav aria-label="Primary" className="flex flex-col gap-space-xs">
      {NAV_ITEMS.map((item) => {
        const active = isActive(item.href);
        return (
          <Link
            key={item.id}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-space-sm rounded-lg px-space-md py-space-sm font-body-md text-body-md transition-colors ${
              active
                ? "bg-primary-container font-title-md text-on-primary"
                : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
            }`}
          >
            <Icon name={item.icon} filled={active} />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
