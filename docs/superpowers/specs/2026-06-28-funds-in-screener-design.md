# 投信（連動ETF）をスクリーナーに追加 — 設計

- 日付: 2026-06-28
- 対象: スクリーナー（データ取得 + 表示）
- 機能4

## 目的

SP500 / オルカン / 楽天VTI / NASDAQ100 などの主要インデックス投信を、**連動ETFの指標**で
スクリーナー一覧に「投信」カテゴリとして混ぜて表示する。

## 対象ファンド（連動ETFで概算・ポートフォリオの FUND_ALIAS と整合）

| ticker(ETF) | 表示名 | 連動先 |
|---|---|---|
| `VOO` | S&P500（VOO） | S&P500 |
| `VTI` | 全米株式（楽天VTI≈VTI） | 全米株式 |
| `ACWI` | 全世界株式（オルカン≈ACWI） | 全世界株 |
| `QQQ` | NASDAQ100（QQQ） | NASDAQ100 |

## データ取得（fetch_data.py）

ETF は個別株と yfinance の返りが違う（実測）:
- `currentPrice` = None → **`regularMarketPrice` → `previousClose`** をフォールバック
- `marketCap` = None → **`totalAssets`（純資産）** をフォールバック
- `netExpenseRatio` = 経費率（**% 表記**: VOO=0.03 等）→ 新カラム `expense_ratio`
- `sector` = None → tickers.csv 側で `インデックス投信` を付与（CSV優先ロジックで採用）

`ok` 判定は従来どおり「price が取れたか」。フォールバック後に price が入るので ETF も ok=True。

## 銘柄リスト

- `tickers.csv` に4ファンド行を追加（`market=FUND` / `index_=投信` / `sector=インデックス投信`）。
- `fetch_tickers.py` にも `FUNDS` 定数を持たせ、Wikipedia 再取得後も投信が残るようにする。

## 表示（lib/common.py / pages_screener.py）

- `load_data`: `market_cap_usd` は **JP のみ円→ドル換算**に変更（US と FUND は USD のまま）。
- スクリーナー:
  - 市場ラジオに **「投信」** を追加（`両方` には自然に含まれる）。
  - 市場ラベル `{JP:日本, US:米国, FUND:投信}`。
  - メトリクスに **投信の件数**を追加。
  - 行の淡い色分けに FUND を追加。
  - 詳細パネル: ファンドのとき **経費率** を指標グリッドに表示。
- 投信は PER/PBR/ROE 等が無い → `fmt` が `—` 表示。株価・移動平均乖離・52週高値比・経費率が中心。

## データ更新

- 当面の `data.parquet` は既存726行を保ったまま **4ファンド行を追記**（今日の株価データを退行させない）。
- 以降は GitHub Actions の日次フル取得が `tickers.csv` 経由で投信も含めて更新。

## テスト

- `tests/test_fund_rows.py`（pandas のみ・streamlit非依存）: `data.parquet` に4ファンドが
  `market==FUND` で存在し、price が非NaN・market_cap_usd 換算が二重割りされていないことを確認。
- 既存テスト（test_app 等）が壊れないこと。
