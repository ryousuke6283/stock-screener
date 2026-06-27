# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from lib.cash import current_balances, total_cash, cash_history


def main():
    led = pd.DataFrame([
        {"date": "2026-06-01", "bank": "A", "amount_jpy": 100000},
        {"date": "2026-06-10", "bank": "A", "amount_jpy": 120000},  # Aの最新
        {"date": "2026-06-05", "bank": "B", "amount_jpy": 50000},
    ])

    cb = current_balances(led)
    a = cb[cb.bank == "A"].iloc[0]
    assert a.amount_jpy == 120000, a.amount_jpy
    assert abs(total_cash(led) - (120000 + 50000)) < 1e-6

    h = cash_history(led)
    assert abs(h.loc[pd.Timestamp("2026-06-01")] - 100000) < 1e-6
    assert abs(h.loc[pd.Timestamp("2026-06-05")] - 150000) < 1e-6   # A=100000(前埋め)+B=50000
    assert abs(h.loc[pd.Timestamp("2026-06-10")] - 170000) < 1e-6   # A=120000+B=50000(前埋め)

    # 空・欠損
    assert total_cash(pd.DataFrame(columns=["date", "bank", "amount_jpy"])) == 0.0
    print("OK: test_cash passed")


if __name__ == "__main__":
    main()
