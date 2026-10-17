import { Badge } from "@/components/ui/Badge";

const MAP = {
  bullish: { label: "Bullish", tone: "success", icon: "trending_up" },
  bearish: { label: "Bearish", tone: "danger", icon: "trending_down" },
  neutral: { label: "Neutral", tone: "neutral", icon: "remove" },
} as const;

/** AI-labeled headline sentiment. Not yet validated on our own headlines, so it is display-only. */
export function SentimentBadge({ sentiment }: { sentiment?: string | null }) {
  if (!sentiment || !(sentiment in MAP)) return null;
  const m = MAP[sentiment as keyof typeof MAP];
  return (
    <span title="Labeled by the Laya model. Accuracy on our headlines is not validated yet.">
      <Badge tone={m.tone} icon={m.icon}>
        AI · {m.label}
      </Badge>
    </span>
  );
}
