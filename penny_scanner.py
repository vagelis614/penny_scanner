# Penny Stock Screener Streamlit App

import streamlit as st
import pandas as pd
import yfinance as yf
import ta
from datetime import datetime, timedelta
import requests

st.title("🔥 Penny Stock Screener")
st.write("Φιλτράρισμα με βάση RSI, MACD, ADX, Volume και Εκρηκτικές Ειδήσεις")

with st.expander("ℹ️ Τι σημαίνει κάθε δείκτης;"):
    st.markdown("""
    - **RSI < 35** → Υπερπουλημένη κατάσταση (πιθανή ανοδική αντίδραση)
    - **MACD > Signal** → Bullish ένδειξη τάσης
    - **ADX > 20** → Υπάρχει αξιοσημείωτο trend
    - **Volume > Μέσος Όγκος** → Αυξημένο ενδιαφέρον
    - **Earnings Soon** → Επερχόμενα οικονομικά αποτελέσματα (πιθανή μεταβλητότητα)
    - **News Catalyst** → Πρόσφατες ειδήσεις σχετικές με FDA, trials, approvals κ.λπ.
    """)

API_KEY = "pub_42f28d75ab6a4124a6c74bc9e2099f77"

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
        except:
            continue
    return penny

def has_biotech_news(ticker, api_key):
    keywords = ['FDA', 'phase 2', 'clinical trial', 'approval', 'data readout', 'pdufa']
    url = f"https://newsdata.io/api/1/news?apikey={api_key}&q={ticker}&language=en"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for article in data.get('results', []):
                text = (article.get('title', '') + article.get('description', '')).lower()
                if any(k.lower() in text for k in keywords):
                    return True, article['title']
    except:
        pass
    return False, None

sample_size = st.number_input("Πόσα tickers να ελέγξω; (max 11000)", min_value=50, max_value=11000, value=500, step=50)
if st.button("Ξεκίνα Σκανάρισμα"):
    tickers = load_tickers()
    penny_stocks = filter_penny_stocks(tickers[:sample_size])
    st.info(f"Βρέθηκαν {len(penny_stocks)} penny stocks κάτω από $5.")

    if not penny_stocks:
        st.error("❌ Δεν βρέθηκαν penny stocks κάτω από $5.")
    else:
        results = []
        progress = st.progress(0)
        today = datetime.today()
        seven_days = today + timedelta(days=7)

        for i, ticker in enumerate(penny_stocks):
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="6mo")
                if len(hist) < 30:
                    continue

                hist = ta.add_all_ta_features(hist, open="Open", high="High", low="Low", close="Close", volume="Volume")
                latest = hist.iloc[-1]
                rsi = latest['momentum_rsi']
                macd = latest['trend_macd']
                signal = latest['trend_macd_signal']
                adx = latest['trend_adx']
                volume = latest['Volume']

                earnings_soon = False
                earnings_date = None
                try:
                    cal = stock.calendar
                    if not cal.empty:
                        earnings_date = cal.loc['Earnings Date'][0]
                        if isinstance(earnings_date, pd.Timestamp) and today <= earnings_date <= seven_days:
                            earnings_soon = True
                except:
                    pass

                news_catalyst, news_title = has_biotech_news(ticker, API_KEY)

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
                        'Score': score,
                        'Earnings Soon': earnings_soon,
                        'Earnings Date': earnings_date.date() if isinstance(earnings_date, pd.Timestamp) else None,
                        'News Catalyst': news_catalyst,
                        'Headline': news_title if news_catalyst else ''
                    })
            except:
                continue
            progress.progress((i + 1) / len(penny_stocks))

        df_results = pd.DataFrame(results)
        if df_results.empty:
            st.warning("❌ No strong buy signals found among penny stocks.")
        else:
            st.success(f"Βρέθηκαν {len(df_results)} υποψήφιες μετοχές.")

            def highlight_rows(row):
                if row['News Catalyst']:
                    return ['background-color: red; color: white'] * len(row)
                elif row['Earnings Soon']:
                    return ['background-color: #0077cc; color: white'] * len(row)
                elif row['Score'] >= 4:
                    return ['background-color: green; color: white'] * len(row)
                elif row['Score'] == 3:
                    return ['background-color: orange; color: black'] * len(row)
                else:
                    return [''] * len(row)

            styled_df = df_results.sort_values(by="Score", ascending=False).style.apply(highlight_rows, axis=1)
            st.dataframe(styled_df, use_container_width=True)

            st.download_button("💾 Κατέβασε CSV", data=df_results.to_csv(index=False), file_name="penny_stock_results.csv")
