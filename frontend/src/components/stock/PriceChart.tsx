import { Card, CardHeader } from "@/components/ui/Card";
import type { PriceBar } from "@/lib/recommendations";

const W = 800;
const H = 260;
const PAD = { top: 18, right: 18, bottom: 30, left: 58 };

const money = (n: number) => `$${n.toFixed(2)}`;

function shortDate(iso: string) {
  const date = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

/** Daily closes for one ticker, drawn by hand as plain SVG (no chart library). */
export function PriceChart({
  ticker,
  bars,
}: {
  ticker: string;
  bars: PriceBar[];
}) {
  if (bars.length < 2) {
    return (
      <Card>
        <CardHeader title="Price" icon="show_chart" />
        <p className="mt-6 font-body-md text-body-md text-on-surface-variant">
          Not enough price history to draw a chart yet.
        </p>
      </Card>
    );
  }

  const closes = bars.map((b) => b.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const x = (i: number) => PAD.left + (i / (bars.length - 1)) * innerW;
  const y = (v: number) => PAD.top + (1 - (v - min) / range) * innerH;

  const line = closes
    .map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`)
    .join(" ");
  const area = `${line} L${x(closes.length - 1).toFixed(1)} ${H - PAD.bottom} L${PAD.left} ${H - PAD.bottom} Z`;

  const up = closes[closes.length - 1] >= closes[0];
  const color = up ? "#166534" : "#d70015";
  const fillId = `price-fill-${ticker.replace(/[^A-Za-z0-9-]/g, "")}`;
  const levels = [
    { value: max, label: money(max) },
    { value: (max + min) / 2, label: money((max + min) / 2) },
    { value: min, label: money(min) },
  ];
  const ticks = [0, Math.floor((bars.length - 1) / 2), bars.length - 1];

  return (
    <Card>
      <CardHeader
        title="Price"
        icon="show_chart"
        subtitle={`Last ${bars.length} daily closes, ${shortDate(bars[0].date)} to ${shortDate(bars[bars.length - 1].date)}.`}
      />
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="mt-5 h-auto w-full"
        role="img"
        aria-label={`${ticker} daily close from ${money(closes[0])} on ${bars[0].date} to ${money(closes[closes.length - 1])} on ${bars[bars.length - 1].date}`}
      >
        <defs>
          <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.18" />
            <stop offset="100%" stopColor={color} stopOpacity="0.01" />
          </linearGradient>
        </defs>

        {levels.map((level, i) => (
          <g key={i}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={y(level.value)}
              y2={y(level.value)}
              stroke="#e8e8ed"
              strokeWidth="1"
            />
            <text
              x={PAD.left - 10}
              y={y(level.value) + 4}
              textAnchor="end"
              fontSize="12"
              fill="#6e6e73"
            >
              {level.label}
            </text>
          </g>
        ))}

        <path d={area} fill={`url(#${fillId})`} />
        <path
          d={line}
          fill="none"
          stroke={color}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle
          cx={x(closes.length - 1)}
          cy={y(closes[closes.length - 1])}
          r="4"
          fill={color}
        />

        {ticks.map((i) => (
          <text
            key={i}
            x={x(i)}
            y={H - 8}
            textAnchor={i === 0 ? "start" : i === bars.length - 1 ? "end" : "middle"}
            fontSize="12"
            fill="#6e6e73"
          >
            {shortDate(bars[i].date)}
          </text>
        ))}
      </svg>
    </Card>
  );
}
