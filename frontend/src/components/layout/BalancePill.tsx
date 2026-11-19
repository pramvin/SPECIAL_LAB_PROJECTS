import Link from "next/link";
import { getPortfolio } from "@/lib/wallet";

const usd = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

/** Paper balance, P/L since start and open-position count; links to the wallet page. */
export async function BalancePill() {
  const portfolio = await getPortfolio();
  if (!portfolio) return null;
  const { balance, changePct, positions } = portfolio;
  const up = changePct >= 0;
  return (
    <Link
      href="/wallet"
      className="hidden shrink-0 items-center gap-2 whitespace-nowrap rounded-full bg-surface-container-low px-3 py-1 font-body-sm text-body-sm text-on-surface-variant md:inline-flex"
    >
      <b className="font-semibold tabular-nums text-on-surface">{usd(balance)}</b>
      <span
        className={`rounded-full px-2 py-0.5 text-[12px] font-semibold tabular-nums ${
          up ? "bg-green-50 text-green-700" : "bg-red-50 text-error"
        }`}
      >
        {up ? "+" : ""}
        {changePct.toFixed(1)}%
      </span>
      <span className="hidden tabular-nums xl:inline">{positions.length} open</span>
    </Link>
  );
}
