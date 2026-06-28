# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from lib.watch import build_watch_view, clean_watch, WATCH_COLS, VIEW_COLS


def _data():
    return pd.DataFrame([
        {"ticker": "7203.T", "name": "トヨタ自動車", "market": "JP", "currency": "JPY", "price": 3000.0},
        {"ticker": "AAPL", "name": "Apple Inc.", "market": "US", "currency": "USD", "price": 200.0},
        {"ticker": "6758.T", "name": "ソニーグループ", "market": "JP", "currency": "JPY", "price": 3500.0},
    ])


def main():
    data = _data()
    watch = pd.DataFrame([
        {"ticker": "7203.T", "target_price": 3200, "memo": "押し目"},   # 3000<=3200 → 到達
        {"ticker": "AAPL", "target_price": 150, "memo": "決算後"},       # 200<=150? いいえ → 未到達
        {"ticker": "6758.T", "target_price": None, "memo": "監視のみ"},  # 目標なし → 判定なし
        {"ticker": "ZZZZ", "target_price": 10, "memo": "対象外"},        # data に無い → price NaN
    ])

    v = build_watch_view(watch, data)
    assert list(v.columns) == VIEW_COLS, v.columns
    assert len(v) == 4

    by = {r["ticker"]: r for _, r in v.iterrows()}

    # 到達: 現在値 <= 目標
    assert by["7203.T"]["reached"] is True or by["7203.T"]["reached"] == True
    # gap = (3200/3000 - 1)*100 ≈ +6.67%
    assert abs(by["7203.T"]["gap_pct"] - ((3200 / 3000 - 1) * 100)) < 1e-6

    # 未到達: 現在値(200) > 目標(150)
    assert not by["AAPL"]["reached"]
    assert abs(by["AAPL"]["gap_pct"] - ((150 / 200 - 1) * 100)) < 1e-6   # 負（-25%）
    assert by["AAPL"]["gap_pct"] < 0

    # 目標なし: reached False / gap NaN / 名前は data から
    assert not by["6758.T"]["reached"]
    assert pd.isna(by["6758.T"]["gap_pct"])
    assert by["6758.T"]["name"] == "ソニーグループ"

    # 対象外ticker: price NaN・reached False・name は ticker フォールバック
    assert pd.isna(by["ZZZZ"]["price"])
    assert not by["ZZZZ"]["reached"]
    assert by["ZZZZ"]["name"] == "ZZZZ"

    # 空のウォッチ → 空のビュー（列だけ）
    empty = build_watch_view(pd.DataFrame(columns=WATCH_COLS), data)
    assert empty.empty and list(empty.columns) == VIEW_COLS

    # clean_watch: 重複は後勝ち・空ticker除去
    dup = pd.DataFrame([
        {"ticker": "7203.T", "target_price": 1, "memo": "old"},
        {"ticker": "7203.T", "target_price": 2, "memo": "new"},
        {"ticker": "", "target_price": 5, "memo": "空"},
    ])
    c = clean_watch(dup)
    assert len(c) == 1 and c.iloc[0]["target_price"] == 2 and c.iloc[0]["memo"] == "new"

    print("OK: test_watch passed")


if __name__ == "__main__":
    main()
