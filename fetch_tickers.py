# -*- coding: utf-8 -*-
"""
銘柄リスト整備スクリプト
  - S&P 500    : English Wikipedia から取得
  - 日経225    : 日本語 Wikipedia の業種別テーブルを連結して取得
結果を SQLite (stocks.db) の tickers テーブルと、確認用 CSV に保存する。

tickers スキーマ:
  ticker   TEXT  yfinanceで使うシンボル (例: 7203.T / AAPL)
  name     TEXT  銘柄名
  sector   TEXT  セクター/業種
  market   TEXT  'JP' or 'US'
  index_   TEXT  'Nikkei225' or 'S&P500'
"""
import io
import re
import sqlite3
from pathlib import Path

import requests
import pandas as pd

HERE = Path(__file__).parent
DB_PATH = HERE / "stocks.db"
HEADERS = {"User-Agent": "Mozilla/5.0 (screener research)"}

# 主要インデックス投信（連動ETFで概算）。market=FUND として一覧に混ぜる。
# ポートフォリオの lib.common.FUND_ALIAS と連動先を揃える。
FUNDS = [
    {"ticker": "VOO",  "name": "S&P500（VOO）",          "sector": "インデックス投信", "market": "FUND", "index_": "投信"},
    {"ticker": "VTI",  "name": "全米株式（楽天VTI≈VTI）", "sector": "インデックス投信", "market": "FUND", "index_": "投信"},
    {"ticker": "ACWI", "name": "全世界株式（オルカン≈ACWI）", "sector": "インデックス投信", "market": "FUND", "index_": "投信"},
    {"ticker": "QQQ",  "name": "NASDAQ100（QQQ）",       "sector": "インデックス投信", "market": "FUND", "index_": "投信"},
]


def fetch_funds() -> pd.DataFrame:
    return pd.DataFrame(FUNDS)


def get_html(url: str) -> str:
    return requests.get(url, headers=HEADERS, timeout=30).text


def fetch_sp500() -> pd.DataFrame:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(io.StringIO(get_html(url)))
    t = tables[0]
    df = pd.DataFrame({
        # yfinanceは "." ではなく "-" 表記 (BRK.B -> BRK-B)
        "ticker": t["Symbol"].astype(str).str.replace(".", "-", regex=False).str.strip(),
        "name": t["Security"].astype(str).str.strip(),
        "sector": t["GICS Sector"].astype(str).str.strip(),
    })
    df["market"] = "US"
    df["index_"] = "S&P500"
    return df


def fetch_nikkei225() -> pd.DataFrame:
    url = "https://ja.wikipedia.org/wiki/日経平均株価"
    tables = pd.read_html(io.StringIO(get_html(url)))
    parts = []
    for t in tables:
        cols = [str(c) for c in t.columns]
        if "証券コード" in cols and "銘柄" in cols:
            parts.append(t[["証券コード", "銘柄"]].copy())
    if not parts:
        raise RuntimeError("日経225の構成銘柄テーブルが見つかりませんでした")
    raw = pd.concat(parts, ignore_index=True)
    # 証券コードが4桁数字の行だけ残す
    raw["証券コード"] = raw["証券コード"].astype(str).str.extract(r"(\d{4})")[0]
    raw = raw.dropna(subset=["証券コード"]).drop_duplicates(subset=["証券コード"])
    df = pd.DataFrame({
        "ticker": raw["証券コード"] + ".T",
        "name": raw["銘柄"].astype(str).str.strip(),
        "sector": None,  # JAページの業種見出しは表外なので後段で補完予定
    })
    df["market"] = "JP"
    df["index_"] = "Nikkei225"
    return df


def main():
    print("S&P500 取得中 ...")
    sp = fetch_sp500()
    print(f"  -> {len(sp)} 銘柄")

    print("日経225 取得中 ...")
    nk = fetch_nikkei225()
    print(f"  -> {len(nk)} 銘柄")

    funds = fetch_funds()
    print(f"投信(連動ETF): {len(funds)} 本")

    all_df = pd.concat([nk, sp, funds], ignore_index=True)

    # SQLiteへ保存
    con = sqlite3.connect(DB_PATH)
    all_df.to_sql("tickers", con, if_exists="replace", index=False)
    con.close()

    # 確認用CSV
    csv_path = HERE / "tickers.csv"
    all_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(f"\n保存完了: {DB_PATH.name} (tickers) / {csv_path.name}")
    print(f"合計 {len(all_df)} 銘柄  (日経225={len(nk)}, S&P500={len(sp)}, 投信={len(funds)})")
    print("\n--- 日経225 先頭5件 ---")
    print(nk.head().to_string(index=False))
    print("\n--- S&P500 先頭5件 ---")
    print(sp.head().to_string(index=False))


if __name__ == "__main__":
    main()
