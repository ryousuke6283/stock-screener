# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.common import quote_ticker, resolve_name, fund_info


def main():
    # 投信エイリアス → 連動ETF
    assert quote_ticker("楽天VTI") == "VTI"
    assert quote_ticker("オルカン") == "ACWI"
    assert quote_ticker("S&P500") == "VOO"
    assert quote_ticker("sp500") == "VOO"        # 正規化（大小・記号）
    assert quote_ticker("7203.T") == "7203.T"    # 非ファンドはそのまま

    # 表示名
    assert "VTI" in resolve_name("楽天VTI")       # 「楽天VTI（≈VTI）」
    assert resolve_name("AAPL") == "アップル"      # 既知の米国株カタカナ
    assert fund_info("ナスダック")[0] == "QQQ"
    print("OK: test_funds passed")


if __name__ == "__main__":
    main()
