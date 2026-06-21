# -*- coding: utf-8 -*-
"""日本株・米国株スクリーナー + マイポートフォリオ（エントリ/ナビ）"""
import streamlit as st
from lib.common import inject_css

st.set_page_config(page_title="株スクリーナー", page_icon=":material/candlestick_chart:", layout="wide")
inject_css()  # 全ページ共通でモノトーンCSSを適用

screener = st.Page("pages_screener.py", title="スクリーナー", icon=":material/candlestick_chart:", default=True)
portfolio = st.Page("pages_portfolio.py", title="ポートフォリオ", icon=":material/account_balance_wallet:")
st.navigation([screener, portfolio]).run()
