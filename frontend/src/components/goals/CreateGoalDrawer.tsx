"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Field, SelectInput, TextInput } from "@/components/ui/Field";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { formatCurrency } from "@/lib/format";

function monthsUntil(iso: string): number {
  const target = new Date(`${iso}T00:00:00Z`);
  const now = new Date();
  const months =
    (target.getUTCFullYear() - now.getUTCFullYear()) * 12 +
    (target.getUTCMonth() - now.getUTCMonth());
  return Math.max(0, months);
}

export function CreateGoalDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [name, setName] = useState("New Vehicle Acquisition");
  const [category, setCategory] = useState("Custom");
  const [targetAmount, setTargetAmount] = useState(15000);
  const [initialDeposit, setInitialDeposit] = useState(20000);
  const [targetDate, setTargetDate] = useState("2026-11-30");
  const [monthly, setMonthly] = useState(500);

  const invalid = targetAmount <= initialDeposit;
  const horizon = useMemo(() => monthsUntil(targetDate), [targetDate]);

  return (
    <div
      className={`fixed inset-0 z-[60] ${open ? "" : "pointer-events-none"}`}
      aria-hidden={!open}
    >
      <div
        onClick={onClose}
        className={`absolute inset-0 bg-on-surface/20 transition-opacity ${
          open ? "opacity-100" : "opacity-0"
        }`}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Create goal"
        className={`scrollbar-quiet absolute right-0 top-0 flex h-full w-full max-w-md flex-col gap-space-md overflow-y-auto border-l border-surface-container-high bg-surface-container-lowest p-space-lg shadow-xl transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-start justify-between gap-space-md">
          <div>
            <span className="font-label-code text-label-code uppercase tracking-wider text-on-surface-variant">
              Interactive Modal / Drawer
            </span>
            <h2 className="font-headline-md text-headline-md text-on-surface">
              Create Goal{" "}
              <span className="text-body-sm text-on-surface-variant">
                (Prototype Step)
              </span>
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close create goal"
            className="rounded-md p-1 text-on-surface-variant hover:bg-surface-container-low"
          >
            <Icon name="close" />
          </button>
        </div>

        <Field label="Goal Name" required htmlFor="goal-name">
          <TextInput
            id="goal-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>

        <Field label="Category" htmlFor="goal-category">
          <SelectInput
            id="goal-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option>Custom</option>
            <option>Liquidity</option>
            <option>Real Estate</option>
            <option>Retirement</option>
            <option>Education</option>
          </SelectInput>
        </Field>

        <div className="grid grid-cols-2 gap-space-md">
          <Field label="Target Amount ($)" htmlFor="goal-target">
            <TextInput
              id="goal-target"
              inputMode="numeric"
              type="number"
              invalid={invalid}
              value={targetAmount}
              onChange={(e) => setTargetAmount(Number(e.target.value))}
            />
          </Field>
          <Field label="Initial Deposit ($)" htmlFor="goal-deposit">
            <TextInput
              id="goal-deposit"
              inputMode="numeric"
              type="number"
              invalid={invalid}
              value={initialDeposit}
              onChange={(e) => setInitialDeposit(Number(e.target.value))}
            />
          </Field>
        </div>

        {invalid && (
          <div
            role="alert"
            className="flex items-start gap-space-sm rounded-md bg-provenance-warning-bg p-space-sm font-body-sm text-body-sm text-provenance-warning-text"
          >
            <Icon name="error" className="mt-0.5 text-[18px]" />
            <span>
              Target amount must be greater than initial deposit (
              {formatCurrency(targetAmount)} vs{" "}
              {formatCurrency(initialDeposit)}).
            </span>
          </div>
        )}

        <div className="grid grid-cols-2 gap-space-md">
          <Field label="Target Date" htmlFor="goal-date">
            <TextInput
              id="goal-date"
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
            />
          </Field>
          <Field label="Monthly Contribution" htmlFor="goal-monthly">
            <TextInput
              id="goal-monthly"
              inputMode="numeric"
              type="number"
              value={monthly}
              onChange={(e) => setMonthly(Number(e.target.value))}
            />
          </Field>
        </div>

        <div className="flex flex-col gap-space-sm rounded-md bg-surface-container-low p-space-md">
          <div className="flex items-center justify-between">
            <span className="font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
              Projected Horizon
            </span>
            <span className="font-title-md text-title-md tabular-nums text-on-surface">
              {horizon} Months
            </span>
          </div>
          <ProgressBar value={Math.min(100, horizon * 3)} size="sm" />
          <span className="font-label-code text-label-code text-on-surface-variant">
            Visual estimate only
          </span>
        </div>

        <div className="flex items-start gap-space-sm rounded-md bg-provenance-ai-bg p-space-sm font-body-sm text-body-sm text-provenance-ai-text">
          <Icon name="info" className="mt-0.5 text-[18px]" />
          <span>
            Source of calculation disclosure: Timeline calculations rely on
            backend projection rules (Pending team approval OP-006). Visual
            estimate only.
          </span>
        </div>

        <div className="mt-auto flex items-center justify-end gap-space-sm border-t border-surface-container-high pt-space-md">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button icon="check" disabled={invalid} onClick={onClose}>
            Save Goal
          </Button>
        </div>
      </aside>
    </div>
  );
}
