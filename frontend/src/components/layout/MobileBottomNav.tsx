import { NavList } from "./NavList";

export function MobileBottomNav() {
  return (
    <div className="fixed inset-x-0 bottom-0 z-50 h-16 border-t border-surface-container-high bg-white/85 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden">
      <NavList variant="bottom" />
    </div>
  );
}
