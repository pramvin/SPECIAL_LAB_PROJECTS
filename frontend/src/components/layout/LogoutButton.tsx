"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Icon } from "@/components/ui/Icon";

/** Ends the session on the backend, then returns to /login. */
export function LogoutButton({ className = "" }: { className?: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function logout() {
    setPending(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  return (
    <button
      type="button"
      onClick={logout}
      disabled={pending}
      aria-label="Log out"
      title="Log out"
      className={`inline-flex items-center gap-space-xs font-body-sm text-body-sm text-on-surface-variant transition-colors hover:text-on-surface disabled:opacity-60 ${className}`}
    >
      <Icon name="logout" className="text-body-sm" />
      <span className="hidden sm:inline">{pending ? "Logging out…" : "Log out"}</span>
    </button>
  );
}
