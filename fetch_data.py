# -*- coding: utf-8 -*-
"""
本番データ取得スクリプト
  tickers.csv の全銘柄について yfinance から指標を取得し、data.parquet に保存する。
  - ThreadPool で並列取得（Yahoo のレート制限を避けるため控えめな並列度）
  - 失敗時リトライ
  - 日本株のセクターも yfinance の info["sector"] から補完

使い方:
  python fetch_data.py            # 全銘柄
  python fetch_data.py --limit 20 # 先頭20銘柄だけ（動作確認用）
  python fetch_data.py --workers 12
"""
from __future__ import annotations
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

HERE = Path(__file__).parent
TICKERS_CSV = HERE / "tickers.csv"
OUT_PARQUET = HERE / "data.parquet"

# yfinance info の生キー -> 保存カラム名
INFO_FIELDS = {
    "sector": "sector",                                  # JP補完用
    "currentPrice": "price",
    "currency": "currency",
    "marketCap": "market_cap",
    # --- バリュー ---
    "trailingPE": "per",
    "forwardPE": "forward_pe",
    "priceToBook": "pbr",
    "priceToSalesTrailing12Months": "psr",
    "dividendYield": "dividend_yield",                   # 単位は % (例 3.51)
    # --- クオリティ ---
    "returnOnEquity": "roe",                             # 小数 (0.10=10%)
    "returnOnAssets": "roa",
    "profitMargins": "profit_margin",
    "debtToEquity": "debt_to_equity",
    # --- グロース ---
    "revenueGrowth": "revenue_growth",
    "earningsGrowth": "earnings_growth",
    "earningsQuarterlyGrowth": "earnings_q_growth",
    # --- モメンタム ---
    "fiftyDayAverage": "ma50",
    "twoHundredDayAverage": "ma200",
    "fiftyTwoWeekHigh": "high_52w",
    "fiftyTwoWeekLow": "low_52w",
    "beta": "beta",
}


def fetch_one(row: dict, retries: int = 2) -> dict:
    ticker = row["ticker"]
    rec = {
        "ticker": ticker,
        "name": row["name"],
        "market": row["market"],
        "index_": row["index_"],
    }
    last_err = None
    for attempt in range(retries + 1):
        try:
            info = yf.Ticker(ticker).info
            for key, col in INFO_FIELDS.items():
                rec[col] = info.get(key)
            # CSV側にセクターがあればそれを優先（S&P500）、無ければinfo由来（JP）
            if row.get("sector") and str(row["sector"]).lower() != "nan":
                rec["sector"] = row["sector"]
            rec["ok"] = rec.get("price") is not None
            return rec
        except Exception as e:  # ネットワーク/レート制限など
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    rec["ok"] = False
    rec["error"] = str(last_err)
    return rec


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """移動平均乖離率・52週高値からの下落率など、便利な派生指標を追加"""
    def safe_ratio(a, b):
        return (df[a] / df[b] - 1) * 100

    df["pct_vs_ma50"] = safe_ratio("price", "ma50")
    df["pct_vs_ma200"] = safe_ratio("price", "ma200")
    df["pct_from_52w_high"] = safe_ratio("price", "high_52w")
    df["pct_from_52w_low"] = safe_ratio("price", "low_52w")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="先頭N銘柄だけ取得")
    ap.add_argument("--workers", type=int, default=10, help="並列数")
    args = ap.parse_args()

    tickers = pd.read_csv(TICKERS_CSV)
    if args.limit:
        tickers = tickers.head(args.limit)
    rows = tickers.to_dict("records")
    total = len(rows)
    print(f"取得対象: {total} 銘柄 / 並列 {args.workers}")

    results = []
    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(fetch_one, r): r["ticker"] for r in rows}
        for fut in as_completed(futures):
            results.append(fut.result())
            done += 1
            if done % 25 == 0 or done == total:
                elapsed = time.time() - t0
                print(f"  {done}/{total}  ({elapsed:.0f}s)")

    df = pd.DataFrame(results)
    df = add_derived(df)
    df["fetched_at"] = datetime.now(timezone.utc).isoformat()

    ok = int(df["ok"].sum())
    ng = total - ok
    print(f"\n取得成功 {ok} / 失敗 {ng}")
    if ng:
        bad = df.loc[~df["ok"], "ticker"].tolist()
        print("  失敗銘柄:", ", ".join(bad[:30]), ("..." if ng > 30 else ""))

    df.to_parquet(OUT_PARQUET, index=False)
    print(f"保存完了: {OUT_PARQUET.name}  ({len(df)} 行, {df.shape[1]} 列)")


if __name__ == "__main__":
    main()
