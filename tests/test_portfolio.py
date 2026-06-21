# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from lib.portfolio import compute_positions, summarize


def main():
    holdings = pd.DataFrame([
        {"ticker": "7203.T", "shares": 100, "avg_cost": 2000.0},
        {"ticker": "AAPL", "shares": 10, "avg_cost": 150.0},
        {"ticker": "BAD", "shares": 5, "avg_cost": 10.0},
    ])
    prices = {
        "7203.T": {"price": 2850.0, "currency": "JPY"},
        "AAPL": {"price": 200.0, "currency": "USD"},
        # BAD は未収録 = 取得不可
    }
    usdjpy = 150.0
    pos = compute_positions(holdings, prices, usdjpy)

    t = pos[pos.ticker == "7203.T"].iloc[0]
    assert t.value_native == 285000.0
    assert t.cost_native == 200000.0
    assert t.pl_native == 85000.0
    assert abs(t.pl_pct - 42.5) < 1e-6
    assert t.value_jpy == 285000.0 and bool(t.jpy_ok)

    a = pos[pos.ticker == "AAPL"].iloc[0]
    assert a.currency == "USD"
    assert a.value_native == 2000.0
    assert a.value_jpy == 2000.0 * 150.0

    b = pos[pos.ticker == "BAD"].iloc[0]
    assert (not bool(b.ok)) and (not bool(b.jpy_ok))

    s = summarize(pos, cash_jpy=500000.0, usdjpy=usdjpy)
    assert abs(s["stock_jpy"] - (285000.0 + 300000.0)) < 1e-6
    assert abs(s["total_jpy"] - (285000.0 + 300000.0 + 500000.0)) < 1e-6
    # fx_cost 無し: 原価は現在レート(150)で換算 → AAPL原価=1500*150=225000 / pl=585000-425000=160000
    assert abs(s["pl_jpy"] - 160000.0) < 1e-6

    # --- fx_cost あり: 米国株の原価を「取得時ドル円」で換算 ---
    holdings2 = pd.DataFrame([
        {"ticker": "7203.T", "shares": 100, "avg_cost": 2000.0, "fx_cost": None},
        {"ticker": "AAPL", "shares": 10, "avg_cost": 150.0, "fx_cost": 140.0},  # 取得時140円/$
    ])
    pos2 = compute_positions(holdings2, prices, usdjpy)
    a2 = pos2[pos2.ticker == "AAPL"].iloc[0]
    # 原価(¥)=150*10*140=210000、評価額(¥)=200*10*150=300000、損益(¥)=90000
    assert abs(a2.cost_jpy - 210000.0) < 1e-6
    assert abs(a2.value_jpy - 300000.0) < 1e-6
    assert abs(a2.pl_jpy - 90000.0) < 1e-6
    t2 = pos2[pos2.ticker == "7203.T"].iloc[0]
    assert abs(t2.cost_jpy - 200000.0) < 1e-6  # 日本株はfx無関係
    s2 = summarize(pos2, cash_jpy=0.0)
    # 原価合計=200000+210000=410000、評価合計=285000+300000=585000、損益=175000
    assert abs(s2["pl_jpy"] - 175000.0) < 1e-6
    print("OK: test_portfolio passed")


if __name__ == "__main__":
    main()
