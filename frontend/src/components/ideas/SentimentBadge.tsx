import { Badge } from "@/components/ui/Badge";
import type { Sentiment } from "@/lib/recommendations";

const MAP: Record<
  Sentiment,
  { label: string; tone: "success" | "danger" | "neutral"; icon: string }
> = {
  positive: { label: "Positive", tone: "success", icon: "trending_up" },
  neutral: { label: "Neutral", tone: "neutral", icon: "remove" },
  negative: { label: "Negative", tone: "danger", icon: "trending_down" },
};

const TITLE =
  "Label from the local sentiment model. It is a guess and can be wrong.";

/** Sentiment pill for one headline. Renders nothing when the headline was not scored. */
export function SentimentBadge({
  sentiment,
}: {
  sentiment?: Sentiment | null;
}) {
  if (!sentiment || !(sentiment in MAP)) return null;
  const m = MAP[sentiment];
  return (
    <span title={TITLE}>
      <Badge tone={m.tone} icon={m.icon}>
        {m.label}
      </Badge>
    </span>
  );
}
