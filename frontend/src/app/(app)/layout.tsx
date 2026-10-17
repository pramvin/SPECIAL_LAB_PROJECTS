import { redirect } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { getMe } from "@/lib/session";

export default async function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const me = await getMe();
  if (!me) redirect("/login");
  if (!me.profile) redirect("/onboarding");
  return <AppShell>{children}</AppShell>;
}
