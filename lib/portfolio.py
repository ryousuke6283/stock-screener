# -*- coding: utf-8 -*-
"""ポートフォリオ損益の純粋計算（Streamlit非依存・テスト可能）。"""
from __future__ import annotations
import pandas as pd

POS_COLS = ["ticker", "shares", "avg_cost", "fx_cost", "currency", "price",
            "value_native", "cost_native", "pl_native", "pl_pct",
            "value_jpy", "cost_jpy", "pl_jpy", "ok", "jpy_ok"]


def _to_jpy(amount: float, currency: str, usdjpy: float):
    if currency == "JPY":
        return amount
    if currency == "USD":
        return amount * usdjpy
    return float("nan")


def _opt_float(v):
    """空欄/NaN/非数値は None、数値は float。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(f) else f


def compute_positions(holdings: pd.DataFrame, prices: dict, usdjpy: float) -> pd.DataFrame:
    """holdings(ticker,shares,avg_cost[,fx_cost]) と prices({ticker:{price,currency}}) から
    1行=1保有を計算。米国株の取得原価は fx_cost(取得時1ドル=円) があればそれで円換算、
    無ければ現在レート。評価額は常に現在レート。"""
    has_fx = "fx_cost" in holdings.columns
    rows = []
    for _, h in holdings.iterrows():
        tk = str(h["ticker"]).strip()
        if not tk:
            continue
        shares = float(h["shares"])
        avg = float(h["avg_cost"])
        fx = _opt_float(h["fx_cost"]) if has_fx else None
        info = prices.get(tk)
        ok = bool(info) and info.get("price") is not None
        price = float(info["price"]) if ok else float("nan")
        currency = (info.get("currency") if ok else None) or ("JPY" if tk.endswith(".T") else "USD")
        value_native = price * shares if ok else float("nan")
        cost_native = avg * shares
        pl_native = (value_native - cost_native) if ok else float("nan")
        pl_pct = (pl_native / cost_native * 100) if (ok and cost_native) else float("nan")
        value_jpy = _to_jpy(value_native, currency, usdjpy) if ok else float("nan")
        # 取得原価の円換算: USDは取得時レート(fx)優先、無ければ現在レート
        if currency == "JPY":
            cost_jpy = cost_native
        elif currency == "USD":
            cost_jpy = cost_native * (fx if fx else usdjpy)
        else:
            cost_jpy = float("nan")
        pl_jpy = (value_jpy - cost_jpy) if (ok and not pd.isna(cost_jpy)) else float("nan")
        jpy_ok = ok and currency in ("JPY", "USD")
        rows.append(dict(ticker=tk, shares=shares, avg_cost=avg, fx_cost=fx, currency=currency,
                         price=price, value_native=value_native, cost_native=cost_native,
                         pl_native=pl_native, pl_pct=pl_pct, value_jpy=value_jpy,
                         cost_jpy=cost_jpy, pl_jpy=pl_jpy, ok=ok, jpy_ok=jpy_ok))
    return pd.DataFrame(rows, columns=POS_COLS)


def summarize(positions: pd.DataFrame, cash_jpy: float, usdjpy: float = None) -> dict:
    """¥換算できる銘柄だけで合計し、総資産・評価損益を返す（原価は取得時レート反映済み）。"""
    conv = positions[positions["jpy_ok"]] if len(positions) else positions
    stock_jpy = float(conv["value_jpy"].sum()) if len(conv) else 0.0
    cost_total = float(conv["cost_jpy"].sum()) if len(conv) else 0.0
    pl_jpy = stock_jpy - cost_total
    pl_pct = (pl_jpy / cost_total * 100) if cost_total else 0.0
    return dict(total_jpy=stock_jpy + float(cash_jpy), stock_jpy=stock_jpy,
                cash_jpy=float(cash_jpy), pl_jpy=pl_jpy, pl_pct=pl_pct)
