"use client";

import Link from "next/link";
import { useState } from "react";
import { LogoWordmark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
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
        setError(
          typeof body?.detail === "string"
            ? body.detail
            : "Could not request a reset link. Please try again later.",
        );
        return;
      }
      setMessage(
        body?.message ??
          "If an account exists for that email, reset instructions will be sent.",
      );
    } catch {
      setError("Cannot reach the server. Is the backend running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-5 py-12">
      <div className="flex w-full max-w-[420px] flex-col gap-8">
        <div className="flex flex-col items-center gap-3 text-center">
          <LogoWordmark compact />
          <h1 className="font-headline-lg text-headline-lg-mobile tracking-tight text-on-surface sm:text-[40px] sm:leading-[44px]">
            Forgot password?
          </h1>
          <p className="max-w-sm font-body-md text-body-md text-on-surface-variant">
            Enter the email address for your account. If it exists, we will
            provide password-reset instructions.
          </p>
        </div>
        <form
          onSubmit={submit}
          className="flex flex-col gap-5 rounded-[28px] bg-surface-container-lowest p-6 sm:p-8"
        >
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
          {message && (
            <p role="status" className="font-body-sm text-body-sm text-on-surface">
              {message}
            </p>
          )}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Sending…" : "Request reset link"}
          </Button>
          <Link
            href="/login"
            className="text-center font-body-sm text-body-sm text-tertiary-accent hover:underline"
          >
            Back to sign in
          </Link>
        </form>
      </div>
    </main>
  );
}
