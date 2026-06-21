# -*- coding: utf-8 -*-
"""保有株の現在値・通貨を yfinance で取得（15分キャッシュ）。"""
from __future__ import annotations
import streamlit as st


@st.cache_data(ttl=15 * 60, show_spinner=False)
def fetch_quotes(tickers: tuple) -> dict:
    import yfinance as yf
    out = {}
    for tk in tickers:
        try:
            fi = yf.Ticker(tk).fast_info
            # fast_info の .get() はキャメルケースキー（lastPrice）
            price = fi.get("lastPrice") or fi.get("last_price")
            cur = fi.get("currency")
            if price:
                out[tk] = {"price": float(price),
                           "currency": cur or ("JPY" if tk.endswith(".T") else "USD")}
            else:
                out[tk] = None
        except Exception:
            out[tk] = None
    return out
