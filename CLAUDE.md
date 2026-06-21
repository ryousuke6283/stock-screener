# CLAUDE.md — 日本株・米国株スクリーナー

このリポジトリで作業するClaude向けのプロジェクト説明書。**まずこれを読めば全体像がつかめます。**

## これは何か

日経225（223銘柄）＋ S&P500（503銘柄）＝計約726銘柄を yfinance で取得し、
**バリュー / グロース / クオリティ / モメンタム** のスタイル別にスクリーニングする
Streamlit Webダッシュボード。スマホ・PCどちらからでも見られる。

- **公開アプリ**: https://stock-screener-hfomupdqkfl9aexgiqw9vm.streamlit.app
- **GitHub**: https://github.com/ryousuke6283/stock-screener （Public）

## 🔄 同期プロトコル（Claudeは毎回これを自動で守ること）

このプロジェクトは **PC・スマホ・クラウドの複数環境**から触られる。
ユーザーは同期作業を覚えていないので、**Claude側が自動で面倒を見ること。**

1. **作業を始める前に必ず**: `git pull --ff-only origin main` を実行して最新化する。
   - もし fast-forward できない（履歴が分岐した）場合は、勝手にマージせず**ユーザーに状況を報告**する。
2. **変更を1つ仕上げるたびに**: `git add -A && git commit && git push origin main` まで実行する。
   - 「コミットしたけど push していない」状態でセッションを終えない。
3. セッションの最後に、**未push の変更が残っていないか確認**し、あれば push する。

→ これにより、ユーザーは「pushし忘れ/pullし忘れ」を一切気にしなくてよい。

## アーキテクチャ（重要）

「ローカルDBを毎回ネット取得」ではなく、**スナップショット運用**で速くしている：

```
GitHub Actions（毎日07:00 JST）─▶ data.parquet を更新してcommit/push
                                          │
Streamlit Cloud がそれを読むだけ ◀────────┘   → 表示が一瞬
```

- データは `data.parquet`（約150KB）に保存。アプリはこれを読むだけなので軽い。
- 毎回 yfinance を叩くのは遅いので**しない**。データ更新は Actions 側の責務。

## 構成（2ページ: スクリーナー + ポートフォリオ）

`st.navigation` で2ページ。共有処理は `lib/` に抽出済み。

| ファイル | 役割 |
|---|---|
| `app.py` | エントリ。`set_page_config` + `inject_css()` + `st.navigation` で2ページを束ねる |
| `pages_screener.py` | スクリーナー画面（プリセット＋スライダー＋詳細パネル）。**スクリーナーUIの変更はここ** |
| `pages_portfolio.py` | マイポートフォリオ（パスワード保護・Google Sheets・損益）。後述 |
| `lib/common.py` | 共有: `load_data` / `usdjpy_rate` / `inject_css` / `disp_name` / `fmt` / `compact` / 辞書類 |
| `lib/portfolio.py` | 損益計算の純粋関数（`compute_positions` / `summarize`）。テスト容易 |
| `lib/prices.py` | 保有株の現在値取得（yfinance `fast_info`、キーは `lastPrice`）|
| `lib/store.py` | Google Sheets 保存層（gspread）。`read_banks/write_banks`・`read_holdings/write_holdings` |
| `fetch_data.py` | 全銘柄の指標を yfinance で取得 → `data.parquet`（並列＋リトライ） |
| `fetch_tickers.py` | 日経225+S&P500の銘柄リスト取得 → `tickers.csv` |
| `data.parquet` | スクリーニング用データ（GitHub Actionsが毎日自動更新） |
| `test_app.py` | スクリーナーの AppTest（`AppTest.from_file("pages_screener.py")`） |
| `tests/test_portfolio*.py` | 損益計算とポートフォリオページのテスト（storeをモック） |
| `.github/workflows/refresh.yml` | データ自動更新ジョブ（cron + 手動 workflow_dispatch） |

## マイポートフォリオ（pages_portfolio.py）

- パスワード保護（`st.secrets["PORTFOLIO_PASSWORD"]`）。スクリーナーは公開のまま。
- データは **Google Sheets** に保存（`lib/store.py`）。`cash` タブ=銀行ごとの預金（bank, amount_jpy）、
  `holdings` タブ=保有株（ticker, shares, avg_cost, fx_cost）。
- **必要な st.secrets**: `PORTFOLIO_PASSWORD` / `PORTFOLIO_SHEET_ID` / `[gcp_service_account]`（鍵JSON）。
  ローカルは `.streamlit/secrets.toml`（**gitignore済・絶対コミットしない**）、本番は Streamlit Cloud の Secrets。
- 現在値は yfinance で都度取得、米国株は `fx_cost`（取得時1ドル=円）で原価を円換算（評価額は現在レート）。
- 保有株/預金の編集は `st.data_editor`。**保存ごとに editor の key をバージョン更新**して編集詰まりを回避している。

## よくある変更のやり方

- **スクリーナーの見た目/UI** → `pages_screener.py` を編集して push。Streamlit Cloudが自動再デプロイ（数分）。
- **共通のCSS/テーマ** → `lib/common.py` の `inject_css()`。
- **プリセット条件** → `pages_screener.py` の `PRESETS` 辞書。
- **取得する指標の追加** → `fetch_data.py` の `INFO_FIELDS` に yfinance の info キーを追加 → 再取得が必要。
- **変更後は必ず**テストを通してから push: `python test_app.py` と `python tests/test_portfolio.py` / `python tests/test_portfolio_page.py`。

## データの単位（ハマりどころ）

- `dividend_yield` … **すでに % 表記**（例: 3.51 = 3.51%）
- `roe` / `revenue_growth` / `earnings_growth` … **小数**（0.10 = 10%）。app.py側で `*100` して表示している。
- `pct_vs_ma50` / `pct_vs_ma200` / `pct_from_52w_high` … 計算済みの**乖離率(%)**。

## 開発時の注意

- **Streamlit Cloud の Python は 3.13 を使うこと**（3.14だと pyarrow/pandas のwheelが無く、ビルドが固まる）。アプリ Settings → Python version で設定済み。
- `requirements.txt` のバージョンは 3.13 で動作確認済み。むやみに上げない。
- データを再取得するとき: `python fetch_data.py`（全726銘柄で約1分）。`--limit N` で少数テスト可。
- ローカルでアプリ確認: `streamlit run app.py` → http://localhost:8501

## 開発予定・TODO（2026-06-21時点）

- マイポートフォリオ（MVP）を本番公開済み。
- ⚠️ **secretsローテーション推奨**: 設計中にサービスアカウント鍵JSONと合言葉が会話に露出したため、
  Google Cloudで鍵を作り直し＋`PORTFOLIO_PASSWORD`変更を未実施なら行う（ローカルとCloud両方のSecrets更新）。
- 構想中の他機能: アラート（価格到達で通知）、メタトレンド分析、主要ニュース。
  いずれも brainstorming → spec → plan の順で1つずつ（specは `docs/superpowers/specs/`）。
