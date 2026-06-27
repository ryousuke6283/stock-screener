# -*- coding: utf-8 -*-
"""Google Sheets 保存層（gspread）。テストではこの関数群をモックする。"""
from __future__ import annotations
import pandas as pd
import streamlit as st

from lib.cash import CASH_COLS  # ["date", "bank", "amount_jpy"]

HOLD_COLS = ["ticker", "shares", "avg_cost", "fx_cost"]


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


def read_cash_ledger() -> pd.DataFrame:
    """預金台帳（date, bank, amount_jpy）。1行=ある日付のその銀行の残高。"""
    recs = _ws("cash", CASH_COLS).get_all_records()
    df = pd.DataFrame(recs, columns=CASH_COLS)
    if not df.empty:
        df["date"] = df["date"].astype(str).str.strip()
        df["bank"] = df["bank"].astype(str).str.strip()
        df["amount_jpy"] = pd.to_numeric(df["amount_jpy"], errors="coerce")
        df = df[~df["bank"].isin(["", "nan", "None", "NaN"])].reset_index(drop=True)
    return df


def write_cash_ledger(df: pd.DataFrame) -> None:
    out = [CASH_COLS]
    for _, r in df.iterrows():
        bank = str(r["bank"]).strip()
        if not bank:
            continue
        d = r.get("date")
        # 日付を YYYY-MM-DD 文字列に
        date_str = "" if (d is None or pd.isna(d)) else str(pd.to_datetime(d).date())
        amt = r.get("amount_jpy")
        amt_val = float(amt) if (amt is not None and not pd.isna(amt)) else 0.0
        out.append([date_str, bank, amt_val])
    ws = _ws("cash", CASH_COLS)
    ws.clear()
    ws.update(out)


def read_holdings() -> pd.DataFrame:
    recs = _ws("holdings", HOLD_COLS).get_all_records()
    df = pd.DataFrame(recs, columns=HOLD_COLS)
    if not df.empty:
        df["ticker"] = df["ticker"].astype(str).str.strip()
        df["shares"] = pd.to_numeric(df["shares"], errors="coerce")
        df["avg_cost"] = pd.to_numeric(df["avg_cost"], errors="coerce")
        df["fx_cost"] = pd.to_numeric(df["fx_cost"], errors="coerce")  # 任意（空欄=NaN）
        df = df[df["ticker"] != ""].dropna(subset=["shares", "avg_cost"]).reset_index(drop=True)
    return df


def write_holdings(df: pd.DataFrame) -> None:
    out = [HOLD_COLS]
    for _, r in df.iterrows():
        tk = str(r["ticker"]).strip()
        if not tk:
            continue
        fx = r.get("fx_cost") if "fx_cost" in df.columns else None
        fx_val = float(fx) if (fx is not None and not pd.isna(fx)) else ""
        out.append([tk, float(r["shares"]), float(r["avg_cost"]), fx_val])
    ws = _ws("holdings", HOLD_COLS)
    ws.clear()
    ws.update(out)
