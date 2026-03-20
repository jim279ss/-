import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from FinMind.data import DataLoader
import feedparser
import re

# --- 頁面設定 ---
st.set_page_config(page_title="AI 高毛利供應鏈決策系統", layout="wide")

# --- 1. 擴充版股票名稱對照表 (確保 100% 中文) ---
STOCK_MAP = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "3017.TW": "奇鋐", "3450.TW": "聯鈞",
    "2312.TW": "金寶", "2409.TW": "友達", "2520.TW": "冠德", "2609.TW": "陽明",
    "2634.TW": "漢翔", "2890.TW": "永豐金", "3051.TW": "鴻名", "3062.TW": "建漢",
    "4906.TW": "正文", "2382.TW": "廣達", "6669.TW": "緯穎", "2308.TW": "台達電",
    "3013.TW": "晟銘電", "3324.TW": "雙鴻", "2421.TW": "建準", "2059.TW": "川湖",
    "6274.TW": "台燿", "2368.TW": "金像電", "3533.TW": "嘉澤", "6213.TW": "聯茂",
    "3661.TW": "世芯-KY", "3443.TW": "創意", "6643.TW": "M31", "3529.TW": "力旺",
    "2454.TW": "聯發科", "3363.TW": "上詮", "6442.TW": "光聖", "3163.TW": "波若威",
    "4979.TW": "華星光", "8299.TW": "群聯", "2408.TW": "南亞科", "3037.TW": "欣興",
    "3189.TW": "景碩", "8046.TW": "南電", "6223.TW": "旺矽", "3583.TW": "辛耘",
    "NVDA": "NVIDIA", "TSM": "台積電ADR", "^SOX": "費城半導體"
}

def get_stock_name(ticker):
    if ticker in STOCK_MAP: return STOCK_MAP[ticker]
    try:
        s = yf.Ticker(ticker)
        name = s.info.get('shortName', ticker)
        for suffix in [" CORPORATION", " CO LTD", " INC.", " TECHNOLOGY", " ELECTRONICS"]:
            name = name.upper().replace(suffix, "")
        return name
    except: return ticker

# --- 2. 新聞抓取功能 ---
def get_latest_news():
    try:
        feed = feedparser.parse("https://tw.stock.yahoo.com/rss/economy")
        return [{"標題": e.title, "連結": e.link, "代碼": re.findall(r'\d{4}', e.title)} for e in feed.entries[:4]]
    except: return []

# --- 3. 核心分析函數 (含毛利率偵測) ---
@st.cache_data(ttl=3600)
def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="150d")
        if df.empty: return None
        
        # 技術面
        curr_price = df['Close'].iloc[-1]
        pct = ((curr_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        ma5 = df['Close'].rolling(5).mean().iloc[-1]
        low_60 = df['Close'].tail(60).min()
        
        # 財報面 (毛利率)
        margin = 0
        try:
            q_fin = stock.quarterly_income_stmt.T
            margin = (q_fin['Gross Profit'].iloc[0] / q_fin['Total Revenue'].iloc[0]) * 100
        except: margin = 0

        # 籌碼面
        chip_sum = 0
        if ".TW" in ticker:
            dl = DataLoader()
            chip_df = dl.taiwan_stock_institutional_investors(
                stock_id=ticker.replace(".TW", ""),
                start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
                end_date=datetime.now().strftime('%Y-%m-%d')
            )
            if not chip_df.empty:
                chip_sum = (chip_df.tail(9)['buy'].sum() - chip_df.tail(9)['sell'].sum()) / 1000

        is_bottom = curr_price < (low_60 * 1.12)
        high_margin = "💎" if margin > 30 else ""
        
        if is_bottom and curr_price > ma5 and chip_sum > 0: signal = "🔥 底部起漲"
        elif curr_price > ma5 and chip_sum > 0: signal = "🚀 多頭續強"
        elif curr_price < ma5 and chip_sum < 0: signal = "❄️ 轉弱觀望"
        else: signal = "☁️ 區間震盪"

        return {
            "股票標的": f"{high_margin}{get_stock_name(ticker)}",
            "現價": round(curr_price, 2),
            "漲跌幅(%)": round(pct, 2),
            "毛利率(%)": round(margin, 1),
            "籌碼(K)": round(chip_sum, 1),
            "買賣建議": signal,
            "ticker": ticker
        }
    except: return None

# --- 4. 主介面 ---
st.title("🚀 AI 高毛利供應鏈決策系統")

# 新聞區
news = get_latest_news()
if news:
    cols = st.columns(len(news))
    for i, n in enumerate(news):
        cols[i].markdown(f"**[{n['標題']}]({n['連結']})**")

st.sidebar.header("👤 個人持股管理")
query_params = st.query_params
default_stocks = query_params.get("stocks", "2330, 3017, 3450, NVDA")
my_input = st.sidebar.text_input("輸入代碼 (逗號隔開)", default_stocks)
if st.sidebar.button("💾 記憶持股連結"):
    st.query_params["stocks"] = my_input
    st.sidebar.success("已產生記憶連結，請加入書籤")

processed_stocks = []
for s in my_input.split(","):
    s = s.strip().upper()
    if s.isdigit() and ".TW" not in s: s = f"{s}.TW"
    processed_stocks.append(s)

# 最新產品線分類
WATCHLIST = {
    "我的持股": processed_stocks,
    "GB200 液冷/機櫃": ["3017.TW", "3324.TW", "3013.TW", "2421.TW", "2308.TW", "2301.TW"],
    "GB200 組裝/PCB": ["2317.TW", "2382.TW", "6669.TW", "6274.TW", "2368.TW", "6213.TW"],
    "CoWoS/先進封裝": ["3583.TW", "6187.TW", "3131.TW", "6223.TW", "2330.TW"],
    "矽光子/CPO": ["3450.TW", "3363.TW", "6442.TW", "3163.TW", "4979.TW", "3081.TW"],
    "IC設計/IP (高毛利)": ["3661.TW", "3443.TW", "2454.TW", "6643.TW", "3529.TW"]
}

tabs = st.tabs(list(WATCHLIST.keys()))
all_tickers = []

for i, cat in enumerate(WATCHLIST.keys()):
    with tabs[i]:
        results = [analyze_stock(t) for t in WATCHLIST[cat] if analyze_stock(t)]
        df = pd.DataFrame(results)
        if not df.empty:
            st.dataframe(df.style.applymap(lambda v: 'color: #FF0000' if "買入" in str(v) or "起漲" in str(v) else ('color: #00FF00' if "賣出" in str(v) else ''), subset=['買賣建議']), use_container_width=True, hide_index=True)
            all_tickers.extend(WATCHLIST[cat])

# --- 5. 深度分析區 (確保不消失) ---
st.divider()
unique_tickers = list(dict.fromkeys(all_tickers))
target = st.selectbox("🎯 選擇分析標的：", unique_tickers, format_func=lambda x: f"{x} {get_stock_name(x)}")

if target:
    st.header(f"🔍 深度分析：{get_stock_name(target)}")
    s_obj = yf.Ticker(target)
    df_all = s_obj.history(period="1y")
    if not df_all.empty:
        for ma in [5, 10, 20, 60, 120]: df_all[f'MA{ma}'] = df_all['Close'].rolling(ma).mean()
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_all.index, open=df_all['Open'], high=df_all['High'], low=df_all['Low'], close=df_all['Close'], name="K線", increasing_line_color='#FF0000', decreasing_line_color='#00AA00'), row=1, col=1)
        ma_colors = {'MA5': '#FFD700', 'MA10': '#00BFFF', 'MA20': '#FF00FF', 'MA60': '#00FF00', 'MA120': '#FFFFFF'}
        for ma, color in ma_colors.items(): fig.add_trace(go.Scatter(x=df_all.index, y=df_all[ma], name=ma, line=dict(color=color, width=1.2)), row=1, col=1)
        vol_colors = ['#FF0000' if df_all['Close'].iloc[i] >= df_all['Open'].iloc[i] else '#00AA00' for i in range(len(df_all))]
