# -*- coding: utf-8 -*-
"""ポートフォリオ損益の純粋計算（Streamlit非依存・テスト可能）。"""
from __future__ import annotations
import pandas as pd

POS_COLS = ["ticker", "shares", "avg_cost", "currency", "price", "value_native",
            "cost_native", "pl_native", "pl_pct", "value_jpy", "ok", "jpy_ok"]


def _to_jpy(amount: float, currency: str, usdjpy: float):
    if currency == "JPY":
        return amount
    if currency == "USD":
        return amount * usdjpy
    return float("nan")


def compute_positions(holdings: pd.DataFrame, prices: dict, usdjpy: float) -> pd.DataFrame:
    """holdings(ticker,shares,avg_cost) と prices({ticker:{price,currency}}) から1行=1保有を計算。"""
    rows = []
    for _, h in holdings.iterrows():
        tk = str(h["ticker"]).strip()
        if not tk:
            continue
        shares = float(h["shares"])
        avg = float(h["avg_cost"])
        info = prices.get(tk)
        ok = bool(info) and info.get("price") is not None
        price = float(info["price"]) if ok else float("nan")
        currency = (info.get("currency") if ok else None) or ("JPY" if tk.endswith(".T") else "USD")
        value_native = price * shares if ok else float("nan")
        cost_native = avg * shares
        pl_native = (value_native - cost_native) if ok else float("nan")
        pl_pct = (pl_native / cost_native * 100) if (ok and cost_native) else float("nan")
        value_jpy = _to_jpy(value_native, currency, usdjpy) if ok else float("nan")
        jpy_ok = ok and currency in ("JPY", "USD")
        rows.append(dict(ticker=tk, shares=shares, avg_cost=avg, currency=currency,
                         price=price, value_native=value_native, cost_native=cost_native,
                         pl_native=pl_native, pl_pct=pl_pct, value_jpy=value_jpy,
                         ok=ok, jpy_ok=jpy_ok))
    return pd.DataFrame(rows, columns=POS_COLS)


def summarize(positions: pd.DataFrame, cash_jpy: float, usdjpy: float) -> dict:
    """¥換算できる銘柄だけで合計し、総資産・評価損益を返す。"""
    conv = positions[positions["jpy_ok"]] if len(positions) else positions
    stock_jpy = float(conv["value_jpy"].sum()) if len(conv) else 0.0
    cost_total = 0.0
    for _, r in conv.iterrows():
        cost_total += _to_jpy(r["cost_native"], r["currency"], usdjpy)
    pl_jpy = stock_jpy - cost_total
    pl_pct = (pl_jpy / cost_total * 100) if cost_total else 0.0
    return dict(total_jpy=stock_jpy + float(cash_jpy), stock_jpy=stock_jpy,
                cash_jpy=float(cash_jpy), pl_jpy=pl_jpy, pl_pct=pl_pct)
