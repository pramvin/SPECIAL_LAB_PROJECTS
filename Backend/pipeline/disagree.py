"""Where does Laya's per-headline sentiment disagree with the LLM's call? (read-only report, changes nothing)

For each ticker's newest successful `llm_analysis` row, count Laya's bullish / bearish headlines among the
headlines the LLM was given. Flag "up" with no more bullish than bearish headlines, and "down" the other way.
A flag means "look again", not "the LLM is wrong": Laya's labels are not validated on our headlines yet.

Run from Backend/:  .venv/bin/python -m pipeline.disagree
"""
import json
import os
import sqlite3

HERE = os.path.dirname(__file__)
DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(HERE, "..", "planwise.db"))


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT ticker, input_news_ids, output_json FROM llm_analysis WHERE output_json IS NOT NULL "
        "AND id IN (SELECT MAX(id) FROM llm_analysis WHERE output_json IS NOT NULL GROUP BY ticker) ORDER BY ticker").fetchall()
    flagged = []
    for ticker, ids_json, out_json in rows:
        ids, d = json.loads(ids_json), json.loads(out_json)["direction"]
        s = dict(conn.execute(
            f"SELECT sentiment, COUNT(*) FROM news_scores WHERE news_id IN ({','.join('?' * len(ids))}) GROUP BY sentiment", ids).fetchall())
        bull, bear = s.get("bullish", 0), s.get("bearish", 0)
        if (d == "up" and bull <= bear) or (d == "down" and bear <= bull):
            flagged.append(ticker)
            print(f"{ticker}: LLM {d} | Laya bullish {bull} bearish {bear} neutral {s.get('neutral', 0)} of {len(ids)}")
    print(f"{len(flagged)} of {len(rows)} tickers flagged")


if __name__ == "__main__":
    main()
