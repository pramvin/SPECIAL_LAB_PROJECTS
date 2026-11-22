import { Badge } from "@/components/ui/Badge";
import type { Rating } from "@/lib/recommendations";

const TONE: Record<Rating, "success" | "warning" | "danger" | "neutral"> = {
  Buy: "success",
  Overweight: "success",
  Hold: "warning",
  Underweight: "danger",
  Sell: "danger",
  REVIEW: "neutral",
};

/**
 * The AI's opinion of the idea. Never a rule figure: the label and the
 * tooltip make clear this is a model opinion, not a backtest.
 */
export function AiRatingBadge({
  rating,
  label,
}: {
  rating: Rating;
  label?: string;
}) {
  return (
    <span title="AI opinion · not backtested">
      <Badge tone={TONE[rating]} icon="auto_awesome">
        {label ?? `AI · ${rating}`}
      </Badge>
    </span>
  );
}

export function ratingTone(
  rating: Rating,
): "success" | "warning" | "danger" | "neutral" {
  return TONE[rating];
}
