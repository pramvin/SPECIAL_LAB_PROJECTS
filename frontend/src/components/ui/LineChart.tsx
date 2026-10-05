"use client";

export interface Series {
  points: number[];
  color: string;
  dashed?: boolean;
  area?: boolean;
}

/**
 * Dependency-free SVG line chart (OVERVIEW.md §9.9: avoid heavy deps).
 * Values are normalized across all series plus the optional target line so
 * relative positions stay truthful within the illustration.
 */
export function LineChart({
  series,
  target,
  height = 120,
  className = "",
  ariaLabel = "Line chart",
}: {
  series: Series[];
  target?: number;
  height?: number;
  className?: string;
  ariaLabel?: string;
}) {
  const width = 600;
  const pad = 10;
  const allPoints = series.flatMap((s) => s.points);
  if (target !== undefined) allPoints.push(target);
  if (allPoints.length === 0) {
    return <div className={className} style={{ height }} />;
  }

  const min = Math.min(...allPoints);
  const max = Math.max(...allPoints);
  const range = max - min || 1;

  const toXY = (value: number, index: number, count: number) => {
    const x =
      count <= 1 ? width / 2 : pad + (index / (count - 1)) * (width - pad * 2);
    const y = height - pad - ((value - min) / range) * (height - pad * 2);
    return [x, y] as const;
  };

  const buildPath = (points: number[]) =>
    points
      .map((value, index) => {
        const [x, y] = toXY(value, index, points.length);
        return `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(" ");

  const targetY =
    target !== undefined
      ? height - pad - ((target - min) / range) * (height - pad * 2)
      : 0;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className={`w-full ${className}`}
      style={{ height }}
      role="img"
      aria-label={ariaLabel}
    >
      {target !== undefined && (
        <line
          x1={pad}
          x2={width - pad}
          y1={targetY}
          y2={targetY}
          stroke="#c1c8c2"
          strokeWidth="1.5"
          strokeDasharray="6 6"
        />
      )}
      {series.map((s, i) => {
        const path = buildPath(s.points);
        const areaPath = `${path} L${width - pad} ${height} L${pad} ${height} Z`;
        return (
          <g key={i}>
            {s.area && <path d={areaPath} fill={s.color} opacity="0.08" />}
            <path
              d={path}
              fill="none"
              stroke={s.color}
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray={s.dashed ? "6 6" : undefined}
            />
            {s.points.length > 0 && !s.dashed && (
              <circle
                cx={toXY(s.points[s.points.length - 1], s.points.length - 1, s.points.length)[0]}
                cy={toXY(s.points[s.points.length - 1], s.points.length - 1, s.points.length)[1]}
                r="4"
                fill={s.color}
              />
            )}
          </g>
        );
      })}
    </svg>
  );
}
