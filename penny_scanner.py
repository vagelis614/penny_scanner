# Penny Stock Screener Streamlit App

import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import matplotlib.pyplot as plt
import time

st.title("🔥 Penny Stock Screener")
st.write("Φιλτράρισμα με βάση RSI, MACD, ADX και τιμή κάτω από $5")

with st.expander("ℹ️ Τι σημαίνει κάθε δείκτης;"):
    st.markdown("""
    - **RSI < 35** → Υπερπουλημένη κατάσταση (πιθανή ανοδική αντίδραση)
    - **MACD > Signal** → Bullish ένδειξη τάσης
    - **ADX > 20** → Υπάρχει αξιοσημείωτο trend (ισχυρό ή αδύναμο)
    - **Volume > Μέσος Όγκος** → Αυξημένο ενδιαφέρον
    """)

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
            if not data.empty:
                price = data['Close'][-1]
                if 0.01 < price < 5:
                    penny.append(ticker)
        except Exception as e:
            print(f"Error for {ticker}: {e}")
            continue
    return penny

sample_size = st.number_input("Πόσα tickers να ελέγξω; (max 11000)", min_value=50, max_value=11000, value=500, step=50)
if st.button("Ξεκίνα Σκανάρισμα"):
    penny_stocks = filter_penny_stocks(tickers[:sample_size])
    st.info(f"Βρέθηκαν {len(penny_stocks)} penny stocks κάτω από $5.")

    if not penny_stocks:
        st.error("❌ Δεν βρέθηκαν penny stocks κάτω από $5.")
    else:
        # --- Step 3: Technical Analysis ---
        results = []
        charts = {}
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

                    # Mini chart
                    fig, ax = plt.subplots()
                    hist['Close'].tail(30).plot(ax=ax)
                    ax.set_title(ticker)
                    ax.set_ylabel("Price")
                    charts[ticker] = fig

            except Exception as e:
                print(f"Error analyzing {ticker}: {e}")
                continue
            progress.progress((i + 1) / len(penny_stocks))

        df_results = pd.DataFrame(results)
        if df_results.empty:
            st.warning("❌ No strong buy signals found among penny stocks.")
        else:
            st.success(f"Βρέθηκαν {len(df_results)} υποψήφιες μετοχές.")

            def color_score(val):
                if val >= 4:
                    return 'background-color: green; color: white'
                elif val == 3:
                    return 'background-color: orange; color: black'
                else:
                    return ''

            styled_df = df_results.sort_values(by="Score", ascending=False).style.applymap(color_score, subset=['Score'])
            st.dataframe(styled_df, use_container_width=True)

            # Show mini charts
            st.subheader("📈 Mini Charts")
            for ticker in df_results.sort_values(by="Score", ascending=False)['Ticker']:
                if ticker in charts:
                    st.pyplot(charts[ticker])

            st.download_button("💾 Κατέβασε CSV", data=df_results.to_csv(index=False), file_name="penny_stock_results.csv")
