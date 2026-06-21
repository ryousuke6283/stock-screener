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
    store.read_cash = lambda: 500000.0
    store.write_cash = lambda a: None
    store.read_holdings = lambda: pd.DataFrame(
        [{"ticker": "7203.T", "shares": 100, "avg_cost": 2000.0, "fx_cost": None},
         {"ticker": "AAPL", "shares": 10, "avg_cost": 150.0, "fx_cost": 145.0}])
    store.write_holdings = lambda df: None
    prices = types.ModuleType("lib.prices")
    prices.fetch_quotes = lambda tks: {
        "7203.T": {"price": 2850.0, "currency": "JPY"},
        "AAPL": {"price": 200.0, "currency": "USD"}}
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
