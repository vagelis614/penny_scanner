# Penny Stock Screener Streamlit App

import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import time

st.title("🔥 Penny Stock Screener")
st.write("Φιλτράρισμα με βάση RSI, MACD, ADX και τιμή κάτω από $5")

# --- Step 1: Load tickers ---
@st.cache_data(show_spinner=False)
def load_tickers():
    nasdaq = pd.read_csv(
        "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt",
        sep="|"
    )
    nyse = pd.read_csv(
        "ftp://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt",
        sep="|"
    )
    tickers = pd.concat([
        nasdaq['Symbol'],
        nyse['ACT Symbol']
    ], ignore_index=True).dropna().unique().tolist()
    return tickers

tickers = load_tickers()
st.success(f"Βρέθηκαν {len(tickers)} συνολικά tickers.")

# --- Step 2: Filter penny stocks under $5 ---
@st.cache_data(show_spinner=False)
def filter_penny_stocks(tickers):
    penny = []
    for ticker in tickers:
        try:
            data = yf.Ticker(ticker).history(period="1d")
            price = data['Close'][-1]
            if price < 5 and price > 0.2:
                penny.append(ticker)
        except:
            continue
    return penny

sample_size = st.slider("Πόσα tickers να ελέγξω;", 50, 500, 100, step=50)
if st.button("Ξεκίνα Σκανάρισμα"):
    penny_stocks = filter_penny_stocks(tickers[:sample_size])
    st.info(f"Βρέθηκαν {len(penny_stocks)} penny stocks κάτω από $5.")

    # --- Step 3: Technical Analysis ---
    results = []
    progress = st.progress(0)

    for i, ticker in enumerate(penny_stocks):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6mo")
            if len(hist) < 30:
                continue

            hist = ta.add_all_ta_features(
                hist, open="Open", high="High", low="Low",
                close="Close", volume="Volume"
            )

            latest = hist.iloc[-1]
            rsi = latest['momentum_rsi']
            macd = latest['trend_macd']
            signal = latest['trend_macd_signal']
            adx = latest['trend_adx']
            volume = latest['Volume']

            score = 0
            if rsi < 35: score += 1
            if macd > signal: score += 1
            if adx > 20: score += 1
            if volume > hist['Volume'].mean(): score += 1

            if score >= 3:
                results.append({
                    'Ticker': ticker,
                    'Price': hist['Close'].iloc[-1],
                    'RSI': round(rsi, 2),
                    'MACD > Signal': macd > signal,
                    'ADX': round(adx, 2),
                    'Volume': int(volume),
                    'Score': score
                })
        except:
            continue
        progress.progress((i + 1) / len(penny_stocks))

    df_results = pd.DataFrame(results)
    st.success(f"Βρέθηκαν {len(df_results)} υποψήφιες μετοχές.")
    st.dataframe(df_results.sort_values(by="Score", ascending=False))
    st.download_button("💾 Κατέβασε CSV", data=df_results.to_csv(index=False), file_name="penny_stock_results.csv")
