"""Placeholder trade ideas. EXAMPLE DATA ONLY: prices, scores and news are
synthetic until the real pipeline (collect -> rank -> risk) writes this table."""

# (ticker, name, sector, horizon, entry, stop, target, score, reasons, news)
_N = "Example news (synthetic)"
SEED = [
    ("NVDA", "NVIDIA", "tech", "1w", 120.00, 115.50, 128.00, 78,
     ["Momentum: price above its 20-day average", "Volume running above its 30-day average", "Earnings catalyst within the week"],
     ["Analyst raises data-center demand outlook", "Supplier reports strong chip orders"]),
    ("XOM", "Exxon Mobil", "energy", "1w", 110.00, 106.60, 116.00, 71,
     ["Crude price trend turning up", "Holding above its 50-day average", "Low volatility versus peers"],
     ["Oil inventories draw down more than expected"]),
    ("JPM", "JPMorgan Chase", "finance", "1w", 200.00, 193.50, 211.00, 68,
     ["Breakout above recent range", "Sector strength in large banks", "Earnings beat history"],
     ["Bank earnings season opens with solid results"]),
    ("JNJ", "Johnson & Johnson", "healthcare", "1w", 155.00, 150.50, 162.00, 64,
     ["Defensive name, steady trend", "Pullback to support held", "Dividend date approaching"],
     ["Pipeline update expected this week"]),
    ("MSFT", "Microsoft", "tech", "1m", 420.00, 395.00, 460.00, 80,
     ["Strong revenue and EPS growth", "Uptrend above 50- and 200-day averages", "Healthy cash flow and margins"],
     ["Cloud segment growth beats estimates", "New enterprise AI contract announced"]),
    ("UNH", "UnitedHealth", "healthcare", "1m", 520.00, 488.00, 575.00, 74,
     ["Earnings surprise last quarter", "Relative strength versus sector", "Stable guidance"],
     ["Company reaffirms full-year guidance"]),
    ("COST", "Costco", "consumer", "1m", 880.00, 830.00, 960.00, 72,
     ["Consistent same-store sales growth", "Trend intact, shallow pullbacks", "Strong ROE"],
     ["Monthly sales report shows steady growth"]),
    ("CVX", "Chevron", "energy", "1m", 150.00, 141.00, 165.00, 66,
     ["Cash flow supports buybacks", "Price recovering from support", "Attractive P/E versus sector"],
     ["Company announces production expansion"]),
    ("AAPL", "Apple", "tech", "3m", 190.00, 170.00, 225.00, 77,
     ["Services revenue growth", "Long-term uptrend", "Product cycle catalyst ahead"],
     ["Supply-chain reports point to strong launch demand"]),
    ("V", "Visa", "finance", "3m", 275.00, 248.00, 320.00, 75,
     ["High margins and steady EPS growth", "Low earnings volatility", "Trend above 200-day average"],
     ["Payment volume growth accelerates"]),
    ("LLY", "Eli Lilly", "healthcare", "3m", 780.00, 700.00, 900.00, 73,
     ["Revenue growth well above sector", "Strong earnings momentum", "Pipeline catalysts expected"],
     ["Trial results expected next quarter"]),
    ("PG", "Procter & Gamble", "consumer", "3m", 165.00, 150.00, 185.00, 65,
     ["Defensive with steady cash flow", "Slow, stable uptrend", "Dividend growth record"],
     ["Pricing actions support margins"]),
]
NEWS_SOURCE = _N
