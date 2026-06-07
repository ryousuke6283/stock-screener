# CLAUDE.md — 日本株・米国株スクリーナー

このリポジトリで作業するClaude向けのプロジェクト説明書。**まずこれを読めば全体像がつかめます。**

## これは何か

日経225（223銘柄）＋ S&P500（503銘柄）＝計約726銘柄を yfinance で取得し、
**バリュー / グロース / クオリティ / モメンタム** のスタイル別にスクリーニングする
Streamlit Webダッシュボード。スマホ・PCどちらからでも見られる。

- **公開アプリ**: https://stock-screener-hfomupdqkfl9aexgiqw9vm.streamlit.app
- **GitHub**: https://github.com/ryousuke6283/stock-screener （Public）

## アーキテクチャ（重要）

「ローカルDBを毎回ネット取得」ではなく、**スナップショット運用**で速くしている：

```
GitHub Actions（毎日07:00 JST）─▶ data.parquet を更新してcommit/push
                                          │
Streamlit Cloud がそれを読むだけ ◀────────┘   → 表示が一瞬
```

- データは `data.parquet`（約150KB）に保存。アプリはこれを読むだけなので軽い。
- 毎回 yfinance を叩くのは遅いので**しない**。データ更新は Actions 側の責務。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `app.py` | Streamlitダッシュボード本体。プリセットボタン＋スライダーで絞り込み |
| `fetch_data.py` | 全銘柄の指標を yfinance で取得 → `data.parquet`（並列＋リトライ） |
| `fetch_tickers.py` | 日経225+S&P500の銘柄リスト取得 → `tickers.csv` |
| `data.parquet` | スクリーニング用データ（GitHub Actionsが毎日自動更新） |
| `tickers.csv` | 対象銘柄リスト |
| `test_app.py` | ダッシュボードの自動テスト（Streamlit AppTest） |
| `.github/workflows/refresh.yml` | データ自動更新ジョブ（cron + 手動 workflow_dispatch） |

## よくある変更のやり方

- **見た目/CSS/UIの変更** → `app.py` を編集して push。Streamlit Cloudが自動で再デプロイ（数分）。
- **プリセット条件の調整** → `app.py` の `PRESETS` 辞書を編集。
- **取得する指標の追加** → `fetch_data.py` の `INFO_FIELDS` に yfinance の info キーを追加 → 再取得が必要。
- **変更後は必ず**、ローカルで `python test_app.py` を通してから push すると安全。

## データの単位（ハマりどころ）

- `dividend_yield` … **すでに % 表記**（例: 3.51 = 3.51%）
- `roe` / `revenue_growth` / `earnings_growth` … **小数**（0.10 = 10%）。app.py側で `*100` して表示している。
- `pct_vs_ma50` / `pct_vs_ma200` / `pct_from_52w_high` … 計算済みの**乖離率(%)**。

## 開発時の注意

- **Streamlit Cloud の Python は 3.13 を使うこと**（3.14だと pyarrow/pandas のwheelが無く、ビルドが固まる）。アプリ Settings → Python version で設定済み。
- `requirements.txt` のバージョンは 3.13 で動作確認済み。むやみに上げない。
- データを再取得するとき: `python fetch_data.py`（全726銘柄で約1分）。`--limit N` で少数テスト可。
- ローカルでアプリ確認: `streamlit run app.py` → http://localhost:8501

## 次にやる予定（2026-06-07時点）

クラウド公開まで完了。**次フェーズは実機スマホを見ながらのCSS/見た目調整**（表の見やすさ、配色、指標の色付けヒートマップ等）。
