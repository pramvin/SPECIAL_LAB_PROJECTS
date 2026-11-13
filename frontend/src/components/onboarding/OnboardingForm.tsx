"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { LogoWordmark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { SectionLabel } from "@/components/ui/Card";
import { LogoutButton } from "@/components/layout/LogoutButton";

interface Option {
  value: string;
  label: string;
}

const QUESTIONS: {
  key: "horizon" | "max_loss_pct" | "experience" | "capital" | "sectors";
  title: string;
  help: string;
  multi?: boolean;
  options: Option[];
}[] = [
  {
    key: "horizon",
    title: "How long do you plan to hold a stock?",
    help: "This sets the default holding period for your trade ideas.",
    options: [
      { value: "1w", label: "1 week" },
      { value: "1m", label: "1 month" },
      { value: "3m", label: "3 months" },
    ],
  },
  {
    key: "max_loss_pct",
    title: "How much loss on one trade can you accept?",
    help: "We use this to keep position sizes and stops in a range you choose.",
    options: [
      { value: "2", label: "Up to 2%" },
      { value: "5", label: "Up to 5%" },
      { value: "10", label: "Up to 10%" },
    ],
  },
  {
    key: "experience",
    title: "How much investing experience do you have?",
    help: "This helps us choose how much explanation to show.",
    options: [
      { value: "beginner", label: "Beginner" },
      { value: "some", label: "Some experience" },
      { value: "experienced", label: "Experienced" },
    ],
  },
  {
    key: "capital",
    title: "How much capital would you invest?",
    help: "Example amounts in USD. This prototype does not move money.",
    options: [
      { value: "under_1k", label: "Under $1,000" },
      { value: "1k_10k", label: "$1,000 – $10,000" },
      { value: "over_10k", label: "Over $10,000" },
    ],
  },
  {
    key: "sectors",
    title: "Which sectors interest you?",
    help: "Pick any that apply, or choose no preference.",
    multi: true,
    options: [
      { value: "tech", label: "Technology" },
      { value: "communication", label: "Communication" },
      { value: "healthcare", label: "Healthcare" },
      { value: "finance", label: "Finance" },
      { value: "energy", label: "Energy" },
      { value: "consumer_discretionary", label: "Consumer Discretionary" },
      { value: "consumer_staples", label: "Consumer Staples" },
      { value: "industrials", label: "Industrials" },
      { value: "materials", label: "Materials" },
      { value: "real_estate", label: "Real Estate" },
      { value: "utilities", label: "Utilities" },
      { value: "any", label: "No preference" },
    ],
  },
];

export function OnboardingForm() {
  const router = useRouter();
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const current = QUESTIONS[step];
  const answered = (answers[current.key]?.length ?? 0) > 0;
  const last = step === QUESTIONS.length - 1;
  const complete = QUESTIONS.every((q) => (answers[q.key]?.length ?? 0) > 0);

  function pick(key: string, value: string, multi?: boolean) {
    setAnswers((prev) => {
      if (!multi) return { ...prev, [key]: [value] };
      const cur = prev[key] ?? [];
      return {
        ...prev,
        [key]: cur.includes(value)
          ? cur.filter((v) => v !== value)
          : [...cur, value],
      };
    });
  }

  async function submit() {
    if (!complete) return;
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
    <main className="mx-auto flex min-h-screen w-full max-w-[720px] flex-col gap-10 px-5 py-8 sm:px-8 sm:py-12">
      <div className="flex items-center justify-between">
        <LogoWordmark compact />
        <LogoutButton />
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between font-body-sm text-body-sm text-on-surface-variant">
          <span>
            Question {step + 1} of {QUESTIONS.length}
          </span>
          <span>{Math.round(((step + 1) / QUESTIONS.length) * 100)}%</span>
        </div>
        <ProgressBar
          value={((step + 1) / QUESTIONS.length) * 100}
          size="sm"
          label="Onboarding progress"
        />
      </div>

      <section className="flex flex-col gap-8 rounded-[28px] bg-surface-container-lowest p-6 sm:p-10">
        <div className="flex flex-col gap-3">
          <SectionLabel>Personalize your ideas</SectionLabel>
          <h1 className="font-headline-lg text-headline-lg-mobile tracking-tight text-on-surface sm:text-[40px] sm:leading-[44px]">
            {current.title}
          </h1>
          <p className="max-w-xl font-body-md text-body-md text-on-surface-variant">
            {current.help}
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {current.options.map((o) => {
            const on = answers[current.key]?.includes(o.value);
            return (
              <button
                key={o.value}
                type="button"
                aria-pressed={on}
                onClick={() => pick(current.key, o.value, current.multi)}
                className={`flex items-center justify-between gap-3 rounded-2xl border px-5 py-4 text-left font-body-md text-body-md transition-colors ${
                  on
                    ? "border-tertiary-accent bg-primary-fixed text-on-primary-fixed"
                    : "border-surface-container-high bg-surface-container-lowest text-on-surface hover:border-outline-variant hover:bg-surface-container-low"
                }`}
              >
                <span>{o.label}</span>
                {on && <span className="text-tertiary-accent">✓</span>}
              </button>
            );
          })}
        </div>

        {error && <p className="font-body-sm text-body-sm text-error">{error}</p>}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-container-high pt-6">
          <Button
            variant="ghost"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0 || busy}
          >
            Back
          </Button>
          <Button
            onClick={() => {
              if (last) submit();
              else setStep((s) => Math.min(QUESTIONS.length - 1, s + 1));
            }}
            disabled={!answered || busy}
          >
            {busy ? "Saving…" : last ? "Save and continue" : "Continue"}
          </Button>
        </div>
      </section>
    </main>
  );
}
