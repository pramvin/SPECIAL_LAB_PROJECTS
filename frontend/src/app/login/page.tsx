"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { LogoWordmark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
import { Field, TextInput } from "@/components/ui/Field";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(
          typeof body?.detail === "string"
            ? body.detail
            : "Check your email and use a password of at least 8 characters.",
        );
        return;
      }
      router.replace("/");
      router.refresh();
    } catch {
      setError("Cannot reach the server. Is the backend running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-5 py-8">
      <div className="flex w-full max-w-[420px] flex-col gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <LogoWordmark compact />
          <h1 className="font-headline-lg text-headline-lg-mobile tracking-tight text-on-surface sm:text-[40px] sm:leading-[44px]">
            {mode === "login" ? "Sign in" : "Create account"}
          </h1>
          <p className="max-w-sm font-body-md text-body-md text-on-surface-variant">
            {mode === "login"
              ? "Welcome back. Sign in to see your trade ideas and saved stocks."
              : "Create a prototype account to personalize your trade ideas."}
          </p>
        </div>

        <form onSubmit={submit} className="flex flex-col gap-4 rounded-[28px] bg-surface-container-lowest p-6">
          <Field label="Email" htmlFor="email">
            <TextInput
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>
          <Field
            label="Password"
            htmlFor="password"
            hint={mode === "register" ? "At least 8 characters" : undefined}
            error={error}
          >
            <TextInput
              id="password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          <Button type="submit" disabled={busy} className="w-full">
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
          {mode === "login" && (
            <Link
              href="/forgot-password"
              className="text-center font-body-sm text-body-sm text-tertiary-accent hover:underline"
            >
              Forgot password?
            </Link>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
            }}
            className="w-full"
          >
            {mode === "login"
              ? "New here? Create an account"
              : "Have an account? Sign in"}
          </Button>
        </form>
      </div>
    </main>
  );
}
