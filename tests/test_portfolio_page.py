# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from streamlit.testing.v1 import AppTest


def _fake_modules():
    import sys, types
    store = types.ModuleType("lib.store")
    store.HOLD_COLS = ["ticker", "shares", "avg_cost", "fx_cost"]
    store.CASH_COLS = ["date", "bank", "amount_jpy"]
    store.read_cash_ledger = lambda: pd.DataFrame(
        [{"date": "2026-06-01", "bank": "A銀行", "amount_jpy": 300000.0},
         {"date": "2026-06-01", "bank": "B銀行", "amount_jpy": 200000.0}])
    store.write_cash_ledger = lambda df: None
    store.read_holdings = lambda: pd.DataFrame(
        [{"ticker": "7203.T", "shares": 100, "avg_cost": 2000.0, "fx_cost": None},
         {"ticker": "楽天VTI", "shares": 10, "avg_cost": 250.0, "fx_cost": 145.0}])
    store.write_holdings = lambda df: None
    prices = types.ModuleType("lib.prices")
    # 楽天VTI は連動ETF VTI に置換されて問い合わされる
    prices.fetch_quotes = lambda tks: {
        "7203.T": {"price": 2850.0, "currency": "JPY"},
        "VTI": {"price": 280.0, "currency": "USD"}}
    prices.fetch_names = lambda tks: {}
    sys.modules["lib.store"] = store
    sys.modules["lib.prices"] = prices


def main():
    _fake_modules()
    at = AppTest.from_file("pages_portfolio.py", default_timeout=60)
    at.secrets["PORTFOLIO_PASSWORD"] = "x"
    at.session_state["pf_auth"] = True   # 認証済みにして本体を表示
    at.run()
    assert not at.exception, f"例外: {at.exception}"
    labels = [m.label for m in at.metric]
    assert any("総資産" in l for l in labels), labels
    print("OK: test_portfolio_page passed")


if __name__ == "__main__":
    main()
