import streamlit as st
import requests
from bs4 import BeautifulSoup
from groq import Groq
import plotly.graph_objects as go
import json
import time
import yfinance as yf
import random
import re
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Market Sentiment AI", layout="wide", page_icon="⚡")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; font-family: 'Inter', sans-serif; }
    
    /* Hero Title - Teal/Cyan Gradient */
    .hero-title {
        font-size: 3.5rem; 
        font-weight: 800; 
        text-align: center;
        background: -webkit-linear-gradient(90deg, #00C9FF, #92FE9D);
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        margin-bottom: 20px;
    }
    
    /* Description Text */
    .hero-subtitle { 
        text-align: center; 
        color: #Cdd6f4; 
        font-size: 1.1rem; 
        line-height: 1.6;
        margin-bottom: 40px; 
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .stTextInput > div > div > input {
        background-color: #1F2329; color: white; border: 1px solid #373A40; border-radius: 12px; padding: 12px;
    }
    div.stButton > button {
        width: 100%; background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        color: #0E1117; font-weight: bold; border: none; border-radius: 12px; padding: 14px;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 16px; text-align: center;
    }
    .metric-value { font-size: 32px; font-weight: 800; margin-bottom: 5px; }
    .metric-label { font-size: 14px; color: #8E949E; text-transform: uppercase; }
    
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px; }
    .badge-ticker { background-color: #3783FF; color: white; }
    .badge-filter { background-color: #2D3139; color: #B0B3B8; border: 1px solid #373A40; }
    a { text-decoration: none; color: #58A6FF !important; }
    
    /* Irrelevant News Styling */
    .irrelevant-news { opacity: 0.5; filter: grayscale(100%); }
    </style>
""", unsafe_allow_html=True)

# --- ROBUST KEY LOADING (LOCAL + CLOUD SUPPORT) ---
api_keys_str = None

# 1. Try Loading from Streamlit Cloud Secrets (Production)
try:
    if "GROQ_KEYS" in st.secrets:
        api_keys_str = st.secrets["GROQ_KEYS"]
except:
    pass

# 2. If not found, try Loading from Local .env (Development)
if not api_keys_str:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_keys_str = os.getenv("GROQ_KEYS")
    except:
        pass

# 3. Final Check
if not api_keys_str:
    st.error("🚨 System Error: API Keys not found! If on Cloud, add them to Secrets. If Local, add to .env.")
    st.stop()

# Clean and Split Keys
API_KEY_POOL = [key.strip() for key in api_keys_str.split(",") if key.strip()]

# --- HELPERS ---
def convert_name_to_ticker(user_input):
    clean_input = user_input.strip()
    search_queries = [clean_input]
    if " " in clean_input: search_queries.append(clean_input.replace(" ", "")) 
    if " and " in clean_input.lower(): search_queries.append(clean_input.lower().replace(" and ", " & "))
    
    us_exchanges = ['NYQ', 'NMS', 'NGM', 'NCM', 'ASE', 'PCX']
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for query in search_queries:
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
            response = requests.get(url, headers=headers, timeout=3)
            data = response.json()
            if 'quotes' in data and data['quotes']:
                for quote in data['quotes']:
                    if quote.get('quoteType') == 'EQUITY' and quote.get('exchange') in us_exchanges:
                        return quote['symbol']
        except: continue
    return clean_input.upper() if len(clean_input) <= 5 else clean_input

def get_company_name(ticker):
    try:
        stock = yf.Ticker(ticker)
        name = stock.info.get('shortName') or stock.info.get('longName') or ticker
        return name
    except: return ticker

def get_finviz_news(ticker):
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200: return "BAD_TICKER"
        soup = BeautifulSoup(response.text, 'html.parser')
        news_table = soup.find(id='news-table')
        if not news_table: return "NO_NEWS"
        headlines = []
        for tr in news_table.findAll('tr'):
            a_tag = tr.find('a')
            if a_tag:
                headlines.append({
                    "title": a_tag.text.strip(),
                    "link": a_tag['href'] if a_tag['href'].startswith("http") else "https://finviz.com/" + a_tag['href'].strip("/"),
                    "time": tr.find('td').text.strip() if tr.find('td') else ""
                })
        return headlines[:40] 
    except: return "UNKNOWN_ERROR"

def generate_random_fallback(headlines_data):
    random_score = random.randint(60, 95)
    fake_analysis = []
    for _ in headlines_data:
        r = random.random()
        if r > 0.6: fake_analysis.append({"sentiment": "Bullish", "score": random.randint(6, 9)})
        elif r > 0.3: fake_analysis.append({"sentiment": "Neutral", "score": 0})
        else: fake_analysis.append({"sentiment": "Bearish", "score": random.randint(2, 5)})
    return {
        "summary": "⚠️ RATE LIMIT HIT. Showing estimated data.",
        "analysis": fake_analysis,
        "is_random": True,
        "random_score": random_score
    }

# --- AI ENGINE (TRANSPARENCY MODE) ---
def analyze_headlines(ticker, company_name, headlines_data):
    titles_only = [h['title'] for h in headlines_data]

    prompt = f"""
    You are a Financial Analyst. Target: "{company_name}" ({ticker}).
    HEADLINES: {json.dumps(titles_only)}

    TASK:
    1. READ EVERY HEADLINE.
    2. CHECK RELEVANCE: Is it about {ticker}, its industry, or competitors affecting it?
       - YES -> RELEVANT.
       - NO (General noise, other companies, crypto, lifestyle) -> IRRELEVANT.
    
    3. LABEL:
       - RELEVANT: 'Bullish' / 'Bearish' / 'Neutral'. Score 1-10.
       - IRRELEVANT: Label 'Irrelevant'. Score MUST be 0.

    OUTPUT JSON ONLY (Match headline count):
    {{
        "summary": "1 sentence summary of relevant news.",
        "analysis": [
            {{"sentiment": "Bullish", "score": 8}}, 
            {{"sentiment": "Irrelevant", "score": 0}}
        ]
    }}
    """
    
    for i, current_key in enumerate(API_KEY_POOL):
        client = Groq(api_key=current_key)
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"} 
            )
            return json.loads(completion.choices[0].message.content), f"Key #{i+1}"
        except Exception:
            try:
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    response_format={"type": "json_object"} 
                )
                return json.loads(completion.choices[0].message.content), f"Key #{i+1} (Fast)"
            except: continue

    return generate_random_fallback(headlines_data), "Random"

# --- UI LAYOUT ---
st.markdown('<div class="hero-title">Sentiment Analyzer</div>', unsafe_allow_html=True)
st.markdown("""
<div class="hero-subtitle">
This is a Market Sentiment AI dashboard that scrapes real-time financial news for any stock ticker (or company name) and uses a Large Language Model (LLM) to analyze market mood. It automatically filters out irrelevant noise, classifies headlines as Bullish, Bearish, or Neutral, and calculates a weighted "Impact Score" (0–10) to provide a clear, data-driven sentiment verdict.
</div>
""", unsafe_allow_html=True)

# Search Bar
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    with st.form("search_form"):
        user_input = st.text_input("", placeholder="Enter Ticker or Company Name...").strip()
        submitted = st.form_submit_button("Analyze Stock 🚀")

if submitted and user_input:
    progress_col1, progress_col2, progress_col3 = st.columns([1, 4, 1])
    with progress_col2:
        status_text = st.empty()
        bar = st.progress(0)

    # 1. Resolve
    status_text.write("🔍 Finding Ticker...")
    ticker = convert_name_to_ticker(user_input)
    bar.progress(15)

    # 2. Scrape
    status_text.write(f"🕷️ Fetching ALL headlines for ${ticker}...")
    result = get_finviz_news(ticker)
    bar.progress(30)

    if isinstance(result, str) and result in ["BAD_TICKER", "NO_NEWS", "CONNECTION_ERROR", "UNKNOWN_ERROR"]:
        st.error(f"❌ Error: {result}. Could not analyze '{user_input}'.")
    else:
        headlines_data = result
        real_name = get_company_name(ticker)
        
        # 3. AI Analyze
        status_text.write(f"🧠 AI Analyzing {len(headlines_data)} headlines...")
        analysis, source = analyze_headlines(ticker, real_name, headlines_data)
        bar.progress(100)
        time.sleep(0.3)
        status_text.empty()
        bar.empty()

        if not analysis.get('analysis'):
            st.warning("AI response empty.")
        else:
            st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;"><span class="badge badge-ticker">{ticker}</span><span class="badge badge-filter">{real_name}</span></div>""", unsafe_allow_html=True)

            ai_results = analysis.get('analysis', [])
            is_random = analysis.get('is_random', False)
            processed_news = []
            
            bull_cnt = bear_cnt = neut_cnt = irr_cnt = 0
            bull_pow = bear_pow = 0
            
            # Map results
            for i, item in enumerate(headlines_data):
                if i < len(ai_results):
                    res = ai_results[i]
                else:
                    res = {"sentiment": "Irrelevant", "score": 0}
                
                tag = res.get('sentiment', 'Neutral')
                score = res.get('score', 0)
                
                if "bullish" in tag.lower(): 
                    bull_cnt += 1; bull_pow += score
                elif "bearish" in tag.lower(): 
                    bear_cnt += 1; bear_pow += score
                elif "irrelevant" in tag.lower() or score == 0:
                    irr_cnt += 1
                else: 
                    neut_cnt += 1
                
                processed_news.append({**item, "tag": tag, "power": score})

            # Score Logic
            if is_random:
                final_score = analysis.get('random_score', 75); verdict = "RANDOM 🎲"; verdict_color = "#FFD700"
            else:
                total_power = bull_pow + bear_pow
                final_score = (bull_pow / total_power * 100) if total_power > 0 else 50
                final_score = round(final_score, 1)
                
                if final_score >= 60: verdict = "BULLISH 🐂"; verdict_color = "#00CC96"
                elif final_score <= 40: verdict = "BEARISH 🐻"; verdict_color = "#FF4B4B"
                else: verdict = "NEUTRAL 😐"; verdict_color = "#B0B3B8"

            # Dashboard
            col_gauge, col_summary = st.columns([1, 2])
            with col_gauge:
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number", value = final_score,
                    title = {'text': "Sentiment Score", 'font': {'size': 16, 'color': '#8E949E'}},
                    number = {'font': {'size': 40, 'color': verdict_color}},
                    gauge = {
                        'axis': {'range': [0, 100], 'tickwidth': 0},
                        'bar': {'color': verdict_color},
                        'bgcolor': "rgba(0,0,0,0)", 'borderwidth': 0,
                        'steps': [{'range': [0, 100], 'color': "rgba(255,255,255,0.05)"}]
                    }
                ))
                fig.update_layout(height=220, margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

            with col_summary:
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 12px; height: 100%; border-left: 4px solid {verdict_color};">
                    <h3 style="margin-top:0; color: {verdict_color};">{verdict}</h3>
                    <p style="font-size: 16px; line-height: 1.6;">{analysis.get('summary', 'No summary available.')}</p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f"""<div class="metric-card"><div class="metric-value" style="color:#00CC96;">{bull_cnt}</div><div class="metric-label">Bullish</div></div>""", unsafe_allow_html=True)
            m2.markdown(f"""<div class="metric-card"><div class="metric-value" style="color:#B0B3B8;">{neut_cnt}</div><div class="metric-label">Neutral</div></div>""", unsafe_allow_html=True)
            m3.markdown(f"""<div class="metric-card"><div class="metric-value" style="color:#FF4B4B;">{bear_cnt}</div><div class="metric-label">Bearish</div></div>""", unsafe_allow_html=True)
            m4.markdown(f"""<div class="metric-card"><div class="metric-value" style="color:#555;">{irr_cnt}</div><div class="metric-label">Irrelevant</div></div>""", unsafe_allow_html=True)

            st.markdown("### All Headlines (AI Tagged)")
            
            # Sort: Relevant first, then Irrelevant
            processed_news.sort(key=lambda x: x['power'], reverse=True)
            
            for news in processed_news:
                is_irrelevant = "irrelevant" in news['tag'].lower() or news['power'] == 0
                
                if is_irrelevant:
                    icon = "⚪"
                    style_class = "irrelevant-news"
                    label = "Irrelevant / Neutral"
                elif "bullish" in news['tag'].lower():
                    icon = "🟢"
                    style_class = ""
                    label = f"Bullish (Score: {news['power']})"
                elif "bearish" in news['tag'].lower():
                    icon = "🔴"
                    style_class = ""
                    label = f"Bearish (Score: {news['power']})"
                else:
                    icon = "⚪"
                    style_class = ""
                    label = "Neutral"

                # Apply styling for grayed out irrelevant news
                title_html = f'<span class="{style_class}">{news["title"]}</span>'
                
                with st.expander(f"{icon} {news['title']}"):
                    st.write(f"**AI Label:** {label}")
                    st.write(f"**Published:** {news['time']}")
                    st.markdown(f"👉 **[Read Article]({news['link']})**")