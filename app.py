# -*- coding: utf-8 -*-
"""
日本株・米国株スクリーニング ダッシュボード (Streamlit)

実行:  streamlit run app.py
data.parquet を読み込み、スライダー/プリセットで絞り込む。
"""
from pathlib import Path

import pandas as pd
import streamlit as st

HERE = Path(__file__).parent
DATA = HERE / "data.parquet"

st.set_page_config(page_title="株スクリーナー", page_icon="📊", layout="wide")


# ---------------- デザイン: kintai-css (BICEPSモノトーン業務SaaS) を翻訳適用 ----------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;600;700&display=swap');

        :root {
          --primary:#18181b; --primary-dark:#09090b;
          --border:#d4d4d8; --border-subtle:#e4e4e7; --muted:#f4f4f5;
          --text:#1e293b; --text-soft:#64748b; --info:#2563eb;
          --radius:18px; --radius-sm:10px; --radius-pill:999px;
        }

        /* === タイポ: Inter + Noto Sans JP、全体的に小さめ === */
        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
        button, input, select, textarea, [data-testid="stMarkdownContainer"] {
          font-family:"Inter","Noto Sans JP","Hiragino Kaku Gothic ProN","Yu Gothic","Meiryo",sans-serif !important;
          letter-spacing:-0.005em;
          font-feature-settings:"palt";
        }
        .stApp { background:#fff; }
        .stApp, [data-testid="stSidebar"] { font-size:13px; }
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li { font-size:13px; }
        [data-testid="stWidgetLabel"] p, .stRadio label, .stSelectbox label {
          font-size:12px !important; color:var(--text-soft);
        }

        /* === 見出し: 小さめ + より黒く (黒の存在感を増す) === */
        h1 { font-size:21px !important; font-weight:700 !important; letter-spacing:-0.02em !important; color:#09090b !important; }
        h2 { font-size:16px !important; font-weight:600 !important; letter-spacing:-0.015em !important; color:#09090b !important; }
        h3 { font-size:13px !important; font-weight:600 !important; color:#18181b !important; }

        /* === サイドバー: 薄グレーのパネル + ヘアライン (灰色を足す) === */
        [data-testid="stSidebar"] {
          background:#f7f7f8;
          border-right:1px solid var(--border);
        }

        /* === ボタン: 楕円ピル形 (白+細枠, ホバーで濃いグレー枠) === */
        .stButton > button, [data-testid="stDownloadButton"] > button {
          background:#fff; color:var(--text);
          border:1px solid var(--border); border-radius:var(--radius-pill);
          font-size:12.5px; font-weight:500; box-shadow:none; padding:6px 14px;
          transition:background .12s, border-color .12s;
        }
        .stButton > button:hover, [data-testid="stDownloadButton"] > button:hover {
          background:var(--muted); border-color:#a1a1aa; color:#09090b;
        }
        .stButton > button:focus:not(:active) { box-shadow:0 0 0 3px rgba(15,23,42,.12); }

        /* === metric: 丸いグレーのカード (灰色を足す + 角丸を強く) === */
        [data-testid="stMetric"] {
          background:#fafafa; border:1px solid var(--border);
          border-radius:var(--radius); padding:12px 16px;
        }
        [data-testid="stMetricLabel"] p { color:var(--text-soft); font-size:12px; }
        [data-testid="stMetricValue"] { font-size:1.5rem !important; font-weight:700; color:#09090b; }

        /* === dataframe: 丸いヘアライン枠 === */
        [data-testid="stDataFrame"] {
          border:1px solid var(--border); border-radius:var(--radius); overflow:hidden;
        }

        /* === 入力/セレクト: 角丸 === */
        [data-baseweb="select"] > div, .stTextInput input, .stNumberInput input {
          border-radius:var(--radius-sm) !important;
        }

        /* === キャプション/補助テキストは小さく muted === */
        [data-testid="stCaptionContainer"] { color:var(--text-soft); font-size:12px; }

        /* === 余白を締める & Streamlit既定の装飾を控えめに === */
        .block-container { padding-top:2rem; }
        #MainMenu, footer, [data-testid="stDecoration"] { visibility:hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()


# ---------------- データ読み込み ----------------
@st.cache_data(ttl=60 * 30)
def load_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA)
    # 表示用に % へ変換した派生列
    df["roe_pct"] = df["roe"] * 100
    df["roa_pct"] = df["roa"] * 100
    df["rev_growth_pct"] = df["revenue_growth"] * 100
    df["earn_growth_pct"] = df["earnings_growth"] * 100
    return df


df = load_data()
fetched = pd.to_datetime(df["fetched_at"].iloc[0]).tz_convert("Asia/Tokyo")

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

# session_state 初期化
for key in OFF:
    st.session_state.setdefault(key, OFF[key])


def apply_preset(cfg: dict):
    for key in OFF:                       # まず全部OFFに戻す
        st.session_state[key] = OFF[key]
    for key, val in cfg.items():          # プリセット値を上書き
        st.session_state[key] = val


# ---------------- サイドバー ----------------
st.sidebar.title("📊 株スクリーナー")
st.sidebar.caption(f"データ更新: {fetched:%Y-%m-%d %H:%M} JST")

st.sidebar.subheader("スタイル別プリセット")
pcols = st.sidebar.columns(2)
for i, (name, cfg) in enumerate(PRESETS.items()):
    if pcols[i % 2].button(name, width="stretch"):
        apply_preset(cfg)
if st.sidebar.button("条件をリセット", width="stretch"):
    apply_preset({})

st.sidebar.divider()

# 市場
market = st.sidebar.radio("市場", ["両方", "日本株", "米国株"], horizontal=True)

# セクター
sectors = sorted(df["sector"].dropna().unique())
sel_sectors = st.sidebar.multiselect("セクター（空＝全部）", sectors, default=[])

st.sidebar.subheader("詳細条件")
for key, label, lo, hi, step, kind, col in SLIDERS:
    st.sidebar.slider(label, lo, hi, step=step, key=key)

# ---------------- 絞り込み ----------------
mask = pd.Series(True, index=df.index)

if market == "日本株":
    mask &= df["market"].eq("JP")
elif market == "米国株":
    mask &= df["market"].eq("US")

if sel_sectors:
    mask &= df["sector"].isin(sel_sectors)

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
st.title("日本株・米国株 スクリーニング")

m1, m2, m3 = st.columns(3)
m1.metric("該当銘柄", f"{len(res)} 件")
m2.metric("日本株", int((res['market'] == 'JP').sum()))
m3.metric("米国株", int((res['market'] == 'US').sum()))

if active_filters:
    st.caption("適用中の数値条件: " + " / ".join(active_filters))
else:
    st.caption("数値条件なし（市場・セクターのみ）")

# 表示する列と日本語ヘッダ
DISPLAY = {
    "ticker": "コード", "name": "銘柄", "market": "市場", "sector": "セクター",
    "price": "株価", "currency": "通貨", "market_cap": "時価総額",
    "per": "PER", "pbr": "PBR", "psr": "PSR", "dividend_yield": "配当%",
    "roe_pct": "ROE%", "rev_growth_pct": "増収%", "earn_growth_pct": "増益%",
    "pct_vs_ma50": "50d乖離%", "pct_vs_ma200": "200d乖離%",
    "pct_from_52w_high": "52w高値比%",
}
view = res[list(DISPLAY)].rename(columns=DISPLAY)

# 並べ替え用デフォルト
sort_col = st.selectbox("並べ替え", list(DISPLAY.values()), index=list(DISPLAY.values()).index("配当%"))
ascending = st.toggle("昇順", value=False)
view = view.sort_values(sort_col, ascending=ascending, na_position="last")

st.dataframe(
    view,
    width="stretch",
    hide_index=True,
    height=620,
    column_config={
        "株価": st.column_config.NumberColumn(format="%.1f"),
        "時価総額": st.column_config.NumberColumn(format="compact"),
        "PER": st.column_config.NumberColumn(format="%.1f"),
        "PBR": st.column_config.NumberColumn(format="%.2f"),
        "PSR": st.column_config.NumberColumn(format="%.2f"),
        "配当%": st.column_config.NumberColumn(format="%.2f"),
        "ROE%": st.column_config.NumberColumn(format="%.1f"),
        "増収%": st.column_config.NumberColumn(format="%.1f"),
        "増益%": st.column_config.NumberColumn(format="%.1f"),
        "50d乖離%": st.column_config.NumberColumn(format="%.1f"),
        "200d乖離%": st.column_config.NumberColumn(format="%.1f"),
        "52w高値比%": st.column_config.NumberColumn(format="%.1f"),
    },
)

st.download_button(
    "この結果をCSVダウンロード",
    view.to_csv(index=False).encode("utf-8-sig"),
    file_name="screen_result.csv",
    mime="text/csv",
)
