# -*- coding: utf-8 -*-
"""data.parquet に投信(連動ETF)行が正しく入っているかの検証（pandasのみ・streamlit非依存）。"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data.parquet")
EXPECTED = {"VOO", "VTI", "ACWI", "QQQ"}


def main():
    df = pd.read_parquet(DATA)
    funds = df[df["market"] == "FUND"]

    # 4ファンドが揃っている
    assert set(funds["ticker"]) >= EXPECTED, set(funds["ticker"])

    # expense_ratio 列が存在
    assert "expense_ratio" in df.columns

    for _, r in funds.iterrows():
        tk = r["ticker"]
        # 価格が取れている（ETFは currentPrice=None なのでフォールバックが効いているか）
        assert pd.notna(r["price"]) and r["price"] > 0, f"{tk} price={r['price']}"
        # 純資産(market_cap)がある・USD建て
        assert pd.notna(r["market_cap"]) and r["market_cap"] > 0, f"{tk} cap"
        assert r["currency"] == "USD", f"{tk} currency={r['currency']}"
        # 経費率が取れている（% 表記なので妥当な範囲）
        assert pd.notna(r["expense_ratio"]) and 0 <= r["expense_ratio"] < 5, f"{tk} exp={r['expense_ratio']}"

    # 既存の個別株も残っている（退行していない）
    assert (df["market"] == "JP").sum() > 100
    assert (df["market"] == "US").sum() > 100

    print(f"OK: test_fund_rows passed (FUND={len(funds)}, total={len(df)})")


if __name__ == "__main__":
    main()
