"use client";

import { useState } from "react";
import { LogoWordmark, MaskedAvatar } from "@/components/brand/Logo";
import { Icon } from "@/components/ui/Icon";
import { Toggle } from "@/components/ui/Toggle";
import { NavList } from "./NavList";
import { PROFILE } from "@/lib/data/profile";

export function Sidebar() {
  const [demoMode, setDemoMode] = useState(true);
  const [maskValues, setMaskValues] = useState(false);

  return (
    <aside className="fixed left-0 top-0 z-50 hidden h-full w-72 flex-col justify-between border-r border-surface-container-high bg-surface-container-lowest lg:flex">
      <div className="flex flex-col">
        <div className="p-space-lg">
          <LogoWordmark />
        </div>

        <div className="px-space-md py-space-xs">
          <div className="flex items-center justify-between rounded-xl bg-surface-container-low p-space-sm">
            <div className="flex items-center gap-space-xs">
              <Icon name="labs" className="text-secondary text-body-sm" />
              <div className="flex flex-col">
                <span className="font-label-caps text-label-caps uppercase text-on-surface">
                  Example Data Mode
                </span>
                <span className="font-label-code text-label-code text-on-surface-variant">
                  Synthetic Portfolio
                </span>
              </div>
            </div>
            <Toggle
              checked={demoMode}
              onChange={setDemoMode}
              label="Toggle example data mode"
            />
          </div>
        </div>

        <div className="px-space-md pt-space-md">
          <span className="mb-space-xs block px-space-sm font-label-caps text-label-caps uppercase tracking-wider text-on-surface-variant">
            Navigation
          </span>
          <NavList variant="sidebar" />
        </div>
      </div>

      <div className="m-space-md flex flex-col gap-space-sm rounded-xl bg-surface-container-low/60 p-space-md">
        <div className="flex items-center gap-space-sm overflow-hidden">
          <MaskedAvatar name={PROFILE.name} size={36} />
          <div className="flex min-w-0 flex-col">
            <span className="truncate font-title-md text-title-md text-on-surface">
              {PROFILE.name}
            </span>
            <span className="font-label-code text-label-code text-on-surface-variant">
              {PROFILE.tierLabel}
            </span>
          </div>
        </div>
        <div className="flex items-center justify-between pt-space-xs">
          <span className="inline-flex items-center gap-space-xs text-on-surface-variant">
            <Icon name="visibility_off" className="text-body-sm" />
            <span className="font-label-code text-label-code">Mask Values</span>
          </span>
          <Toggle
            checked={maskValues}
            onChange={setMaskValues}
            label="Toggle masking financial values"
          />
        </div>
      </div>
    </aside>
  );
}
