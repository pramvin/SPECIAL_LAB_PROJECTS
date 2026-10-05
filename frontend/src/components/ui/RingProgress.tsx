export function RingProgress({
  value,
  size = 56,
  stroke = 6,
  tone = "primary",
  showLabel = true,
}: {
  value: number; // 0..100
  size?: number;
  stroke?: number;
  tone?: "primary" | "secondary";
  showLabel?: boolean;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const color = tone === "secondary" ? "#485f84" : "#1b4332";
  return (
    <span
      className="relative inline-flex shrink-0 items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${Math.round(clamped)} percent`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#dae2fd"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      {showLabel && (
        <span className="absolute font-title-md text-title-md font-semibold text-on-surface">
          {Math.round(clamped)}%
        </span>
      )}
    </span>
  );
}
