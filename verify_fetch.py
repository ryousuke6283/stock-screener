# -*- coding: utf-8 -*-
"""
yfinance 取得検証スクリプト（MVP第一歩）
日本株3 + 米国株3 で、スクリーニングに使う指標がちゃんと取れるか確認する。
"""
import yfinance as yf
import pandas as pd

# 日本株は .T、米国株はそのまま
TICKERS = {
    "7203.T": "トヨタ自動車",
    "9984.T": "ソフトバンクG",
    "6758.T": "ソニーG",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
}

# 取りたい指標（info の生キー）と表示名
FIELDS = {
    "currentPrice": "株価",
    "currency": "通貨",
    "trailingPE": "PER",
    "priceToBook": "PBR",
    "dividendYield": "配当利回り",
    "returnOnEquity": "ROE",
    "revenueGrowth": "増収率",
    "earningsGrowth": "増益率",
    "fiftyDayAverage": "50日平均",
    "twoHundredDayAverage": "200日平均",
    "marketCap": "時価総額",
}

rows = []
for code, name in TICKERS.items():
    print(f"取得中: {code} ({name}) ...")
    try:
        info = yf.Ticker(code).info
        row = {"コード": code, "銘柄": name}
        for key, label in FIELDS.items():
            row[label] = info.get(key)
        rows.append(row)
    except Exception as e:
        print(f"  失敗: {e}")

df = pd.DataFrame(rows)

# 見やすく整形
pd.set_option("display.unicode.east_asian_width", True)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

print("\n===== 取得結果 =====")
print(df.to_string(index=False))

# どの指標が欠損しているか集計
print("\n===== 欠損チェック（None の数 / 全6銘柄）=====")
print(df.drop(columns=["コード", "銘柄"]).isna().sum().to_string())
