# -*- coding: utf-8 -*-
import pandas as pd
import streamlit as st
from lib.common import (
    SECTOR_JP, US_NAME_JP, LOGO_SVG, usdjpy_rate, load_data,
    disp_name, fmt, compact,
)
from lib import store, watch as watchlib

df = load_data()
fetched = pd.to_datetime(df["fetched_at"].iloc[0]).tz_convert("Asia/Tokyo")


# ---------------- ウォッチリスト（Google Sheets保存・失敗時は機能オフ）----------------
@st.cache_data(ttl=120, show_spinner=False)
def _load_watch():
    """ウォッチを読み込む。Secrets未設定/取得失敗なら (空df, False)=機能オフ。"""
    try:
        return store.read_watch(), True
    except Exception:
        return pd.DataFrame(columns=watchlib.WATCH_COLS), False


def _save_watch(new_df: pd.DataFrame) -> None:
    store.write_watch(new_df)
    _load_watch.clear()   # 次のrunで最新を読む


watch_df, watch_enabled = _load_watch()
watched = set(watch_df["ticker"]) if not watch_df.empty else set()


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_income(ticker: str):
    """年次の損益計算書を取得（クリックされた1銘柄のみ・キャッシュ）。"""
    import yfinance as yf
    try:
        return yf.Ticker(ticker).income_stmt
    except Exception:
        return None


# 株価チャートの期間 → yfinance の period/interval（"start"は今日からの日数指定）
PERIODS = {
    "1日": dict(period="1d", interval="5m"),
    "1週": dict(period="5d", interval="15m"),
    "2週": dict(start=14, interval="60m"),
    "1ヶ月": dict(period="1mo", interval="1d"),
    "3ヶ月": dict(period="3mo", interval="1d"),
    "半年": dict(period="6mo", interval="1d"),
    "1年": dict(period="1y", interval="1d"),
    "2年": dict(period="2y", interval="1wk"),
    "3年": dict(period="3y", interval="1wk"),
    "5年": dict(period="5y", interval="1wk"),
    "上場来": dict(period="max", interval="1mo"),
}


@st.cache_data(ttl=30 * 60, show_spinner=False)
def fetch_price(ticker: str, label: str):
    """指定期間の株価（終値）を取得。"""
    import yfinance as yf
    from datetime import date, timedelta
    cfg = PERIODS[label]
    try:
        t = yf.Ticker(ticker)
        if "start" in cfg:
            h = t.history(start=date.today() - timedelta(days=cfg["start"]), interval=cfg["interval"])
        else:
            h = t.history(period=cfg["period"], interval=cfg["interval"])
        if h is None or h.empty:
            return None
        return h[["Close"]].rename(columns={"Close": "終値"})
    except Exception:
        return None


# 棒グラフのモノトーン配色（売上=黒 / 営業利益=中グレー / 純利益=薄グレー）
_BAR_GRAY = {"売上高": "#18181b", "営業利益": "#71717a", "純利益": "#a1a1aa"}


def build_financials_table(inc, cur: str):
    """income_stmt から 売上高/営業利益/純利益/EPS を年次テーブル化（古い年→新しい年）。"""
    if inc is None or getattr(inc, "empty", True):
        return None
    cols = list(inc.columns)[:4][::-1]      # 直近4年、古い順
    years = [str(getattr(c, "year", c)) for c in cols]
    out = pd.DataFrame(index=years)
    money = {"Total Revenue": f"売上高(十億{cur})", "Operating Income": f"営業利益(十億{cur})",
             "Net Income": f"純利益(十億{cur})"}
    for key, label in money.items():
        if key in inc.index:
            out[label] = [round(inc.loc[key, c] / 1e9, 1) if pd.notna(inc.loc[key, c]) else None for c in cols]
    for key in ("Diluted EPS", "Basic EPS"):
        if key in inc.index:
            out["EPS"] = [round(inc.loc[key, c], 2) if pd.notna(inc.loc[key, c]) else None for c in cols]
            break
    return out


def render_detail(row: pd.Series) -> None:
    name = disp_name(row["ticker"], row["name"], row["market"])
    cur = row.get("currency") or ""
    market_jp = "日本株" if row["market"] == "JP" else "米国株"
    st.divider()
    st.markdown(
        f"### {name} "
        f"<span class='dim'>{row['ticker']} · {market_jp} · {row['sector_jp']}</span>",
        unsafe_allow_html=True,
    )

    # メインから移した指標（PC=4列/スマホ=2列のグリッドで間延び防止）
    items = [
        ("株価", f"{fmt(row['price'], 1)} {cur}", ""),
        ("時価総額", f"${compact(row['market_cap_usd'])}", f"現地通貨 {compact(row['market_cap'])} {cur}"),
        ("PER", fmt(row["per"], 1), ""),
        ("PBR", fmt(row["pbr"], 2), ""),
        ("配当利回り", fmt(row["dividend_yield"], 2, "%"), ""),
        ("ROE", fmt(row["roe_pct"], 1, "%"), ""),
        ("増収率", fmt(row["rev_growth_pct"], 1, "%"), ""),
        ("増益率", fmt(row["earn_growth_pct"], 1, "%"), ""),
        ("PSR", fmt(row["psr"], 2), ""),
        ("50日線乖離", fmt(row["pct_vs_ma50"], 1, "%"), ""),
        ("200日線乖離", fmt(row["pct_vs_ma200"], 1, "%"), ""),
        ("52週高値比", fmt(row["pct_from_52w_high"], 1, "%"), ""),
    ]
    parts = []
    for label, val, tip in items:
        t = f' title="{tip}"' if tip else ""
        parts.append(f'<div class="m"{t}><div class="m-l">{label}</div><div class="m-v">{val}</div></div>')
    st.markdown(f'<div class="metric-grid">{"".join(parts)}</div>', unsafe_allow_html=True)

    # 財務（年次） — グラフはモノトーン＆幅を左寄せで制限（PCで間延びさせない）
    with st.spinner("財務データを取得中…"):
        inc = fetch_income(row["ticker"])
    st.markdown("#### 財務（年次・数年分）")
    fin = build_financials_table(inc, cur)
    if fin is not None and not fin.empty:
        st.dataframe(fin, width="stretch")
        money_cols = [c for c in fin.columns if c.startswith(("売上高", "営業利益", "純利益"))]
        if money_cols:
            colors = [_BAR_GRAY[next(k for k in _BAR_GRAY if c.startswith(k))] for c in money_cols]
            with st.columns([3, 2])[0]:
                st.bar_chart(fin[money_cols], color=colors, height=260)
    else:
        st.caption("この銘柄の財務データは取得できませんでした。")

    # 株価チャート（期間切替・モノトーン・"終値"表記）
    st.markdown("#### 株価チャート")
    period = st.segmented_control("期間", list(PERIODS), default="1年", key=f"pd_{row['ticker']}") or "1年"
    with st.spinner("株価データを取得中…"):
        h = fetch_price(row["ticker"], period)
    if h is not None and not h.empty:
        with st.columns([3, 2])[0]:
            st.line_chart(h["終値"], color="#18181b", height=300)
    else:
        st.caption("この期間の株価データは取得できませんでした。")


def render_watch_panel(watch_df: pd.DataFrame, data_df: pd.DataFrame, enabled: bool) -> None:
    """一覧の最上部のウォッチリスト（先頭表示・到達アラート・編集）。"""
    st.markdown("#### :material/star: ウォッチリスト")
    if not enabled:
        st.caption("ウォッチ機能は現在利用できません（保存先が未設定）。")
        return

    wv = watchlib.build_watch_view(watch_df, data_df)
    if wv.empty:
        st.caption("ウォッチ銘柄はまだありません。下の一覧で銘柄を選び「★ ウォッチに追加」を押すと、ここに表示されます。")
    else:
        reached = list(wv["reached"])
        disp = pd.DataFrame({
            "状態": ["買い時" if r else ("—" if pd.isna(t) else "監視中")
                    for r, t in zip(reached, wv["target_price"])],
            "銘柄": [disp_name(tk, nm, mk) for tk, nm, mk in zip(wv["ticker"], wv["name"], wv["market"])],
            "市場": wv["market"].map({"JP": "日本", "US": "米国"}).fillna(""),
            "現在値": wv["price"],
            "目標買値": wv["target_price"],
            "あと%": wv["gap_pct"],
            "メモ": wv["memo"],
            "通貨": wv["currency"],
        })

        def _tint(row):
            return ["background-color:#dcfce7" if reached[row.name] else ""] * len(row)

        styled = disp.style.apply(_tint, axis=1)
        st.dataframe(
            styled, width="stretch", hide_index=True,
            column_config={
                "現在値": st.column_config.NumberColumn(format="%.1f"),
                "目標買値": st.column_config.NumberColumn(format="%.1f"),
                "あと%": st.column_config.NumberColumn(
                    format="%+.1f%%", help="現在値から目標買値まであと何%（マイナス＝すでに目標以下）"),
            },
        )
        n_reached = int(wv["reached"].sum())
        if n_reached:
            st.success(f"{n_reached}銘柄が目標買値に到達しています（買い時）。",
                       icon=":material/notifications_active:")

    # 編集（目標買値・メモ・追加・削除）
    with st.expander(":material/edit: ウォッチを編集（目標買値・メモ・追加・削除）"):
        wver = st.session_state.setdefault("watch_ver", 0)
        src = watch_df if not watch_df.empty else pd.DataFrame(columns=watchlib.WATCH_COLS)
        edited = st.data_editor(
            src, num_rows="dynamic", width="stretch",
            column_config={
                "ticker": st.column_config.TextColumn(
                    "ティッカー", required=True,
                    help="日本株=4桁+.T（例 7203.T）/ 米国株=シンボル（例 AAPL）"),
                "target_price": st.column_config.NumberColumn(
                    "目標買値", min_value=0.0,
                    help="現地通貨（日本株=円 / 米国株=ドル）。空欄なら到達判定なし"),
                "memo": st.column_config.TextColumn("メモ"),
            },
            column_order=["ticker", "target_price", "memo"],
            key=f"watch_editor_{wver}",
        )
        if st.button("ウォッチを保存", type="primary", icon=":material/save:", key="watch_save"):
            _save_watch(edited)
            st.session_state["watch_ver"] = wver + 1
            st.success("保存しました。")
            st.rerun()

# ---------------- スライダー定義（OFF値＝この端ならフィルタ無効） ----------------
# (key, ラベル, min, max, step, 種類['max'/'min'], 対象カラム)
SLIDERS = [
    ("per_max",  "PER 上限",          0.0, 200.0, 1.0,  "max", "per"),
    ("pbr_max",  "PBR 上限",          0.0,  30.0, 0.1,  "max", "pbr"),
    ("psr_max",  "PSR 上限",          0.0,  30.0, 0.1,  "max", "psr"),
    ("div_min",  "配当利回り 下限 (%)", 0.0,  10.0, 0.1,  "min", "dividend_yield"),
    ("roe_min",  "ROE 下限 (%)",     -50.0,  60.0, 1.0,  "min", "roe_pct"),
    ("rev_min",  "増収率 下限 (%)",   -50.0, 150.0, 1.0,  "min", "rev_growth_pct"),
    ("ma200_min","200日線乖離 下限 (%)", -60.0, 60.0, 1.0, "min", "pct_vs_ma200"),
    ("ma50_min", "50日線乖離 下限 (%)",  -60.0, 60.0, 1.0, "min", "pct_vs_ma50"),
]
OFF = {}   # 各スライダーの「無効」値
for key, _l, lo, hi, _s, kind, _c in SLIDERS:
    OFF[key] = hi if kind == "max" else lo

# プリセット: スタイル別の初期条件
PRESETS = {
    "バリュー（割安）":   {"per_max": 15.0, "pbr_max": 1.5, "div_min": 2.5},
    "高配当":            {"div_min": 3.5},
    "グロース（成長）":   {"rev_min": 15.0},
    "クオリティ（優良）": {"roe_min": 15.0},
    "モメンタム":        {"ma200_min": 5.0, "ma50_min": 0.0},
}
# プリセットのアイコン（Material Symbols = モノトーン線画）
PRESET_ICONS = {
    "バリュー（割安）":   ":material/sell:",          # 値札
    "高配当":            ":material/payments:",       # 配当
    "グロース（成長）":   ":material/trending_up:",    # 右肩上がり
    "クオリティ（優良）": ":material/verified:",       # 認証マーク
    "モメンタム":        ":material/bolt:",           # 勢い
}

# session_state 初期化
for key in OFF:
    st.session_state.setdefault(key, OFF[key])


def apply_preset(cfg: dict):
    for key in OFF:                       # まず全部OFFに戻す
        st.session_state[key] = OFF[key]
    for key, val in cfg.items():          # プリセット値を上書き
        st.session_state[key] = val


# ---------------- サイドバー ----------------
st.sidebar.markdown(
    f'<div class="brand">{LOGO_SVG}<span>株スクリーナー</span></div>',
    unsafe_allow_html=True,
)
st.sidebar.caption(f"データ更新: {fetched:%Y-%m-%d %H:%M} JST")

st.sidebar.subheader(":material/style: スタイル別プリセット")
# 1列・全幅でボタンの縦横サイズを統一
for name, cfg in PRESETS.items():
    if st.sidebar.button(name, icon=PRESET_ICONS[name], width="stretch"):
        apply_preset(cfg)
if st.sidebar.button("条件をリセット", icon=":material/refresh:", width="stretch"):
    apply_preset({})

st.sidebar.divider()

# 市場
market = st.sidebar.radio(":material/public: 市場", ["両方", "日本株", "米国株"], horizontal=True)

# セクター（日本語表記）
sectors = sorted(df["sector_jp"].dropna().unique())
sel_sectors = st.sidebar.multiselect(":material/category: セクター（空＝全部）", sectors, default=[])

st.sidebar.subheader(":material/tune: 詳細条件")
for key, label, lo, hi, step, kind, col in SLIDERS:
    st.sidebar.slider(label, lo, hi, step=step, key=key)

# ---------------- 絞り込み ----------------
mask = pd.Series(True, index=df.index)

if market == "日本株":
    mask &= df["market"].eq("JP")
elif market == "米国株":
    mask &= df["market"].eq("US")

if sel_sectors:
    mask &= df["sector_jp"].isin(sel_sectors)

active_filters = []
for key, label, lo, hi, step, kind, col in SLIDERS:
    val = st.session_state[key]
    if val == OFF[key]:
        continue  # 端＝無効なのでスキップ（NaN銘柄を不当に除外しない）
    active_filters.append(f"{label} = {val:g}")
    if kind == "max":
        mask &= df[col] <= val      # NaN は False → 除外（割安条件で赤字を弾く等は妥当）
    else:
        mask &= df[col] >= val

res = df[mask].copy()

# ---------------- メイン表示 ----------------
st.markdown(
    f"""
    <div class="hero">
      <div class="hero-kicker">STOCK SCREENER</div>
      <div class="hero-title">{LOGO_SVG}<span>日本株・米国株 スクリーニング</span></div>
      <div class="hero-sub">Nikkei&nbsp;225 + S&amp;P&nbsp;500 ・ {len(df)}銘柄をスタイル別に絞り込み</div>
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3 = st.columns(3)
m1.metric(":material/filter_alt: 該当銘柄", f"{len(res)} 件")
m2.metric(":material/currency_yen: 日本株", int((res['market'] == 'JP').sum()))
m3.metric(":material/attach_money: 米国株", int((res['market'] == 'US').sum()))

if active_filters:
    st.caption("適用中の数値条件: " + " / ".join(active_filters))
else:
    st.caption("数値条件なし（市場・セクターのみ）")

# ====== ウォッチリスト（一覧の先頭に固定表示・到達アラート）======
render_watch_panel(watch_df, df, watch_enabled)
st.divider()

# ====== 一覧（コンパクト）: コード/通貨/PER以降は詳細パネルへ移動 ======
res = res.assign(
    _disp=[disp_name(t, n, m) for t, n, m in zip(res["ticker"], res["name"], res["market"])]
)

# 並べ替え（表示していない指標でもソート可能） — 下端揃えで行をきれいに
SORT_COLS = {
    "時価総額": "market_cap_usd", "株価": "price", "PER": "per", "PBR": "pbr",
    "配当%": "dividend_yield", "ROE%": "roe_pct", "増収%": "rev_growth_pct",
    "200日線乖離%": "pct_vs_ma200",
}
sc1, sc2 = st.columns([3, 1], vertical_alignment="bottom")
with sc1:
    sort_label = st.selectbox(":material/sort: 並べ替え", list(SORT_COLS), index=0)
with sc2:
    ascending = st.toggle("昇順", value=False)
res = res.sort_values(SORT_COLS[sort_label], ascending=ascending, na_position="last").reset_index(drop=True)

# メイン表示はコンパクトに（銘柄・市場・セクター・株価・時価総額のみ）
MAIN_COLS = {"_disp": "銘柄", "market": "市場", "sector_jp": "セクター",
             "price": "株価", "market_cap_usd": "時価総額($)"}
view = res[list(MAIN_COLS)].rename(columns=MAIN_COLS)
view["市場"] = view["市場"].map({"JP": "日本", "US": "米国"}).fillna(view["市場"])
view.insert(0, "★", ["★" if t in watched else "" for t in res["ticker"]])  # ウォッチ済みを区別


def _row_tint(r):
    # 日本=うっすらグレー / 米国=白 でやさしく区別
    bg = "#f1f2f4" if r["市場"] == "日本" else "#ffffff"
    return [f"background-color:{bg}"] * len(r)


styled = view.style.apply(_row_tint, axis=1)

st.caption(f"行クリック（スマホは下の選択ボックス）で詳細＋数年分の財務 ／ 時価総額は日米比較のためUSD換算（1ドル≒{usdjpy_rate():.0f}円）")
event = st.dataframe(
    styled,
    width="stretch",
    hide_index=True,
    height=430,
    on_select="rerun",
    selection_mode="single-row",
    key="result_tbl",
    column_config={
        "★": st.column_config.TextColumn(width="small", help="ウォッチ登録済み"),
        "株価": st.column_config.NumberColumn(format="%.1f"),
        "時価総額($)": st.column_config.NumberColumn(format="compact"),
    },
)

# CSVは全指標を残す
EXPORT = {
    "ticker": "コード", "_disp": "銘柄", "market": "市場", "sector_jp": "セクター",
    "price": "株価", "currency": "通貨", "market_cap": "時価総額",
    "per": "PER", "pbr": "PBR", "psr": "PSR", "dividend_yield": "配当%",
    "roe_pct": "ROE%", "rev_growth_pct": "増収%", "earn_growth_pct": "増益%",
    "pct_vs_ma50": "50d乖離%", "pct_vs_ma200": "200d乖離%", "pct_from_52w_high": "52w高値比%",
}
st.download_button(
    "この結果をCSVダウンロード（全指標）",
    res[list(EXPORT)].rename(columns=EXPORT).to_csv(index=False).encode("utf-8-sig"),
    file_name="screen_result.csv",
    mime="text/csv",
    icon=":material/download:",
)

# ====== 詳細パネル（一覧の行クリック or 下のセレクトボックス） ======
names = [f"{n}　{t}" for n, t in zip(res["_disp"], res["ticker"])]
pick = st.selectbox(":material/search: 詳細を見る銘柄（一覧の行クリックでも開けます）", ["—"] + names, index=0)

rows = event.selection.rows if (event and event.selection) else []
if rows:                                   # 一覧クリックを優先
    chosen = res.iloc[rows[0]]
elif pick != "—":                          # スマホ等はこちらで確実に選べる
    chosen = res.iloc[names.index(pick)]
else:
    chosen = None

if chosen is not None:
    if watch_enabled:                      # 公開スクリーナー上で★追加/解除（保存先=Sheets）
        is_w = chosen["ticker"] in watched
        label = "★ ウォッチ解除" if is_w else "★ ウォッチに追加"
        if st.button(label, key=f"wt_{chosen['ticker']}", icon=":material/star:"):
            if is_w:
                new = watch_df[watch_df["ticker"] != chosen["ticker"]]
            else:
                add = pd.DataFrame([{"ticker": chosen["ticker"], "target_price": None, "memo": ""}])
                new = pd.concat([watch_df, add], ignore_index=True)
            _save_watch(new)
            st.rerun()
    render_detail(chosen)
else:
    st.info(
        "一覧の行をクリック、または上のボックスで銘柄を選ぶと、ここに詳細（移した指標＋数年分の財務＋株価チャート）が表示されます。",
        icon=":material/touch_app:",
    )
