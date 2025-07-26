import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import ta

st.set_page_config(page_title="AI Penny Stock Screener", layout="wide")

st.title("📈 AI Penny Stock Screener (RSI, MACD, ADX, Volume)")

# ----------- Σκράπινγκ penny stock tickers από Finviz -----------
@st.cache_data
def get_penny_stock_tickers(max_price=5.0):
    url = f"https://finviz.com/screener.ashx?v=111&s=ta_topgainers&f=sh_price_u{max_price}&r=1"
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    tickers = []
    for row in soup.select('a.screener-link-primary'):
        ticker = row.text.strip()
        if ticker.isalpha():
            tickers.append(ticker)
    return list(set(tickers))

tickers = get_penny_stock_tickers()

st.markdown(f"🔍 **Found {len(tickers)} penny stocks under $5:**")
st.write(tickers)

# ----------- Λογική για screening ----------
def analyze_ticker(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df.empty or df['Close'].isnull().all():
            return None

        df = df.dropna()
        df['RSI'] = ta.momentum.RSIIndicator(close=df['Close']).rsi()
        macd = ta.trend.MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        adx = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'])
        df['ADX'] = adx.adx()
        df['Volume'] = df['Volume']

        latest = df.iloc[-1]
        if latest['RSI'] < 30 and latest['MACD'] > latest['MACD_signal'] and latest['ADX'] > 25:
            return {
                'Ticker': ticker,
                'Price': latest['Close'],
                'RSI': round(latest['RSI'], 2),
                'MACD': round(latest['MACD'], 2),
                'MACD Signal': round(latest['MACD_signal'], 2),
                'ADX': round(latest['ADX'], 2),
                'Volume': int(latest['Volume']),
            }
        return None
    except Exception as e:
        return None

st.markdown("📊 **Scanning stocks... This may take a moment.**")

results = []
for ticker in tickers:
    res = analyze_ticker(ticker)
    if res:
        results.append(res)

if results:
    df_results = pd.DataFrame(results).sort_values(by="ADX", ascending=False)
    st.success(f"✅ Found {len(df_results)} strong 'Buy' candidates!")
    st.dataframe(df_results, use_container_width=True)
else:
    st.warning("❌ No strong buy signals found among penny stocks.")
