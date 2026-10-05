import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { ModelInputsPanel } from "./ModelInputsPanel";
import { GoalTargetPanel } from "./GoalTargetPanel";
import { ChatComposer } from "./ChatComposer";
import {
  ACTION_STEP,
  ANSWER,
  ASSISTANT_HEADER,
  ASSUMPTIONS,
  RATIONALE,
  SUGGESTED_PROMPTS,
  USER_QUESTION,
  VERIFICATION_NOTE,
} from "@/lib/data/assistant";

function UserBubble() {
  return (
    <div className="flex flex-col items-end gap-1">
      <span className="font-label-code text-label-code uppercase tracking-wider text-on-surface-variant">
        You • Financial Planner Client · 10:42 AM
      </span>
      <p className="max-w-[85%] rounded-xl rounded-tr-sm bg-primary-container p-space-md font-body-lg text-body-lg text-on-primary">
        {USER_QUESTION}
      </p>
    </div>
  );
}

function AssistantAnswer() {
  return (
    <Card className="flex flex-col gap-space-md p-0">
      <div className="flex flex-wrap items-center justify-between gap-space-sm rounded-t-lg bg-provenance-input-bg px-space-md py-space-sm">
        <span className="inline-flex items-center gap-space-xs font-label-code text-label-code uppercase tracking-wide text-provenance-input-text">
          <Icon name="auto_awesome" className="text-[16px]" />
          Generated Guidance • Verification Needed
        </span>
        <span className="font-label-code text-label-code text-on-surface-variant">
          {VERIFICATION_NOTE}
        </span>
      </div>

      <div className="flex flex-col gap-space-md px-space-lg pb-space-lg">
        <div className="flex items-center gap-space-xs text-on-surface-variant">
          <Icon name="thumb_up" className="text-[16px]" />
          <Icon name="thumb_down" className="text-[16px]" />
        </div>

        <h2 className="font-headline-md text-headline-md text-on-surface">
          {ANSWER.headline}
        </h2>
        <p className="font-body-md text-body-md text-on-surface-variant">
          {ANSWER.body}
        </p>

        <div className="grid grid-cols-1 gap-space-md sm:grid-cols-3">
          {ANSWER.stats.map((stat) => (
            <div
              key={stat.label}
              className="flex flex-col gap-1 rounded-md bg-surface-container-low p-space-sm"
            >
              <span className="font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
                {stat.label}
              </span>
              <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
                {stat.value}
              </span>
              <span className="font-label-code text-label-code text-on-surface-variant">
                {stat.sub}
              </span>
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-space-sm rounded-md border border-surface-container-high p-space-md">
          <div className="flex flex-wrap items-center justify-between gap-space-sm">
            <span className="inline-flex items-center gap-space-xs font-title-md text-title-md text-on-surface">
              <Icon name="schema" className="text-[18px]" />
              Assumptions &amp; Data Sources
            </span>
            <ProvenanceBadge
              provenance="ai"
              label={ASSISTANT_HEADER.provenanceNote}
            />
          </div>
          <div className="grid grid-cols-2 gap-space-md sm:grid-cols-4">
            {ASSUMPTIONS.map((a) => (
              <div key={a.label} className="flex flex-col gap-1">
                <span className="font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
                  {a.label}
                </span>
                <span className="font-title-md text-title-md tabular-nums text-on-surface">
                  {a.value}
                </span>
                <ProvenanceBadge provenance={a.provenance} />
              </div>
            ))}
          </div>
          <div className="flex items-start gap-space-sm rounded-md bg-provenance-warning-bg p-space-sm font-body-sm text-body-sm text-provenance-warning-text">
            <Icon name="warning" className="mt-0.5 text-[18px]" />
            <span>{ANSWER.caveat}</span>
          </div>
        </div>

        <div className="flex flex-col gap-space-sm">
          <span className="font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
            Rationale &amp; Recommended Next Steps
          </span>
          {RATIONALE.map((step) => (
            <div key={step.title} className="flex items-start gap-space-sm">
              <Icon
                name="check_circle"
                className="mt-0.5 text-[18px] text-primary"
              />
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                <strong className="text-on-surface">{step.title}:</strong>{" "}
                {step.body}
              </p>
            </div>
          ))}
          <div className="flex items-start gap-space-sm">
            <Icon
              name="arrow_forward"
              className="mt-0.5 text-[18px] text-secondary"
            />
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              <strong className="text-on-surface">Actionable Step:</strong>{" "}
              {ACTION_STEP}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-space-sm">
          <Button icon="play_arrow">Apply to Simulation</Button>
          <Button variant="secondary" icon="science">
            Challenge Assumption
          </Button>
        </div>
        <div className="flex items-center gap-space-sm font-label-code text-label-code text-on-surface-variant">
          <span>Was this response helpful?</span>
          <Icon name="thumb_up" className="text-[16px]" />
          <Icon name="thumb_down" className="text-[16px]" />
        </div>
      </div>
    </Card>
  );
}

export function AssistantView() {
  return (
    <>
      <div className="flex flex-wrap items-center gap-space-sm rounded-lg bg-surface-container-low p-space-md">
        <Icon name="info" className="text-secondary" />
        <span className="font-body-sm text-body-sm text-on-surface">
          <strong>{ASSISTANT_HEADER.title}</strong> —{" "}
          {ASSISTANT_HEADER.disclaimer} (OP-008).
        </span>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-space-sm">
        <span className="inline-flex items-center gap-space-xs font-body-sm text-body-sm text-on-surface">
          <span className="h-2 w-2 rounded-full bg-primary-container" />
          {ASSISTANT_HEADER.scenario}
        </span>
        <div className="flex flex-wrap items-center gap-space-sm">
          <Button variant="secondary" size="sm" icon="add">
            New
          </Button>
          <Button variant="ghost" size="sm" icon="ios_share">
            Export
          </Button>
          <Button variant="ghost" size="sm" icon="delete">
            Clear
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-space-lg xl:grid-cols-[2fr_1fr]">
        <div className="flex flex-col gap-space-lg">
          <div className="flex flex-col gap-space-sm">
            <div className="flex flex-wrap items-center justify-between gap-space-sm">
              <span className="font-label-code text-label-code uppercase tracking-wider text-on-surface-variant">
                Recommended Analytical Inquiries
              </span>
              <span className="inline-flex items-center gap-1 font-label-code text-label-code text-secondary">
                <Icon name="auto_awesome" className="text-[14px]" />
                Auto-Tailored to Goals
              </span>
            </div>
            <div className="flex flex-wrap gap-space-sm">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="rounded-full border border-surface-container-high bg-surface-container-lowest px-space-md py-1.5 font-body-sm text-body-sm text-on-surface-variant hover:bg-surface-container-low"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-space-lg">
            <UserBubble />
            <AssistantAnswer />
          </div>

          <div className="flex items-center gap-space-sm rounded-lg bg-surface-container-low px-space-md py-space-sm">
            <Icon
              name="autorenew"
              className="animate-spin text-secondary"
            />
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Agent synthesizing financial impact with conservative safety
              margins…
            </span>
          </div>

          <ChatComposer />
        </div>

        <div className="flex flex-col gap-space-lg xl:sticky xl:top-20 xl:self-start">
          <ModelInputsPanel />
          <GoalTargetPanel />
        </div>
      </div>
    </>
  );
}
