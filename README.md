# 📊 日本株・米国株スクリーナー

日経225 + S&P500（計約726銘柄）を yfinance で取得し、Streamlit ダッシュボードで
バリュー / グロース / クオリティ / モメンタムのスタイル別にスクリーニングする。

データは `data.parquet`（スナップショット）に保存し、ダッシュボードはそれを読むだけなので
表示が速い。データ更新は GitHub Actions が毎日自動で行う（手動実行も可）。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `app.py` | Streamlit ダッシュボード本体 |
| `fetch_data.py` | 全銘柄の指標を取得して `data.parquet` に保存 |
| `fetch_tickers.py` | 日経225 + S&P500 の銘柄リストを取得（`tickers.csv` / `stocks.db`）|
| `data.parquet` | スクリーニング用データ（GitHub Actions が自動更新）|
| `tickers.csv` | 対象銘柄リスト |
| `test_app.py` | ダッシュボードの自動テスト（AppTest）|
| `.github/workflows/refresh.yml` | 毎日のデータ自動更新ジョブ |

## ローカルで動かす

```powershell
pip install -r requirements.txt
python fetch_tickers.py      # 銘柄リスト作成（初回のみ / 構成変更時）
python fetch_data.py         # データ取得 → data.parquet
streamlit run app.py         # ダッシュボード起動
```

ブラウザで http://localhost:8501 を開く。同じ Wi-Fi のスマホからは
表示される Network URL（例: http://192.168.x.x:8501）でアクセスできる。

## クラウド公開（PCオフでもスマホで見る）

1. このリポジトリを GitHub に push
2. [share.streamlit.io](https://share.streamlit.io) でこのリポジトリ・`app.py` を指定してデプロイ
3. 発行された URL をスマホのホーム画面に追加すれば、いつでも閲覧可能

### データ更新

- **自動**: GitHub Actions が毎日 07:00 JST に `fetch_data.py` を実行し `data.parquet` を更新
- **手動**: GitHub の Actions タブ → 「Refresh stock data」→ 「Run workflow」（スマホのブラウザからも実行可）

データが更新されると Streamlit Cloud が自動で再デプロイし、最新が反映される。

## 注意

- yfinance は Yahoo Finance の非公式データ。欠損や遅延がありうる（投資判断は自己責任で）。
- 配当利回りは `%` 表記、ROE・増収率などは小数を `%` 換算して表示している。
