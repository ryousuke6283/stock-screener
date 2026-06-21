# マイポートフォリオ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 株スクリーナーに、現預金＋保有株の評価損益をクラウド同期で管理する「マイポートフォリオ」ページ（パスワード保護）を追加する。

**Architecture:** 既存の単一 `app.py` を `st.navigation` の2ページ構成へ分割（共有処理は `lib/` に抽出）。スクリーナーは公開のまま、ポートフォリオは簡易パスワードで保護。データは Google Sheets（gspread）に保存し、現在値は yfinance で都度取得、USDJPY 換算で¥合算。

**Tech Stack:** Streamlit 1.58 / pandas / yfinance / gspread + google-auth / Google Sheets

**前提:** ユーザーは Google サービスアカウント鍵JSON（`~/Downloads/toushiapp-*.json`）と共有済みスプレッドシートを用意済み。設計書: `docs/superpowers/specs/2026-06-21-portfolio-design.md`。

**作業ブランチ:** `feat/portfolio`（本番=main の稼働中スクリーナーを壊さないため。MVP検証後に main へマージ＝公開）。

---

## Task 0: ブランチ作成と依存・パッケージ土台

**Files:**
- Create: `lib/__init__.py`
- Modify: `requirements.txt`

- [ ] **Step 1: 作業ブランチを作成**

```bash
cd /c/Users/81909/dev/stock-screener
git checkout -b feat/portfolio
```

- [ ] **Step 2: lib パッケージを作る**

`lib/__init__.py` を空ファイルで作成。

- [ ] **Step 3: 依存を追加**

`requirements.txt` の末尾に2行追加:

```
gspread==6.1.4
google-auth==2.35.0
```

- [ ] **Step 4: ローカルにインストール**

Run: `pip install gspread==6.1.4 google-auth==2.35.0`
Expected: `Successfully installed ...`

- [ ] **Step 5: Commit**

```bash
git add lib/__init__.py requirements.txt
git commit -m "chore: feat/portfolio用にlib土台とgspread/google-auth依存を追加"
```

---

## Task 1: 共有処理を lib/common.py に抽出し、2ページ構成へ移行（スクリーナーは無変更で動くこと）

**Files:**
- Create: `lib/common.py`
- Create: `pages_screener.py`
- Modify: `app.py`
- Modify: `test_app.py`

- [ ] **Step 1: lib/common.py を作成し、app.py から共有定義を“移動”**

`app.py` から次の定義を**そのまま切り取って** `lib/common.py` に貼り、先頭に `import pandas as pd` と `import streamlit as st` を付ける:
`SECTOR_JP`, `US_NAME_JP`, `LOGO_SVG`, `inject_css`(関数), `usdjpy_rate`(関数), `load_data`(関数), `disp_name`(関数), `fmt`(関数), `compact`(関数)。

（これらはスクリーナーとポートフォリオの両方で使う共有部品。`load_data`/`usdjpy_rate` は `@st.cache_data` デコレータごと移動。）

- [ ] **Step 2: pages_screener.py を作成し、スクリーナー本体を移動**

`app.py` の `st.set_page_config(...)` と `inject_css()` 呼び出しを**除いた**スクリーナー画面の全ロジック（SLIDERS〜詳細パネル〜CSVダウンロード、`render_detail`/`fetch_income`/`fetch_price`/`PERIODS`/`build_financials_table`/`_BAR_GRAY`/`PRESETS`/`PRESET_ICONS` 等）を `pages_screener.py` に移動。先頭に追加:

```python
# -*- coding: utf-8 -*-
import pandas as pd
import streamlit as st
from lib.common import (
    SECTOR_JP, US_NAME_JP, LOGO_SVG, usdjpy_rate, load_data,
    disp_name, fmt, compact,
)
```

- [ ] **Step 3: app.py をナビ・エントリに置き換え**

`app.py` を以下の全文に:

```python
# -*- coding: utf-8 -*-
"""日本株・米国株スクリーナー + マイポートフォリオ（エントリ/ナビ）"""
import streamlit as st
from lib.common import inject_css

st.set_page_config(page_title="株スクリーナー", page_icon=":material/candlestick_chart:", layout="wide")
inject_css()  # 全ページ共通でモノトーンCSSを適用

screener = st.Page("pages_screener.py", title="スクリーナー", icon=":material/candlestick_chart:", default=True)
portfolio = st.Page("pages_portfolio.py", title="ポートフォリオ", icon=":material/account_balance_wallet:")
st.navigation([screener, portfolio]).run()
```

- [ ] **Step 4: 仮の pages_portfolio.py を作成（ナビ成立用の最小）**

```python
# -*- coding: utf-8 -*-
import streamlit as st
st.title(":material/account_balance_wallet: マイポートフォリオ")
st.info("準備中…")
```

- [ ] **Step 5: test_app.py をスクリーナーページ対象に更新**

`test_app.py` 内の `AppTest.from_file("app.py")` を **すべて** `AppTest.from_file("pages_screener.py")` に置換（2箇所）。

- [ ] **Step 6: スクリーナーのテストが通ることを確認**

Run: `python test_app.py`
Expected: `OK: AppTest 全チェック通過`（初期726件 / バリュー / グロースが従来どおり）

- [ ] **Step 7: ローカルでアプリ起動して2ページ表示を目視**

Run: `python -m streamlit run app.py --server.headless true` を起動 → ログに `Local URL` が出れば停止。エラーが無いこと（ナビにスクリーナー/ポートフォリオの2項目）。

- [ ] **Step 8: Commit**

```bash
git add lib/common.py pages_screener.py pages_portfolio.py app.py test_app.py
git commit -m "refactor: 共有処理をlib/commonへ抽出し st.navigation の2ページ構成に移行"
```

---

## Task 2: 損益計算（純粋関数・TDD）

**Files:**
- Create: `lib/portfolio.py`
- Test: `tests/test_portfolio.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_portfolio.py`:

```python
# -*- coding: utf-8 -*-
import pandas as pd
from lib.portfolio import compute_positions, summarize


def main():
    holdings = pd.DataFrame([
        {"ticker": "7203.T", "shares": 100, "avg_cost": 2000.0},
        {"ticker": "AAPL", "shares": 10, "avg_cost": 150.0},
        {"ticker": "BAD", "shares": 5, "avg_cost": 10.0},
    ])
    prices = {
        "7203.T": {"price": 2850.0, "currency": "JPY"},
        "AAPL": {"price": 200.0, "currency": "USD"},
        # BAD は未収録 = 取得不可
    }
    usdjpy = 150.0
    pos = compute_positions(holdings, prices, usdjpy)

    t = pos[pos.ticker == "7203.T"].iloc[0]
    assert t.value_native == 285000.0
    assert t.cost_native == 200000.0
    assert t.pl_native == 85000.0
    assert abs(t.pl_pct - 42.5) < 1e-6
    assert t.value_jpy == 285000.0 and bool(t.jpy_ok)

    a = pos[pos.ticker == "AAPL"].iloc[0]
    assert a.currency == "USD"
    assert a.value_native == 2000.0
    assert a.value_jpy == 2000.0 * 150.0

    b = pos[pos.ticker == "BAD"].iloc[0]
    assert (not bool(b.ok)) and (not bool(b.jpy_ok))

    s = summarize(pos, cash_jpy=500000.0, usdjpy=usdjpy)
    assert abs(s["stock_jpy"] - (285000.0 + 300000.0)) < 1e-6
    assert abs(s["total_jpy"] - (285000.0 + 300000.0 + 500000.0)) < 1e-6
    # cost: 200000(JPY) + 150*10*150(USD→JPY)=225000 → 425000 ; pl=585000-425000=160000
    assert abs(s["pl_jpy"] - 160000.0) < 1e-6
    print("OK: test_portfolio passed")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python tests/test_portfolio.py`
Expected: FAIL（`ModuleNotFoundError: No module named 'lib.portfolio'`）

- [ ] **Step 3: lib/portfolio.py を実装**

```python
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
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python tests/test_portfolio.py`
Expected: `OK: test_portfolio passed`

- [ ] **Step 5: Commit**

```bash
git add lib/portfolio.py tests/test_portfolio.py
git commit -m "feat(portfolio): 損益計算の純粋関数 compute_positions/summarize をTDDで実装"
```

---

## Task 3: 現在値取得（yfinance）

**Files:**
- Create: `lib/prices.py`

- [ ] **Step 1: lib/prices.py を実装**

```python
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
            price = fi.get("last_price")
            cur = fi.get("currency")
            if price:
                out[tk] = {"price": float(price),
                           "currency": cur or ("JPY" if tk.endswith(".T") else "USD")}
            else:
                out[tk] = None
        except Exception:
            out[tk] = None
    return out
```

- [ ] **Step 2: 実データで動作確認**

Run:
```bash
python -c "from lib.prices import fetch_quotes; print(fetch_quotes(('7203.T','AAPL')))"
```
Expected: `{'7203.T': {'price': ..., 'currency': 'JPY'}, 'AAPL': {'price': ..., 'currency': 'USD'}}`（価格は数値）

- [ ] **Step 3: Commit**

```bash
git add lib/prices.py
git commit -m "feat(portfolio): 保有株の現在値取得 fetch_quotes を追加"
```

---

## Task 4: Google Sheets 保存層

**Files:**
- Create: `lib/store.py`

- [ ] **Step 1: lib/store.py を実装**

```python
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
```

- [ ] **Step 2: 構文チェック**

Run: `python -c "import ast; ast.parse(open('lib/store.py',encoding='utf-8').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add lib/store.py
git commit -m "feat(portfolio): Google Sheets保存層 store.py を追加"
```

---

## Task 5: シークレット設定（ユーザー伴走）

**Files:**
- Create: `.streamlit/secrets.toml`（**.gitignore 済み・コミットしない**）

- [ ] **Step 1: .gitignore を確認**

Run: `grep secrets .gitignore`
Expected: `.streamlit/secrets.toml` が含まれる（既存）。無ければ追記。

- [ ] **Step 2: ローカル secrets を作成（ユーザーの鍵JSONを取り込む）**

`~/Downloads/toushiapp-*.json` の中身を読み、`.streamlit/secrets.toml` に次の形で記入（**実装者がユーザーと一緒に**。鍵はチャットに表示しない）:

```toml
PORTFOLIO_PASSWORD = "（ユーザーが決める合言葉）"
PORTFOLIO_SHEET_ID = "（スプレッドシートURLの /d/<ここ>/）"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
universe_domain = "googleapis.com"
```

- [ ] **Step 3: 接続スモークテスト**

Run: `python -c "import streamlit as st" ` 後、ローカルで `streamlit run app.py` を起動し、ポートフォリオページで（Task 6実装後に）読み書きが通ることを確認。Task 5時点では `.streamlit/secrets.toml` の体裁確認のみ:
Run: `python -c "import tomllib;tomllib.load(open('.streamlit/secrets.toml','rb'));print('toml ok')"`
Expected: `toml ok`

- [ ] **Step 4: コミットしない（鍵のため）**

`git status` に `.streamlit/secrets.toml` が現れないこと（gitignore済み）を確認。Run: `git status --short`。Expected: secrets.toml が出ない。

---

## Task 6: ポートフォリオページ本体（認証＋UI＋配線）

**Files:**
- Modify: `pages_portfolio.py`（Task1の仮実装を本実装に置換）
- Test: `tests/test_portfolio_page.py`

- [ ] **Step 1: 失敗するスモークテストを書く（store/pricesをモック・認証バイパス）**

`tests/test_portfolio_page.py`:

```python
# -*- coding: utf-8 -*-
import pandas as pd
from streamlit.testing.v1 import AppTest


def _fake_modules():
    import sys, types
    store = types.ModuleType("lib.store")
    store.HOLD_COLS = ["ticker", "shares", "avg_cost"]
    store.read_cash = lambda: 500000.0
    store.write_cash = lambda a: None
    store.read_holdings = lambda: pd.DataFrame(
        [{"ticker": "7203.T", "shares": 100, "avg_cost": 2000.0},
         {"ticker": "AAPL", "shares": 10, "avg_cost": 150.0}])
    store.write_holdings = lambda df: None
    prices = types.ModuleType("lib.prices")
    prices.fetch_quotes = lambda tks: {
        "7203.T": {"price": 2850.0, "currency": "JPY"},
        "AAPL": {"price": 200.0, "currency": "USD"}}
    sys.modules["lib.store"] = store
    sys.modules["lib.prices"] = prices


def main():
    _fake_modules()
    at = AppTest.from_file("pages_portfolio.py", default_timeout=60)
    at.secrets["PORTFOLIO_PASSWORD"] = "x"
    at.session_state["pf_auth"] = True   # 認証済みにして本体を表示
    at.run()
    assert not at.exception, f"例外: {at.exception}"
    # サマリーに総資産メトリクスが出ている
    labels = [m.label for m in at.metric]
    assert any("総資産" in l for l in labels), labels
    print("OK: test_portfolio_page passed")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python tests/test_portfolio_page.py`
Expected: FAIL（まだ本体が仮実装＝総資産メトリクスが無い）

- [ ] **Step 3: pages_portfolio.py を本実装に置換**

```python
# -*- coding: utf-8 -*-
"""マイポートフォリオ（パスワード保護・Google Sheets・損益表示）"""
import pandas as pd
import streamlit as st

from lib.common import usdjpy_rate, disp_name, fmt, US_NAME_JP
from lib.portfolio import compute_positions, summarize
from lib import store, prices

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
    cash = store.read_cash()
    holdings = store.read_holdings()
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")
    st.stop()

rate = usdjpy_rate()
quotes = prices.fetch_quotes(tuple(holdings["ticker"])) if not holdings.empty else {}
pos = compute_positions(holdings, quotes, rate)
s = summarize(pos, cash, rate)

# ---- サマリー ----
def _yen(v):
    return "—" if pd.isna(v) else f"¥{v:,.0f}"

c = st.columns(4)
c[0].metric(":material/account_balance: 総資産", _yen(s["total_jpy"]))
c[1].metric(":material/trending_up: 評価損益", _yen(s["pl_jpy"]), f"{s['pl_pct']:+.1f}%")
c[2].metric(":material/savings: 現預金", _yen(s["cash_jpy"]))
c[3].metric(":material/show_chart: 株式評価額", _yen(s["stock_jpy"]))

st.divider()

# ---- 現預金の編集 ----
st.markdown("#### :material/savings: 現預金")
new_cash = st.number_input("現預金（円）", min_value=0.0, value=float(cash), step=10000.0, format="%.0f")
if st.button("現預金を保存", type="primary", icon=":material/save:"):
    store.write_cash(new_cash)
    st.success("保存しました。")
    st.rerun()

st.divider()

# ---- 保有株の編集 ----
st.markdown("#### :material/edit_note: 保有株を編集")
st.caption("行の追加・編集・削除ができます。ticker は 日本株=4桁+.T（例 7203.T）/ 米国株=シンボル（例 AAPL）")
edited = st.data_editor(
    holdings if not holdings.empty else pd.DataFrame(columns=store.HOLD_COLS),
    num_rows="dynamic",
    width="stretch",
    column_config={
        "ticker": st.column_config.TextColumn("ティッカー", required=True),
        "shares": st.column_config.NumberColumn("株数", min_value=0.0, step=1.0),
        "avg_cost": st.column_config.NumberColumn("平均取得単価", min_value=0.0),
    },
    key="pf_editor",
)
if st.button("保有株を保存", type="primary", icon=":material/save:"):
    store.write_holdings(edited)
    st.success("保存しました。")
    st.rerun()

st.divider()

# ---- 保有株テーブル（計算結果）----
st.markdown("#### :material/table_rows: 保有株（評価損益）")
if pos.empty:
    st.info("保有株がありません。上で追加してください。", icon=":material/info:")
else:
    view = pd.DataFrame({
        "銘柄": [disp_name(t, t, "US" if not t.endswith(".T") else "JP") for t in pos["ticker"]],
        "株数": pos["shares"],
        "取得単価": pos["avg_cost"],
        "現在値": pos["price"],
        "評価額(¥)": pos["value_jpy"],
        "損益(¥)": [v - c if (not pd.isna(v)) else float("nan")
                    for v, c in zip(pos["value_jpy"],
                                    [(_c * rate if cur == "USD" else _c) for _c, cur in
                                     zip(pos["cost_native"], pos["currency"])])],
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
```

- [ ] **Step 4: スモークテストが通ることを確認**

Run: `python tests/test_portfolio_page.py`
Expected: `OK: test_portfolio_page passed`

- [ ] **Step 5: スクリーナーのテストも回帰確認**

Run: `python test_app.py`
Expected: `OK: AppTest 全チェック通過`

- [ ] **Step 6: ローカル実機で確認（secrets実物が必要）**

`streamlit run app.py` → ポートフォリオページ → 合言葉ログイン → 現預金保存・保有株を1件追加保存 → Googleシートに反映され、評価損益が表示されることを目視。

- [ ] **Step 7: Commit**

```bash
git add pages_portfolio.py tests/test_portfolio_page.py
git commit -m "feat(portfolio): ポートフォリオページ(認証+現預金+保有株編集+損益表示)を実装"
```

---

## Task 7: デプロイ（Streamlit Cloud secrets 登録 → main へマージ → 公開）

**Files:** なし（運用作業）

- [ ] **Step 1: Streamlit Cloud に secrets を登録**

share.streamlit.io → 対象アプリ → Settings → Secrets に、`.streamlit/secrets.toml` と同じ内容（`PORTFOLIO_PASSWORD` / `PORTFOLIO_SHEET_ID` / `[gcp_service_account]`）を貼り付けて保存。

- [ ] **Step 2: ブランチを push してプレビュー（任意）**

```bash
git push -u origin feat/portfolio
```
（必要なら Streamlit Cloud のブランチを一時的に feat/portfolio に向けて実機確認）

- [ ] **Step 3: main にマージして公開**

```bash
git checkout main
git pull --ff-only
git merge --no-ff feat/portfolio -m "feat: マイポートフォリオ機能を追加"
git push origin main
```

- [ ] **Step 4: 公開アプリで最終確認**

スマホ・PCで `https://stock-screener-...streamlit.app` を開き、ポートフォリオページのログイン→保存→損益表示が動くことを確認。スクリーナーが従来どおり動くことも確認。

---

## Self-Review メモ（spec 対応）

- 2ページ構成/パスはポートフォリオのみ → Task1, Task6 ✓
- Google Sheets(cash/holdings) → Task4 ✓
- 任意銘柄の現在値取得 + USDJPY換算 → Task3, Task2 ✓
- st.data_editor 編集 → Task6 ✓
- モノトーン/黒ボタン(type="primary")/Materialアイコン積極活用 → Task6 ✓
- 取得失敗除外・空ポートフォリオ・通貨非対応の扱い → Task2/Task6 ✓
- store モックでの損益テスト → Task2, Task6 ✓
- 依存追加 gspread/google-auth → Task0 ✓
- ユーザー手作業(Google設定/secrets) → Task5（鍵は非コミット）✓
