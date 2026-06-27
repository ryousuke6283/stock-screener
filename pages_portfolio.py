# -*- coding: utf-8 -*-
"""マイポートフォリオ（パスワード保護・Google Sheets・損益表示）"""
import sys, os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)
import datetime as _dt
import pandas as pd
import streamlit as st

from lib.common import usdjpy_rate, resolve_name, quote_ticker
from lib.portfolio import compute_positions, summarize
from lib import store, prices, cash as cashlib

st.markdown("### :material/account_balance_wallet: マイポートフォリオ")


# ---- 簡易パスワード（このページのみ）----
def _gate() -> bool:
    if st.session_state.get("pf_auth"):
        return True
    st.caption("このページはパスワード保護されています。")
    pw = st.text_input("パスワード", type="password")
    if st.button("ログイン", type="primary", icon=":material/login:"):
        if pw and pw == st.secrets.get("PORTFOLIO_PASSWORD"):
            st.session_state["pf_auth"] = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    return False


if not _gate():
    st.stop()

# ---- データ読み込み ----
try:
    ledger = store.read_cash_ledger()
    holdings = store.read_holdings()
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")
    st.stop()

cash = cashlib.total_cash(ledger)
rate = usdjpy_rate()

# 価格: 投資信託は連動ETFに置換して取得し、元のtickerキーに戻す
tks = list(holdings["ticker"]) if not holdings.empty else []
qmap = {tk: quote_ticker(tk) for tk in tks}
raw = prices.fetch_quotes(tuple(sorted(set(qmap.values())))) if tks else {}
quotes = {tk: raw.get(qmap[tk]) for tk in tks}
pos = compute_positions(holdings, quotes, rate)
s = summarize(pos, cash, rate)

# 銘柄名: ファンド名/対象銘柄名/既知名で解決、未解決はYahooの名称で補完
names = {tk: resolve_name(tk) for tk in tks}
unknown = [tk for tk in tks if names.get(tk) == tk]
if unknown:
    yn = prices.fetch_names(tuple(unknown))
    for tk in unknown:
        if yn.get(tk):
            names[tk] = yn[tk]

# ---- サマリー ----
def _yen(v):
    return "—" if pd.isna(v) else f"¥{v:,.0f}"

c = st.columns(4)
c[0].metric(":material/account_balance: 総資産", _yen(s["total_jpy"]))
c[1].metric(":material/trending_up: 評価損益", _yen(s["pl_jpy"]), f"{s['pl_pct']:+.1f}%")
c[2].metric(":material/savings: 現預金", _yen(s["cash_jpy"]))
c[3].metric(":material/show_chart: 株式評価額", _yen(s["stock_jpy"]))

st.divider()

# ---- 預金（銀行ごと・日付つき台帳）----
st.markdown("#### :material/savings: 預金（銀行ごと・履歴）")
st.caption("1行 = ある日付のその銀行の残高。日付を変えて追加すると履歴になります。"
           "現在の預金 = 各銀行の最新日付の残高の合計。")
bver = st.session_state.setdefault("pf_bank_ver", 0)
if ledger.empty:
    ledger_src = pd.DataFrame(columns=store.CASH_COLS)
else:
    ledger_src = ledger.copy()
    ledger_src["date"] = pd.to_datetime(ledger_src["date"], errors="coerce")
ledger_edited = st.data_editor(
    ledger_src,
    num_rows="dynamic",
    width="stretch",
    column_config={
        "date": st.column_config.DateColumn("日付", default=_dt.date.today(), format="YYYY-MM-DD"),
        "bank": st.column_config.TextColumn("銀行", required=True),
        "amount_jpy": st.column_config.NumberColumn("残高(円)", min_value=0.0, format="¥%.0f"),
    },
    column_order=["date", "bank", "amount_jpy"],
    key=f"pf_bank_{bver}",
)
st.caption(f"現在の預金合計（各銀行の最新）: ¥{cashlib.total_cash(ledger_edited):,.0f}")
if st.button("預金を保存", type="primary", icon=":material/save:"):
    store.write_cash_ledger(ledger_edited)
    st.session_state["pf_bank_ver"] = bver + 1
    st.success("保存しました。")
    st.rerun()

# 総預金の推移チャート
hist = cashlib.cash_history(ledger)
if len(hist) >= 2:
    st.caption("総預金の推移")
    st.line_chart(hist, color="#18181b", height=240)

st.divider()

# ---- 保有株の編集 ----
st.markdown("#### :material/edit_note: 保有株を編集")
st.caption("行の追加・編集・削除ができます。米国株は『取得時¥/$』に買った時の1ドル=円を入れると損益が正確に（空欄なら現在レート）。"
           "投資信託は ticker 欄に 楽天VTI / S&P500 / オルカン / ナスダック と入力すると連動ETFで概算します。")
ver = st.session_state.setdefault("pf_editor_ver", 0)
src = holdings if not holdings.empty else pd.DataFrame(columns=store.HOLD_COLS)
edited = st.data_editor(
    src,
    num_rows="dynamic",
    width="stretch",
    column_config={
        "ticker": st.column_config.TextColumn("ティッカー", required=True,
                                              help="日本株=4桁+.T (例 7203.T) / 米国株=シンボル (例 AAPL)"),
        "shares": st.column_config.NumberColumn("株数", min_value=0.0, step=1.0),
        "avg_cost": st.column_config.NumberColumn("平均取得単価", min_value=0.0,
                                                  help="現地通貨建て（日本株=円 / 米国株=ドル）"),
        "fx_cost": st.column_config.NumberColumn("取得時¥/$ (米国株)", min_value=0.0,
                                                 help="米国株のみ: 買った時の1ドル=何円。空欄なら現在レートで換算"),
    },
    key=f"pf_editor_{ver}",
)
if st.button("保有株を保存", type="primary", icon=":material/save:"):
    store.write_holdings(edited)
    st.session_state["pf_editor_ver"] = ver + 1   # 保存後はエディタを作り直して編集詰まりを防ぐ
    st.success("保存しました。")
    st.rerun()

st.divider()

# ---- 保有株テーブル（計算結果）----
st.markdown("#### :material/table_rows: 保有株（評価損益）")
if pos.empty:
    st.info("保有株がありません。上で追加してください。", icon=":material/info:")
else:
    view = pd.DataFrame({
        "コード": list(pos["ticker"]),
        "銘柄名": [names.get(t, t) for t in pos["ticker"]],
        "株数": pos["shares"],
        "取得単価": pos["avg_cost"],
        "取得時¥/$": pos["fx_cost"],
        "現在値": pos["price"],
        "評価額(¥)": pos["value_jpy"],
        "損益(¥)": pos["pl_jpy"],
        "損益%": pos["pl_pct"],
        "通貨": pos["currency"],
    })

    def _pl_color(val):
        if pd.isna(val):
            return ""
        return "color:#16a34a" if val > 0 else ("color:#dc2626" if val < 0 else "")

    styled = view.style.map(_pl_color, subset=["損益(¥)", "損益%"])
    st.dataframe(
        styled, width="stretch", hide_index=True,
        column_config={
            "取得単価": st.column_config.NumberColumn(format="%.2f"),
            "取得時¥/$": st.column_config.NumberColumn(format="%.1f"),
            "現在値": st.column_config.NumberColumn(format="%.2f"),
            "評価額(¥)": st.column_config.NumberColumn(format="¥%.0f"),
            "損益(¥)": st.column_config.NumberColumn(format="¥%.0f"),
            "損益%": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    bad = pos[~pos["ok"]]["ticker"].tolist()
    if bad:
        st.caption("現在値を取得できなかった銘柄（合計から除外）: " + ", ".join(bad))

st.caption(f"為替: 1ドル ≒ {rate:.1f}円 ／ 現在値は15分キャッシュ")
