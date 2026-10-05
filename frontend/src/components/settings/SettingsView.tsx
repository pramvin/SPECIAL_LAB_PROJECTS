"use client";

import { useState } from "react";
import { Card, CardHeader, SectionLabel } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { Toggle } from "@/components/ui/Toggle";
import { Badge } from "@/components/ui/Badge";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { MaskedAvatar } from "@/components/brand/Logo";
import { PROFILE } from "@/lib/data/profile";

type SettingItem = {
  id: string;
  title: string;
  description: string;
  defaultOn: boolean;
  supported: boolean;
};

const SETTINGS: SettingItem[] = [
  {
    id: "demo-mode",
    title: "Example Data Mode",
    description:
      "Use the synthetic portfolio profile. No real accounts or personal data are loaded.",
    defaultOn: true,
    supported: true,
  },
  {
    id: "mask-values",
    title: "Mask values by default",
    description:
      "Hide financial figures behind a masked state when the prototype loads (visual only).",
    defaultOn: false,
    supported: true,
  },
  {
    id: "session-only",
    title: "Session-only state",
    description:
      "Prototype holds data in memory for the session. Persistence and retention rules are TBD with the team.",
    defaultOn: true,
    supported: false,
  },
  {
    id: "analytics",
    title: "Product analytics",
    description:
      "Not implemented. Requires an explicit privacy decision before any telemetry is added.",
    defaultOn: false,
    supported: false,
  },
];

const OPEN_POINTS = [
  "Authentication and account model",
  "Bank / investment connections",
  "Data retention, deletion, and consent wording",
  "AI guidance boundaries and disclaimers",
];

export function SettingsView() {
  const [state, setState] = useState<Record<string, boolean>>(
    Object.fromEntries(SETTINGS.map((s) => [s.id, s.defaultOn])),
  );

  return (
    <>
      <div className="flex flex-col gap-1">
        <SectionLabel>Workspace Controls</SectionLabel>
        <h1 className="font-headline-lg text-headline-lg font-bold tracking-tight text-primary">
          Settings &amp; Privacy
        </h1>
        <p className="max-w-2xl font-body-sm text-body-sm text-on-surface-variant">
          Prototype preferences only. Controls marked TBD are not final product
          behavior and must be confirmed by the team before shipping.
        </p>
      </div>

      <Card className="flex flex-col gap-space-md">
        <CardHeader
          icon="person"
          title="Profile"
          subtitle={PROFILE.tierLabel}
          badge={<ProvenanceBadge provenance="example" />}
        />
        <div className="flex items-center gap-space-md">
          <MaskedAvatar name={PROFILE.name} size={48} />
          <div className="flex flex-col">
            <span className="font-title-md text-title-md text-on-surface">
              {PROFILE.name}
            </span>
            <span className="font-label-code text-label-code text-on-surface-variant">
              Synthetic profile • Demo mode
            </span>
          </div>
        </div>
      </Card>

      <Card className="flex flex-col gap-space-sm">
        <CardHeader
          icon="shield_person"
          title="Privacy & Data Controls"
          subtitle="All toggles below affect the prototype UI only."
        />
        <div className="flex flex-col divide-y divide-surface-container-high">
          {SETTINGS.map((setting) => (
            <div
              key={setting.id}
              className="flex items-start justify-between gap-space-md py-space-lg"
            >
              <div className="flex flex-col">
                <div className="flex items-center gap-space-xs">
                  <span className="font-title-md text-title-md text-on-surface">
                    {setting.title}
                  </span>
                  {!setting.supported && (
                    <Badge tone="neutral" icon="pending">
                      TBD
                    </Badge>
                  )}
                </div>
                <span className="max-w-xl font-body-sm text-body-sm text-on-surface-variant">
                  {setting.description}
                </span>
              </div>
              <Toggle
                checked={state[setting.id]}
                label={setting.title}
                onChange={
                  setting.supported
                    ? (next) =>
                        setState((prev) => ({ ...prev, [setting.id]: next }))
                    : undefined
                }
              />
            </div>
          ))}
        </div>
      </Card>

      <Card className="flex flex-col gap-space-md">
        <CardHeader
          icon="label"
          title="Data Provenance Legend"
          subtitle="How the prototype labels the source of every figure."
        />
        <div className="grid grid-cols-1 gap-space-sm sm:grid-cols-2">
          <div className="flex items-center gap-space-sm rounded-md bg-surface-container-low p-space-sm">
            <ProvenanceBadge provenance="input" />
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Values you typed or confirmed.
            </span>
          </div>
          <div className="flex items-center gap-space-sm rounded-md bg-surface-container-low p-space-sm">
            <ProvenanceBadge provenance="ai" />
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Generated guidance with stated assumptions.
            </span>
          </div>
          <div className="flex items-center gap-space-sm rounded-md bg-surface-container-low p-space-sm">
            <ProvenanceBadge provenance="example" />
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Synthetic demonstration data.
            </span>
          </div>
          <div className="flex items-center gap-space-sm rounded-md bg-surface-container-low p-space-sm">
            <ProvenanceBadge provenance="warning" />
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Something needs your review.
            </span>
          </div>
        </div>
      </Card>

      <Card className="flex flex-col gap-space-sm">
        <CardHeader
          icon="rule"
          title="Open Points (Not Yet Supported)"
          subtitle="Preserved as TBD per OVERVIEW.md §10."
        />
        <ul className="flex flex-col gap-space-sm">
          {OPEN_POINTS.map((point) => (
            <li
              key={point}
              className="flex items-center gap-space-sm font-body-sm text-body-sm text-on-surface-variant"
            >
              <Icon name="radio_button_unchecked" className="text-[16px]" />
              {point}
            </li>
          ))}
        </ul>
      </Card>
    </>
  );
}
