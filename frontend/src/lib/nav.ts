export interface NavItem {
  id: string;
  label: string;
  shortLabel: string;
  href: string;
  icon: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    shortLabel: "Dashboard",
    href: "/",
    icon: "dashboard",
  },
  {
    id: "goals",
    label: "Goals",
    shortLabel: "Goals",
    href: "/goals",
    icon: "flag",
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
