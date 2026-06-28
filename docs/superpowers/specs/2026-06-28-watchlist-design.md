# ウォッチリスト ＋ 目標買値 ＋ 到達アラート — 設計

- 日付: 2026-06-28
- 対象: スクリーナー画面（公開ページ）
- 関連機能: 旧「買値メモ＋アラート」(機能2) と「ウォッチ機能＋先頭表示」(機能3) を1つに統合

## 目的

スクリーナーで気になった銘柄を **ウォッチ登録**し、各銘柄に **目標買値** と **メモ** を持たせる。
現在値が目標買値以下になったら **アプリ内で色強調（到達アラート）** する。ウォッチ銘柄は
一覧の最上部に常時表示（フィルタの影響を受けない）。

## スコープ外（今回やらない）

- メール / LINE 等の能動通知（アプリ内の色表示のみ）
- リアルタイム株価での判定（日次スナップショットで判定）
- 編集のパスワード保護（公開スクリーナー上で誰でも編集可。URLが推測しにくい個人アプリ前提）

## データモデル / 保存先

Google Sheets に新タブ **`watch`**。

| 列 | 型 | 内容 |
|---|---|---|
| `ticker` | str | 銘柄コード（例 `7203.T` / `AAPL`）。スクリーナー対象と一致 |
| `target_price` | float? | 目標買値（任意・**現地通貨**: 日本株=円 / 米国株=ドル）。空欄=到達判定なし |
| `memo` | str | 自由メモ |

- `lib/store.py` に `read_watch()` / `write_watch(df)` を追加（既存 cash/holdings と同じ作法）。
- 公開スクリーナーは頻繁に開かれるため、読み込みは **TTLキャッシュ**し、★操作/保存のたびに `clear()` で即反映。
- Secrets 未設定や Sheets 失敗時は **例外を握りつぶしてウォッチ機能オフ**（スクリーナー本体は壊さない）。

## 到達アラートのロジック（純粋関数）

`lib/watch.py`（Streamlit 非依存・テスト可能）

- `WATCH_COLS = ["ticker", "target_price", "memo"]`
- `build_watch_view(watch_df, data_df) -> pd.DataFrame`
  - ウォッチ各行に、data.parquet から **銘柄名 / 現在値(price) / 通貨 / 市場** を結合。
  - `gap_pct = (target_price / price - 1) * 100`（現在値から目標まであと何%。負=既に目標以下）。
  - `reached = price <= target_price`（target_price が有効な数値のときのみ True）。
  - data.parquet に無い ticker は price=NaN、reached=False（「ウォッチのみ」表示）。

判定は **日次スナップショット株価**（`data.parquet` の `price`、現地通貨）と `target_price` を直接比較。
スナップショットは毎朝07:00 JST更新なので **日次精度**。

## スクリーナー画面のUI

1. **最上部に「★ ウォッチリスト」パネル**（= 先頭表示）。現在のフィルタに関係なく全ウォッチ銘柄を表示。
   - 表示: 銘柄 / 現在値 / 目標買値 / あと何%(gap) / メモ / 通貨
   - **到達アラート**: `reached` 行を緑で強調＋「買い時」表示。
   - `st.data_editor` で `target_price` / `memo` をその場編集、行削除も可。「保存」ボタンで `write_watch` → キャッシュ clear → rerun。
2. **メイン一覧テーブル**: ウォッチ済み銘柄の行に ★ 印を付けて区別。
3. **詳細パネル**（銘柄クリック時）: 「★ ウォッチに追加 / 解除」トグルボタン。
   公開スクリーナー上で直接スターを押す操作の中心。押下で watch を更新 → 保存 → clear → rerun。

## モジュール構成

| ファイル | 変更 |
|---|---|
| `lib/watch.py` | 新規。`WATCH_COLS` と `build_watch_view`（純粋関数） |
| `lib/store.py` | `read_watch` / `write_watch` 追加 |
| `pages_screener.py` | ウォッチパネル＋★ボタン＋行マーク |
| `tests/test_watch.py` | 新規。`build_watch_view` の到達判定・gap計算をテスト |

## テスト

- `build_watch_view`: 到達/未到達/目標空欄/対象外ticker の各ケースを純粋関数として検証
  （cash.py / portfolio.py と同じ方針）。
- 既存の `test_app.py`（スクリーナー AppTest）が壊れないこと。
