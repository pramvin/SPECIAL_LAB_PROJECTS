"use client";

import Link from "next/link";
import { useState } from "react";
import { LogoWordmark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field, TextInput } from "@/components/ui/Field";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const res = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) {
        setError(typeof body?.detail === "string" ? body.detail : "Could not request a reset link. Please try again later.");
        return;
      }
      setMessage(body?.message ?? "If an account exists for that email, reset instructions will be sent.");
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
            <h1 className="font-headline-sm text-headline-sm text-on-surface">Forgot password?</h1>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Enter the email address for your account. If it exists, we will provide password-reset instructions.
            </p>
            <Field label="Email" htmlFor="email" error={error}>
              <TextInput
                id="email"
                type="email"
                autoComplete="email"
                required
                maxLength={254}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            {message && <p role="status" className="font-body-sm text-body-sm text-on-surface">{message}</p>}
            <Button type="submit" disabled={busy}>{busy ? "Sending…" : "Request reset link"}</Button>
            <Link href="/login" className="text-center font-body-sm text-body-sm text-primary underline-offset-4 hover:underline">
              Back to sign in
            </Link>
          </form>
        </Card>
      </div>
    </main>
  );
}
