import { NavList } from "./NavList";

export function MobileBottomNav() {
  return (
    <div className="fixed inset-x-0 bottom-0 z-40 h-16 border-t border-surface-container-high bg-surface-container-lowest/95 backdrop-blur-xl lg:hidden">
      <NavList variant="bottom" />
    </div>
  );
}
