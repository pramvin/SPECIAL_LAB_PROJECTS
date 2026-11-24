/** Plain-words fallback for a block the backend could not fill. */
export function BlockUnavailable({
  status,
  reason,
}: {
  status: "unavailable" | "skipped";
  reason: string | null;
}) {
  return (
    <div className="rounded-[16px] bg-surface-container-low px-4 py-3 font-body-sm text-body-sm text-on-surface-variant">
      <span className="font-medium text-on-surface">
        {status === "skipped" ? "Skipped." : "Not available right now."}
      </span>{" "}
      {reason ?? "The backend did not give a reason."}
    </div>
  );
}
