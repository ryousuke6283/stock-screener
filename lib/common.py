# -*- coding: utf-8 -*-
import pandas as pd
import streamlit as st
from pathlib import Path

HERE = Path(__file__).parent.parent
DATA = HERE / "data.parquet"

# セクターの日本語表記（日本株=yfinance系 と 米国株=GICS系 で表記が違うので両方を同じ和名に統一）
SECTOR_JP = {
    "Information Technology": "情報技術", "Technology": "情報技術",
    "Health Care": "ヘルスケア", "Healthcare": "ヘルスケア",
    "Financials": "金融", "Financial Services": "金融",
    "Consumer Discretionary": "一般消費財", "Consumer Cyclical": "一般消費財",
    "Consumer Staples": "生活必需品", "Consumer Defensive": "生活必需品",
    "Industrials": "資本財・サービス",
    "Energy": "エネルギー",
    "Materials": "素材", "Basic Materials": "素材",
    "Utilities": "公益事業",
    "Real Estate": "不動産",
    "Communication Services": "コミュニケーション",
}

# 米国主要銘柄のカタカナ名（辞書に無い銘柄は英語名のまま表示）
US_NAME_JP = {
    "AAPL": "アップル", "MSFT": "マイクロソフト", "NVDA": "エヌビディア",
    "AMZN": "アマゾン", "GOOGL": "アルファベット", "GOOG": "アルファベット",
    "META": "メタ・プラットフォームズ", "TSLA": "テスラ", "BRK-B": "バークシャー・ハサウェイ",
    "AVGO": "ブロードコム", "JPM": "JPモルガン・チェース", "V": "ビザ", "MA": "マスターカード",
    "UNH": "ユナイテッドヘルス", "XOM": "エクソンモービル", "JNJ": "ジョンソン&ジョンソン",
    "PG": "P&G", "HD": "ホーム・デポ", "COST": "コストコ", "MRK": "メルク", "ABBV": "アッヴィ",
    "CVX": "シェブロン", "PEP": "ペプシコ", "KO": "コカ・コーラ", "ADBE": "アドビ",
    "WMT": "ウォルマート", "CRM": "セールスフォース", "BAC": "バンク・オブ・アメリカ",
    "MCD": "マクドナルド", "NFLX": "ネットフリックス", "AMD": "AMD", "LIN": "リンデ",
    "TMO": "サーモフィッシャー", "ACN": "アクセンチュア", "CSCO": "シスコシステムズ",
    "ABT": "アボット", "DHR": "ダナハー", "INTC": "インテル", "QCOM": "クアルコム",
    "TXN": "テキサス・インスツルメンツ", "INTU": "インテュイット", "IBM": "IBM",
    "PM": "フィリップ・モリス", "CAT": "キャタピラー", "VZ": "ベライゾン",
    "DIS": "ウォルト・ディズニー", "NKE": "ナイキ", "PFE": "ファイザー", "AMGN": "アムジェン",
    "NOW": "サービスナウ", "UNP": "ユニオン・パシフィック", "GS": "ゴールドマン・サックス",
    "HON": "ハネウェル", "RTX": "RTX", "SPGI": "S&Pグローバル", "LOW": "ロウズ",
    "ISRG": "インテュイティブ・サージカル", "BKNG": "ブッキング", "AXP": "アメリカン・エキスプレス",
    "T": "AT&T", "ELV": "エレバンス・ヘルス", "PLD": "プロロジス", "BLK": "ブラックロック",
    "SYK": "ストライカー", "MDT": "メドトロニック", "GILD": "ギリアド・サイエンシズ",
    "ADP": "ADP", "TJX": "TJX", "VRTX": "バーテックス", "C": "シティグループ",
    "MMC": "マーシュ・マクレナン", "CB": "チャブ", "BSX": "ボストン・サイエンティフィック",
    "MO": "アルトリア", "SO": "サザン", "ZTS": "ゾエティス", "CI": "シグナ",
    "PGR": "プログレッシブ", "FI": "ファイサーブ", "BA": "ボーイング", "DE": "ディア",
    "MU": "マイクロン", "LMT": "ロッキード・マーチン", "WFC": "ウェルズ・ファーゴ",
    "KLAC": "KLA", "PANW": "パロアルトネットワークス", "SBUX": "スターバックス",
    "MDLZ": "モンデリーズ", "AMAT": "アプライド・マテリアルズ", "ADI": "アナログ・デバイセズ",
    "REGN": "リジェネロン", "ORCL": "オラクル", "F": "フォード", "GM": "ゼネラルモーターズ",
    "UPS": "UPS", "PYPL": "ペイパル", "UBER": "ウーバー", "ABNB": "エアビーアンドビー",
    "MS": "モルガン・スタンレー", "GE": "GEエアロスペース", "WM": "ウェイスト・マネジメント",
}

# ブランドロゴ（Lucide candlestick-chart / currentColorでモノトーン追従）
LOGO_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M9 5v4"/><rect width="4" height="6" x="7" y="9" rx="1"/><path d="M9 15v2"/>'
    '<path d="M17 3v2"/><rect width="4" height="8" x="15" y="5" rx="1"/><path d="M17 13v3"/>'
    '<path d="M3 3v18h18"/></svg>'
)


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
        .stApp, [data-testid="stSidebar"] { font-size:12px; }
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li { font-size:12px; }
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

        /* === ボタン: 楕円ピル形 + 縦横サイズ統一 (全幅・最小高さ・中央寄せ) === */
        .stButton > button, [data-testid="stDownloadButton"] > button {
          background:#fff; color:var(--text);
          border:1px solid var(--border); border-radius:var(--radius-pill);
          font-size:12.5px; font-weight:500; box-shadow:none; padding:7px 14px;
          transition:background .12s, border-color .12s;
          width:100%; min-height:40px;
          display:inline-flex; align-items:center; justify-content:center; gap:7px;
          white-space:nowrap;
        }
        /* ボタン内のアイコンサイズを揃える */
        .stButton > button [data-testid="stIconMaterial"],
        [data-testid="stDownloadButton"] > button [data-testid="stIconMaterial"] {
          font-size:16px; line-height:1;
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
        [data-testid="stCaptionContainer"] { color:var(--text-soft); font-size:11.5px; }

        /* === ブランド（サイドバー見出し）: ロゴ+ワードマーク === */
        .brand {
          display:flex; align-items:center; gap:9px;
          font-size:17px; font-weight:700; letter-spacing:-0.03em;
          color:#09090b; margin:0 0 10px;
        }
        .brand svg { width:21px; height:21px; flex-shrink:0; color:var(--primary); }

        /* === ヒーロー（メイン見出し）: kicker + ロゴ + サブ + 下ヘアライン === */
        .hero { margin:0 0 16px; padding-bottom:14px; border-bottom:1px solid var(--border); }
        .hero-kicker {
          font-size:10.5px; font-weight:700; letter-spacing:0.22em;
          text-transform:uppercase; color:var(--text-soft);
        }
        .hero-title {
          display:flex; align-items:center; gap:10px; margin-top:5px;
          font-size:20px; font-weight:700; letter-spacing:-0.03em; color:#09090b;
          line-height:1.2;
        }
        .hero-title svg { width:22px; height:22px; flex-shrink:0; color:var(--primary); }
        .hero-sub { margin-top:6px; font-size:12px; color:var(--text-soft); }
        .dim { color:var(--text-soft); font-weight:400; font-size:13px; }

        /* === 詳細の指標グリッド: PC=4列 / スマホ=2列（間延び防止）=== */
        .metric-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:8px 0 4px; }
        .metric-grid .m { background:#fafafa; border:1px solid var(--border); border-radius:12px; padding:9px 12px; }
        .metric-grid .m-l { font-size:11px; color:var(--text-soft); margin-bottom:2px; }
        .metric-grid .m-v { font-size:16px; font-weight:700; color:#09090b; letter-spacing:-0.02em; }
        @media (max-width:640px) { .metric-grid { grid-template-columns:repeat(2,1fr); } }

        /* === メイン領域のドロップダウン等が横に伸びすぎないよう上限 === */
        section[data-testid="stMain"] [data-baseweb="select"] { max-width:460px; }

        /* === 余白を締める & Streamlit既定の装飾を控えめに === */
        .block-container { padding-top:2rem; }
        #MainMenu, footer, [data-testid="stDecoration"] { visibility:hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------- データ読み込み ----------------
@st.cache_data(ttl=60 * 60)
def usdjpy_rate() -> float:
    """USD/JPY（1ドル=何円）。時価総額をUSDに揃えて日米を比較可能にするため。"""
    import yfinance as yf
    try:
        r = yf.Ticker("JPY=X").fast_info["last_price"]
        if r and r > 50:
            return float(r)
    except Exception:
        pass
    return 155.0  # 取得失敗時のフォールバック


@st.cache_data(ttl=60 * 30)
def load_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA)
    # 表示用に % へ変換した派生列
    df["roe_pct"] = df["roe"] * 100
    df["roa_pct"] = df["roa"] * 100
    df["rev_growth_pct"] = df["revenue_growth"] * 100
    df["earn_growth_pct"] = df["earnings_growth"] * 100
    df["sector_jp"] = df["sector"].map(SECTOR_JP).fillna(df["sector"])
    # 時価総額をUSDに統一（日本株は円→ドル換算）して日米を同じ土俵で比較
    rate = usdjpy_rate()
    df["market_cap_usd"] = df["market_cap"].where(df["market"].eq("US"), df["market_cap"] / rate)
    return df


# ---------------- 詳細パネル用ヘルパー ----------------
def disp_name(ticker: str, name: str, market: str) -> str:
    """米国株は辞書にあればカタカナ、無ければ英語名。日本株はそのまま。"""
    return US_NAME_JP.get(ticker, name) if market == "US" else name


def fmt(v, p: int = 2, suf: str = "") -> str:
    return "—" if pd.isna(v) else f"{v:.{p}f}{suf}"


def compact(v) -> str:
    if pd.isna(v):
        return "—"
    for unit, d in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if abs(v) >= d:
            return f"{v / d:.1f}{unit}"
    return f"{v:.0f}"


# ---------------- 投資信託エイリアス（連動ETFで概算） ----------------
# 入力ティッカー(別名) -> (価格取得に使う連動ETF, 表示名)
FUND_ALIAS = {
    "楽天VTI": ("VTI", "楽天VTI（≈VTI）"),
    "VTI投信": ("VTI", "楽天VTI（≈VTI）"),
    "SP500": ("VOO", "S&P500投信（≈VOO）"),
    "S&P500": ("VOO", "S&P500投信（≈VOO）"),
    "オルカン": ("ACWI", "オルカン（≈ACWI）"),
    "全世界": ("ACWI", "オルカン（≈ACWI）"),
    "ナスダック": ("QQQ", "NASDAQ100（≈QQQ）"),
    "NASDAQ100": ("QQQ", "NASDAQ100（≈QQQ）"),
}


def _norm_alias(s) -> str:
    return str(s).strip().upper().replace(" ", "").replace("　", "")


_FUND_LOOKUP = {_norm_alias(k): v for k, v in FUND_ALIAS.items()}


def fund_info(ticker):
    """ファンド別名なら (連動ETF, 表示名)、違えば None。"""
    return _FUND_LOOKUP.get(_norm_alias(ticker))


def quote_ticker(ticker: str) -> str:
    """価格取得に使うティッカー（ファンドは連動ETFに置換）。"""
    fi = fund_info(ticker)
    return fi[0] if fi else str(ticker).strip()


@st.cache_data(ttl=60 * 30)
def ticker_name_map() -> dict:
    """スクリーニング対象(225/500)の ticker -> 表示名（JP=日本語 / US=カタカナ優先）。"""
    df = load_data()
    out = {}
    for _, r in df.iterrows():
        if r["market"] == "US":
            out[r["ticker"]] = US_NAME_JP.get(r["ticker"], r["name"])
        else:
            out[r["ticker"]] = r["name"]
    return out


def resolve_name(ticker: str) -> str:
    """銘柄名を解決: ファンド名 → 対象銘柄名 → 既知カタカナ → ティッカーそのまま。"""
    tk = str(ticker).strip()
    fi = fund_info(tk)
    if fi:
        return fi[1]
    nm = ticker_name_map().get(tk)
    if nm:
        return nm
    return US_NAME_JP.get(tk, tk)
