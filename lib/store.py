# -*- coding: utf-8 -*-
"""Google Sheets 保存層（gspread）。テストではこの関数群をモックする。"""
from __future__ import annotations
import pandas as pd
import streamlit as st

HOLD_COLS = ["ticker", "shares", "avg_cost"]


@st.cache_resource(show_spinner=False)
def _client():
    import gspread
    from google.oauth2.service_account import Credentials
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=scopes)
    return gspread.authorize(creds)


def _ws(name: str, headers: list):
    sh = _client().open_by_key(st.secrets["PORTFOLIO_SHEET_ID"])
    try:
        return sh.worksheet(name)
    except Exception:
        ws = sh.add_worksheet(title=name, rows=200, cols=max(2, len(headers)))
        ws.update([headers])
        return ws


def read_cash() -> float:
    recs = _ws("cash", ["amount_jpy"]).get_all_records()
    if recs:
        try:
            return float(recs[0].get("amount_jpy") or 0)
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def write_cash(amount_jpy: float) -> None:
    _ws("cash", ["amount_jpy"]).update([["amount_jpy"], [float(amount_jpy)]])


def read_holdings() -> pd.DataFrame:
    recs = _ws("holdings", HOLD_COLS).get_all_records()
    df = pd.DataFrame(recs, columns=HOLD_COLS)
    if not df.empty:
        df["ticker"] = df["ticker"].astype(str).str.strip()
        df["shares"] = pd.to_numeric(df["shares"], errors="coerce")
        df["avg_cost"] = pd.to_numeric(df["avg_cost"], errors="coerce")
        df = df[df["ticker"] != ""].dropna(subset=["shares", "avg_cost"]).reset_index(drop=True)
    return df


def write_holdings(df: pd.DataFrame) -> None:
    out = [HOLD_COLS]
    for _, r in df.iterrows():
        tk = str(r["ticker"]).strip()
        if not tk:
            continue
        out.append([tk, float(r["shares"]), float(r["avg_cost"])])
    ws = _ws("holdings", HOLD_COLS)
    ws.clear()
    ws.update(out)
