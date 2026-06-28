# -*- coding: utf-8 -*-
"""ウォッチリストの集計（純粋関数・Streamlit非依存・テスト可能）。

watch = 1行が「ウォッチ銘柄 + 任意の目標買値 + メモ」。
到達判定は data.parquet の日次スナップショット株価（現地通貨）と目標買値を直接比較する。
"""
from __future__ import annotations
import pandas as pd

WATCH_COLS = ["ticker", "target_price", "memo"]

# build_watch_view が返す列（順序固定・UIはこの順で使う）
VIEW_COLS = ["ticker", "name", "market", "currency", "price",
             "target_price", "gap_pct", "reached", "memo"]


def _opt_float(v):
    """空欄/NaN/非数値は None、数値は float。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(f) else f


def clean_watch(watch_df: pd.DataFrame) -> pd.DataFrame:
    """生のウォッチ表を正規化（ticker必須、重複は後勝ちで除去）。columns=WATCH_COLS。"""
    if watch_df is None or watch_df.empty:
        return pd.DataFrame(columns=WATCH_COLS)
    d = watch_df.copy()
    for c in WATCH_COLS:
        if c not in d.columns:
            d[c] = None
    d["ticker"] = d["ticker"].astype(str).str.strip()
    d["memo"] = d["memo"].fillna("").astype(str)
    d["target_price"] = pd.to_numeric(d["target_price"], errors="coerce")
    d = d[~d["ticker"].isin(["", "nan", "None", "NaN"])]
    d = d.drop_duplicates(subset=["ticker"], keep="last").reset_index(drop=True)
    return d[WATCH_COLS]


def build_watch_view(watch_df: pd.DataFrame, data_df: pd.DataFrame) -> pd.DataFrame:
    """ウォッチ各行に銘柄名/現在値/通貨/市場/gap_pct/reached を付与して返す。

    - gap_pct = (target/price - 1)*100（現在値→目標まであと何%。負=既に目標以下）
    - reached = price <= target（target が有効な数値のときのみ True）
    - data_df に無い ticker は price=NaN・reached=False（「ウォッチのみ」）
    """
    w = clean_watch(watch_df)
    if w.empty:
        return pd.DataFrame(columns=VIEW_COLS)

    if data_df is not None and not data_df.empty:
        cols = [c for c in ("ticker", "name", "market", "currency", "price") if c in data_df.columns]
        info = data_df[cols].drop_duplicates(subset=["ticker"], keep="first")
    else:
        info = pd.DataFrame(columns=["ticker", "name", "market", "currency", "price"])

    m = w.merge(info, on="ticker", how="left")
    # data に無い銘柄は ticker を名前のフォールバックに
    m["name"] = m["name"].where(m["name"].notna(), m["ticker"])
    for c in ("market", "currency"):
        if c not in m.columns:
            m[c] = None

    def _gap(r):
        p, t = _opt_float(r.get("price")), _opt_float(r.get("target_price"))
        if p is None or t is None or p == 0:
            return float("nan")
        return (t / p - 1.0) * 100.0

    def _reached(r):
        p, t = _opt_float(r.get("price")), _opt_float(r.get("target_price"))
        return bool(p is not None and t is not None and p <= t)

    m["gap_pct"] = m.apply(_gap, axis=1)
    m["reached"] = m.apply(_reached, axis=1)
    return m[VIEW_COLS].reset_index(drop=True)
