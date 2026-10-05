import { Sidebar } from "./Sidebar";
import { DesktopHeader } from "./Header";
import { MobileTopBar } from "./MobileTopBar";
import { MobileBottomNav } from "./MobileBottomNav";

/**
 * Responsive application shell.
 * Desktop (lg+): fixed sidebar + fixed top header.
 * Mobile/tablet: sticky top bar + fixed bottom tab navigation.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-surface">
      <Sidebar />
      <MobileTopBar />
      <div className="lg:pl-72">
        <DesktopHeader />
        <main className="scrollbar-quiet px-space-md pb-24 pt-space-lg sm:px-space-lg lg:px-space-xl lg:pb-space-xl lg:pt-16">
          <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-section-mobile lg:gap-section">
            {children}
          </div>
        </main>
      </div>
      <MobileBottomNav />
    </div>
  );
}
