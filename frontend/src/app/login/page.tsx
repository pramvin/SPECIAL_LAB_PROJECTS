"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { LogoWordmark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
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
    <main className="flex min-h-screen items-center justify-center p-space-lg">
      <div className="flex w-full max-w-sm flex-col gap-space-lg">
        <LogoWordmark compact />
        <Card>
          <form onSubmit={submit} className="flex flex-col gap-space-md">
            <h1 className="font-headline-sm text-headline-sm text-on-surface">
              {mode === "login" ? "Sign in" : "Create account"}
            </h1>
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
            <Button type="submit" disabled={busy}>
              {mode === "login" ? "Sign in" : "Create account"}
            </Button>
            {mode === "login" && (
              <Link
                href="/forgot-password"
                className="text-center font-body-sm text-body-sm text-primary underline-offset-4 hover:underline"
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
            >
              {mode === "login" ? "New here? Create an account" : "Have an account? Sign in"}
            </Button>
          </form>
        </Card>
      </div>
    </main>
  );
}
