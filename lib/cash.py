# -*- coding: utf-8 -*-
"""預金台帳の集計（純粋関数・Streamlit非依存・テスト可能）。

台帳 = 1行が「ある日付・ある銀行の残高」。
- 現在残高 = 各銀行の最新日付の残高
- 履歴     = 日付ごとの総預金（各銀行を最新値で前埋めして合計）
"""
from __future__ import annotations
import pandas as pd

CASH_COLS = ["date", "bank", "amount_jpy"]


def _clean(ledger: pd.DataFrame) -> pd.DataFrame:
    if ledger is None or ledger.empty:
        return pd.DataFrame(columns=CASH_COLS)
    d = ledger.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d["bank"] = d["bank"].astype(str).str.strip()
    d["amount_jpy"] = pd.to_numeric(d["amount_jpy"], errors="coerce")
    d = d[~d["bank"].isin(["", "nan", "None", "NaN"])]
    d = d.dropna(subset=["date", "amount_jpy"]).reset_index(drop=True)
    return d


def current_balances(ledger: pd.DataFrame) -> pd.DataFrame:
    """各銀行の最新日付の残高。columns: bank, amount_jpy, date（dateの新しい順）。"""
    d = _clean(ledger)
    if d.empty:
        return pd.DataFrame(columns=["bank", "amount_jpy", "date"])
    latest = d.sort_values("date").groupby("bank", as_index=False).last()
    return latest[["bank", "amount_jpy", "date"]].sort_values("date", ascending=False).reset_index(drop=True)


def total_cash(ledger: pd.DataFrame) -> float:
    cb = current_balances(ledger)
    return float(cb["amount_jpy"].sum()) if not cb.empty else 0.0


def cash_history(ledger: pd.DataFrame) -> pd.Series:
    """日付 -> 総預金（各銀行を最新値で前埋めして合計）。index=date の Series。"""
    d = _clean(ledger)
    if d.empty:
        return pd.Series(dtype=float)
    piv = d.pivot_table(index="date", columns="bank", values="amount_jpy", aggfunc="last")
    piv = piv.sort_index().ffill()
    return piv.sum(axis=1)
