/**
 * Thin wrapper around the Material Symbols Outlined icon font.
 * The font is loaded in the root layout; sizing is inherited from
 * the surrounding text utilities.
 */
export function Icon({
  name,
  className = "",
  filled = false,
  "aria-hidden": ariaHidden = true,
}: {
  name: string;
  className?: string;
  filled?: boolean;
  "aria-hidden"?: boolean;
}) {
  return (
    <span
      aria-hidden={ariaHidden}
      className={`material-symbols-outlined select-none not-italic ${className}`}
      style={filled ? { fontVariationSettings: "'FILL' 1" } : undefined}
    >
      {name}
    </span>
  );
}
