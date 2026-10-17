import { redirect } from "next/navigation";
import { OnboardingForm } from "@/components/onboarding/OnboardingForm";
import { getMe } from "@/lib/session";

export default async function OnboardingPage() {
  const me = await getMe();
  if (!me) redirect("/login");
  return <OnboardingForm />;
}
