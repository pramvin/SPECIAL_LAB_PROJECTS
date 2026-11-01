"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { LogoWordmark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field, TextInput } from "@/components/ui/Field";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    if (password !== confirmPassword) {
      setError("The passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) {
        setError(typeof body?.detail === "string" ? body.detail : "Could not reset your password. Request a new link.");
        return;
      }
      setMessage(body?.message ?? "Password updated. Please sign in again.");
    } catch {
      setError("Cannot reach the server. Is the backend running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-space-lg">
      <div className="flex w-full max-w-sm flex-col gap-space-lg">
        <LogoWordmark compact />
        <Card>
          <form onSubmit={submit} className="flex flex-col gap-space-md">
            <h1 className="font-headline-sm text-headline-sm text-on-surface">Set a new password</h1>
            {!token && <p role="alert" className="font-body-sm text-body-sm text-error">This reset link is missing its token. Request a new one.</p>}
            <Field label="New password" htmlFor="password" hint="Use at least 8 characters." error={error}>
              <TextInput id="password" type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={password} onChange={(e) => setPassword(e.target.value)} />
            </Field>
            <Field label="Confirm new password" htmlFor="confirm-password">
              <TextInput id="confirm-password" type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
            </Field>
            {message && <p role="status" className="font-body-sm text-body-sm text-on-surface">{message}</p>}
            <Button type="submit" disabled={busy || !token || Boolean(message)}>{busy ? "Updating…" : "Update password"}</Button>
            <Link href="/login" className="text-center font-body-sm text-body-sm text-primary underline-offset-4 hover:underline">Back to sign in</Link>
          </form>
        </Card>
      </div>
    </main>
  );
}

export default function ResetPasswordPage() {
  return <Suspense fallback={<main className="flex min-h-screen items-center justify-center">Loading…</main>}><ResetPasswordForm /></Suspense>;
}
