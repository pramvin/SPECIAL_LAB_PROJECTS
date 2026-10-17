import { cookies } from "next/headers";

export interface InvestorProfile {
  horizon: string;
  max_loss_pct: number;
  experience: string;
  capital: string;
  sectors: string[];
  risk_level: string;
}

export interface Me {
  email: string;
  profile: InvestorProfile | null;
}

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/** Current signed-in user from the backend, or null. Server-side only. */
export async function getMe(): Promise<Me | null> {
  const session = (await cookies()).get("session")?.value;
  if (!session) return null;
  try {
    const res = await fetch(`${BACKEND_URL}/api/me`, {
      headers: { cookie: `session=${session}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as Me) : null;
  } catch {
    return null;
  }
}
