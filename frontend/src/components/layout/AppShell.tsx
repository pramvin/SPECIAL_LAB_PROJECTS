import { DesktopHeader } from "./Header";
import { MobileBottomNav } from "./MobileBottomNav";

/**
 * Responsive application shell.
 * Desktop: slim sticky top navigation + centered content.
 * Mobile: the same top bar plus a translucent bottom tab bar.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-surface">
      <DesktopHeader />
      <main className="scrollbar-quiet pb-24 pt-6 md:pt-10 lg:pb-16">
        <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-section-mobile px-5 sm:px-6 lg:gap-section lg:px-8">
          {children}
        </div>
      </main>
      <footer className="border-t border-surface-container-high bg-background">
        <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-3 px-5 py-8 pb-24 font-body-sm text-body-sm text-on-surface-variant sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8 lg:pb-8">
          <p>
            PlanWise AI is a prototype using example and delayed market data.
            It is not investment advice and nothing here is guaranteed.
          </p>
          <p className="shrink-0 text-on-surface-variant/70">
            Not investment advice · Not backtested
          </p>
        </div>
      </footer>
      <MobileBottomNav />
    </div>
  );
}
