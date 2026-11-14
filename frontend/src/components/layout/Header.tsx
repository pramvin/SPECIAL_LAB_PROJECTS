import { LogoWordmark, MaskedAvatar } from "@/components/brand/Logo";
import { PROFILE } from "@/lib/data/profile";
import { LogoutButton } from "./LogoutButton";
import { NavList } from "./NavList";

export function DesktopHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-surface-container-high/70 bg-white/80 backdrop-blur-xl">
      <div className="mx-auto flex h-14 w-full max-w-[1280px] items-center justify-between gap-4 px-5 sm:px-6 lg:px-8">
        <LogoWordmark compact />
        <div className="hidden md:block">
          <NavList variant="top" />
        </div>
        <div className="flex items-center gap-3">
          <LogoutButton className="hidden sm:inline-flex" />
          <MaskedAvatar name={PROFILE.name} size={32} />
        </div>
      </div>
    </header>
  );
}
