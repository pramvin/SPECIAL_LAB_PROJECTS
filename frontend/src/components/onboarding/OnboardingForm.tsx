"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { LogoWordmark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
import { Card, SectionLabel } from "@/components/ui/Card";

interface Option {
  value: string;
  label: string;
}

const QUESTIONS: {
  key: "horizon" | "max_loss_pct" | "experience" | "capital" | "sectors";
  title: string;
  multi?: boolean;
  options: Option[];
}[] = [
  {
    key: "horizon",
    title: "How long do you plan to hold a stock?",
    options: [
      { value: "1w", label: "1 week" },
      { value: "1m", label: "1 month" },
      { value: "3m", label: "3 months" },
    ],
  },
  {
    key: "max_loss_pct",
    title: "How much loss on one trade can you accept?",
    options: [
      { value: "2", label: "Up to 2%" },
      { value: "5", label: "Up to 5%" },
      { value: "10", label: "Up to 10%" },
    ],
  },
  {
    key: "experience",
    title: "How much investing experience do you have?",
    options: [
      { value: "beginner", label: "Beginner" },
      { value: "some", label: "Some experience" },
      { value: "experienced", label: "Experienced" },
    ],
  },
  {
    key: "capital",
    title: "How much capital would you invest (USD)?",
    options: [
      { value: "under_1k", label: "Under $1,000" },
      { value: "1k_10k", label: "$1,000 – $10,000" },
      { value: "over_10k", label: "Over $10,000" },
    ],
  },
  {
    key: "sectors",
    title: "Which sectors interest you? (pick any)",
    multi: true,
    options: [
      { value: "tech", label: "Technology" },
      { value: "healthcare", label: "Healthcare" },
      { value: "finance", label: "Finance" },
      { value: "energy", label: "Energy" },
      { value: "consumer", label: "Consumer" },
      { value: "any", label: "No preference" },
    ],
  },
];

export function OnboardingForm() {
  const router = useRouter();
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const complete = QUESTIONS.every((q) => (answers[q.key]?.length ?? 0) > 0);

  function pick(key: string, value: string, multi?: boolean) {
    setAnswers((prev) => {
      if (!multi) return { ...prev, [key]: [value] };
      const cur = prev[key] ?? [];
      return {
        ...prev,
        [key]: cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value],
      };
    });
  }

  async function submit() {
    setBusy(true);
    setError("");
    try {
      const res = await fetch("/api/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          horizon: answers.horizon[0],
          max_loss_pct: Number(answers.max_loss_pct[0]),
          experience: answers.experience[0],
          capital: answers.capital[0],
          sectors: answers.sectors,
        }),
      });
      if (!res.ok) {
        setError("Could not save your answers. Please try again.");
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
    <main className="mx-auto flex min-h-screen w-full max-w-xl flex-col gap-space-lg p-space-lg">
      <LogoWordmark compact />
      <div className="flex flex-col gap-1">
        <h1 className="font-headline-sm text-headline-sm text-on-surface">
          Tell us how you invest
        </h1>
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          5 quick questions so we can tailor trade ideas to you. You can change
          these later.
        </p>
      </div>
      {QUESTIONS.map((q, i) => (
        <Card key={q.key}>
          <fieldset className="flex flex-col gap-space-sm">
            <legend className="mb-space-sm flex flex-col gap-1">
              <SectionLabel>Question {i + 1} of 5</SectionLabel>
              <span className="font-title-md text-title-md text-on-surface">
                {q.title}
              </span>
            </legend>
            <div className="flex flex-wrap gap-space-sm">
              {q.options.map((o) => {
                const on = answers[q.key]?.includes(o.value);
                return (
                  <button
                    key={o.value}
                    type="button"
                    aria-pressed={on}
                    onClick={() => pick(q.key, o.value, q.multi)}
                    className={`h-10 rounded-md border px-space-md font-body-md text-body-md transition-colors ${
                      on
                        ? "border-primary-container bg-primary-container text-on-primary"
                        : "border-outline-variant bg-surface-container-lowest text-on-surface hover:bg-surface-container-low"
                    }`}
                  >
                    {o.label}
                  </button>
                );
              })}
            </div>
          </fieldset>
        </Card>
      ))}
      {error && <p className="font-body-sm text-body-sm text-error">{error}</p>}
      <Button onClick={submit} disabled={!complete || busy}>
        Save and continue
      </Button>
    </main>
  );
}
