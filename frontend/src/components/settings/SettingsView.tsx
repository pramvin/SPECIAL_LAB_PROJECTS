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
    title: "Example data mode",
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
      "The prototype holds data in memory for the session. Persistence and retention rules are TBD with the team.",
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
    <div className="flex flex-col gap-12 lg:gap-16">
      <header className="flex flex-col gap-4">
        <SectionLabel>Workspace controls</SectionLabel>
        <h1 className="max-w-3xl font-headline-lg text-headline-lg-mobile tracking-tight text-on-surface sm:text-headline-lg">
          Settings &amp; privacy
        </h1>
        <p className="max-w-2xl font-body-lg text-body-lg text-on-surface-variant">
          Prototype preferences only. Controls marked TBD are not final product
          behavior and must be confirmed by the team before shipping.
        </p>
      </header>

      <Card className="flex flex-col gap-6">
        <CardHeader
          icon="person"
          title="Profile"
          subtitle={PROFILE.tierLabel}
          badge={<ProvenanceBadge provenance="example" />}
        />
        <div className="flex items-center gap-4">
          <MaskedAvatar name={PROFILE.name} size={52} />
          <div className="flex flex-col gap-1">
            <span className="font-title-md text-title-md text-on-surface">
              {PROFILE.name}
            </span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Synthetic profile · demo mode
            </span>
          </div>
        </div>
      </Card>

      <Card className="flex flex-col gap-2">
        <CardHeader
          icon="shield_person"
          title="Privacy & data controls"
          subtitle="All toggles below affect the prototype UI only."
        />
        <div className="flex flex-col divide-y divide-surface-container-high">
          {SETTINGS.map((setting) => (
            <div
              key={setting.id}
              className="flex items-start justify-between gap-6 py-6"
            >
              <div className="flex flex-col gap-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-title-md text-title-md text-on-surface">
                    {setting.title}
                  </span>
                  {!setting.supported && (
                    <Badge tone="neutral" icon="pending">
                      TBD
                    </Badge>
                  )}
                </div>
                <span className="max-w-2xl font-body-sm text-body-sm text-on-surface-variant">
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

      <Card className="flex flex-col gap-6">
        <CardHeader
          icon="label"
          title="Data provenance legend"
          subtitle="How the prototype labels the source of every figure."
        />
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            {
              provenance: "input" as const,
              text: "Values you typed or confirmed.",
            },
            {
              provenance: "ai" as const,
              text: "Generated guidance with stated assumptions.",
            },
            {
              provenance: "example" as const,
              text: "Synthetic demonstration data.",
            },
            {
              provenance: "warning" as const,
              text: "Something needs your review.",
            },
          ].map((item) => (
            <div
              key={item.provenance}
              className="flex items-center gap-3 rounded-xl bg-surface-container-low p-4"
            >
              <ProvenanceBadge provenance={item.provenance} />
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                {item.text}
              </span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="flex flex-col gap-5">
        <CardHeader
          icon="rule"
          title="Open points"
          subtitle="Not yet supported. Preserved as TBD per OVERVIEW.md §10."
        />
        <ul className="flex flex-col gap-3">
          {OPEN_POINTS.map((point) => (
            <li
              key={point}
              className="flex items-center gap-3 font-body-md text-body-md text-on-surface-variant"
            >
              <Icon
                name="radio_button_unchecked"
                className="text-[18px]"
              />
              {point}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
