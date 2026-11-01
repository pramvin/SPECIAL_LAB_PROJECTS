export interface NavItem {
  id: string;
  label: string;
  shortLabel: string;
  href: string;
  icon: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    id: "ideas",
    label: "Trade ideas",
    shortLabel: "Ideas",
    href: "/",
    icon: "trending_up",
  },
  {
    id: "goals",
    label: "Goals",
    shortLabel: "Goals",
    href: "/goals",
    icon: "flag",
  },
  {
  id: "watchlist",
  label: "Watchlist",
  shortLabel: "Watchlist",
  href: "/watchlist",
  icon: "bookmark",
  },
  {
    id: "assistant",
    label: "Plan & Assistant",
    shortLabel: "Assistant",
    href: "/assistant",
    icon: "psychology",
  },
  {
    id: "settings",
    label: "Settings & Privacy",
    shortLabel: "Settings",
    href: "/settings",
    icon: "shield_person",
  },
];
