import { Button } from "@/components/ui/Button";
import { Card, SectionLabel } from "@/components/ui/Card";
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
    <div className="flex flex-col items-end gap-2">
      <span className="font-body-sm text-body-sm text-on-surface-variant">
        You · 10:42 AM
      </span>
      <p className="max-w-[85%] rounded-[24px] rounded-br-md bg-primary-container px-5 py-4 font-body-md text-body-md text-on-primary">
        {USER_QUESTION}
      </p>
    </div>
  );
}

function AssistantAnswer() {
  return (
    <Card className="flex flex-col gap-8 !p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-t-[24px] bg-primary-fixed px-6 py-4 md:px-8">
        <span className="inline-flex items-center gap-2 font-body-sm text-body-sm font-medium text-on-primary-fixed">
          <Icon name="auto_awesome" className="text-[16px]" />
          Generated guidance · verification needed
        </span>
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          {VERIFICATION_NOTE}
        </span>
      </div>

      <div className="flex flex-col gap-8 px-6 pb-8 md:px-8">
        <div className="flex flex-col gap-3">
          <h2 className="font-headline-sm text-headline-sm text-on-surface">
            {ANSWER.headline}
          </h2>
          <p className="max-w-2xl font-body-md text-body-md text-on-surface-variant">
            {ANSWER.body}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          {ANSWER.stats.map((stat) => (
            <div
              key={stat.label}
              className="flex flex-col gap-1 rounded-xl bg-surface-container-low p-4"
            >
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                {stat.label}
              </span>
              <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
                {stat.value}
              </span>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                {stat.sub}
              </span>
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-5 rounded-[20px] border border-surface-container-high p-5 md:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="inline-flex items-center gap-2 font-title-md text-title-md text-on-surface">
              <Icon name="schema" className="text-[18px]" />
              Assumptions &amp; data sources
            </span>
            <ProvenanceBadge
              provenance="ai"
              label={ASSISTANT_HEADER.provenanceNote}
            />
          </div>
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-4">
            {ASSUMPTIONS.map((a) => (
              <div key={a.label} className="flex flex-col gap-1.5">
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  {a.label}
                </span>
                <span className="font-title-md text-title-md tabular-nums text-on-surface">
                  {a.value}
                </span>
                <ProvenanceBadge provenance={a.provenance} />
              </div>
            ))}
          </div>
          <div className="flex items-start gap-3 rounded-xl bg-provenance-warning-bg p-4 font-body-sm text-body-sm text-provenance-warning-text">
            <Icon name="warning" className="mt-0.5 text-[18px]" />
            <span>{ANSWER.caveat}</span>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <SectionLabel>Rationale &amp; recommended next steps</SectionLabel>
          {RATIONALE.map((step) => (
            <div key={step.title} className="flex items-start gap-3">
              <Icon
                name="check_circle"
                className="mt-0.5 text-[18px] text-tertiary-accent"
              />
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                <strong className="text-on-surface">{step.title}:</strong>{" "}
                {step.body}
              </p>
            </div>
          ))}
          <div className="flex items-start gap-3">
            <Icon
              name="arrow_forward"
              className="mt-0.5 text-[18px] text-tertiary-accent"
            />
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              <strong className="text-on-surface">Actionable step:</strong>{" "}
              {ACTION_STEP}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 border-t border-surface-container-high pt-6">
          <Button icon="play_arrow">Apply to simulation</Button>
          <Button variant="secondary" icon="science">
            Challenge assumption
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function AssistantView() {
  return (
    <div className="flex flex-col gap-12 lg:gap-16">
      <header className="flex flex-col gap-4">
        <SectionLabel>Plan &amp; Assistant</SectionLabel>
        <h1 className="max-w-3xl font-headline-lg text-headline-lg-mobile tracking-tight text-on-surface sm:text-headline-lg">
          Ask about your plan
        </h1>
        <p className="max-w-2xl font-body-lg text-body-lg text-on-surface-variant">
          Explore trade-offs, test assumptions, and see how changes affect your
          goals. Guidance is generated and not validated.
        </p>
        <div className="flex flex-wrap items-center gap-3 font-body-sm text-body-sm text-on-surface-variant">
          <span className="inline-flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-tertiary-accent" />
            {ASSISTANT_HEADER.scenario}
          </span>
          <span className="hidden h-4 w-px bg-surface-container-high sm:block" />
          <span>{ASSISTANT_HEADER.disclaimer} (OP-008)</span>
        </div>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-2">
          {SUGGESTED_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="rounded-full border border-surface-container-high bg-surface-container-lowest px-4 py-2 font-body-sm text-body-sm text-on-surface-variant transition-colors hover:border-tertiary-accent hover:text-tertiary-accent"
            >
              {prompt}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
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

      <div className="grid grid-cols-1 gap-10 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex flex-col gap-10">
          <div className="flex flex-col gap-8">
            <UserBubble />
            <AssistantAnswer />
          </div>

          <div className="flex items-center gap-3 rounded-full bg-surface-container-low px-5 py-3">
            <Icon name="autorenew" className="animate-spin text-tertiary-accent" />
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Agent synthesizing financial impact with conservative safety
              margins…
            </span>
          </div>

          <ChatComposer />
        </div>

        <div className="flex flex-col gap-6 xl:sticky xl:top-24 xl:self-start">
          <ModelInputsPanel />
          <GoalTargetPanel />
        </div>
      </div>
    </div>
  );
}
