import { Icon } from "@/components/ui/Icon";
import { MaskedAvatar } from "@/components/brand/Logo";
import { PROFILE } from "@/lib/data/profile";

export function DesktopHeader() {
  return (
    <header className="fixed left-72 right-0 top-0 z-40 hidden h-16 items-center justify-between border-b border-surface-container-high bg-surface/85 px-space-lg backdrop-blur-xl lg:flex">
      <div className="flex items-center gap-space-md">
        <span className="font-headline-sm text-headline-sm font-semibold tracking-tight text-on-surface">
          Advisory Workspace
        </span>
        <span className="inline-flex items-center gap-space-xs rounded-full bg-secondary-fixed px-2.5 py-1 font-label-code text-label-code text-on-secondary-fixed">
          <Icon name="lock" className="text-body-sm text-secondary" />
          Client Data Masked
        </span>
      </div>
      <div className="flex items-center gap-space-md">
        <a
          href="#"
          className="inline-flex items-center gap-space-xs font-body-sm text-body-sm text-on-surface-variant transition-colors hover:text-on-surface"
        >
          <Icon name="help_center" className="text-body-sm" />
          Help &amp; Glossary
        </a>
        <span className="h-5 w-px bg-outline-variant/40" />
        <MaskedAvatar name={PROFILE.name} size={32} />
      </div>
    </header>
  );
}
