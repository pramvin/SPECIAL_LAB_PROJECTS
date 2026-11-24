import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Card, CardHeader } from "@/components/ui/Card";
import { NoticeBanner } from "@/components/ui/NoticeBanner";
import { PriceChart } from "@/components/stock/PriceChart";
import { StockDetail } from "@/components/stock/StockDetail";
import { StockHeader } from "@/components/stock/StockHeader";
import { getPrices, type Horizon } from "@/lib/recommendations";

function BackLink() {
  return (
    <Link
      href="/"
      className="inline-flex w-fit items-center gap-1 font-body-sm text-body-sm font-medium text-on-surface-variant hover:text-on-surface"
    >
      <Icon name="arrow_back" className="text-[16px]" />
      All ideas
    </Link>
  );
}

export default async function StockPage({
  params,
  searchParams,
}: {
  params: Promise<{ ticker: string }>;
  searchParams: Promise<{ h?: string }>;
}) {
  const { ticker: raw } = await params;
  const { h } = await searchParams;
  const ticker = raw.trim().toUpperCase();
  const horizon: Horizon = h === "1m" || h === "3m" ? h : "1w";
  const prices = ticker ? await getPrices(ticker, 60) : null;

  if (!prices) {
    return (
      <div className="flex flex-col gap-5">
        <BackLink />
        <Card as="section">
          <CardHeader title="Could not load this stock" icon="error" />
          <p className="mt-4 font-body-md text-body-md text-on-surface">
            We could not load prices for {ticker || "this ticker"}. It may not
            be in our list, or the backend is offline.
          </p>
        </Card>
      </div>
    );
  }

  const lastBar = prices.bars[prices.bars.length - 1];

  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <StockHeader
        ticker={prices.ticker}
        name={prices.name}
        price={prices.price}
        change={prices.change}
        changePct={prices.change_pct}
        asOf={lastBar?.date ?? null}
        horizon={horizon}
      />
      <PriceChart ticker={prices.ticker} bars={prices.bars} />
      <StockDetail
        key={`${prices.ticker}-${horizon}`}
        ticker={prices.ticker}
        horizon={horizon}
      />
      <NoticeBanner icon="info" tone="neutral" title="Not investment advice">
        The news, social and chart reads are written by a model from public
        data and have not been backtested. Labels can be wrong.
      </NoticeBanner>
    </div>
  );
}
