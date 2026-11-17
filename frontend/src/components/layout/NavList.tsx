"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/lib/nav";
import { Icon } from "@/components/ui/Icon";

export function NavList({ variant }: { variant: "sidebar" | "bottom" | "top" }) {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  if (variant === "bottom") {
    return (
      <nav
        aria-label="Primary"
        className="flex h-full items-stretch justify-around px-2"
      >
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.id}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex flex-1 flex-col items-center justify-center gap-1 rounded-xl py-2 font-body-sm text-[11px] font-medium transition-colors ${
                active ? "text-tertiary-accent" : "text-on-surface-variant"
              }`}
            >
              <Icon name={item.icon} filled={active} className="text-[22px]" />
              <span>{item.shortLabel}</span>
            </Link>
          );
        })}
      </nav>
    );
  }

  if (variant === "top") {
    return (
      <nav aria-label="Primary" className="flex items-center gap-1">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.id}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`rounded-full px-4 py-2 font-body-sm text-body-sm font-medium transition-colors ${
                active
                  ? "bg-surface-container-low text-on-surface"
                  : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    );
  }

  return (
    <nav aria-label="Primary" className="flex flex-col gap-1">
      {NAV_ITEMS.map((item) => {
        const active = isActive(item.href);
        return (
          <Link
            key={item.id}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 rounded-xl px-4 py-3 font-body-md text-body-md transition-colors ${
              active
                ? "bg-primary-container font-medium text-on-primary"
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
