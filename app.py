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
st.set_page_config(page_title="AI 供應鏈投資決策系統", layout="wide")

# --- 1. 股票名稱對照表 (含最新 GB200 供應鏈) ---
STOCK_MAP = {
    "NVDA": "NVIDIA", "TSM": "台積電ADR", "^SOX": "費城半導體",
    "2330.TW": "台積電", "2317.TW": "鴻海", "3017.TW": "奇鋐", "3450.TW": "聯鈞",
    "2382.TW": "廣達", "6669.TW": "緯穎", "2308.TW": "台達電", "3013.TW": "晟銘電",
    "3324.TW": "雙鴻", "2421.TW": "建準", "2059.TW": "川湖", "6274.TW": "台燿",
    "2368.TW": "金像電", "3533.TW": "嘉澤", "6213.TW": "聯茂", "2376.TW": "技嘉",
    "3583.TW": "辛耘", "6187.TW": "萬潤", "3131.TW": "弘塑", "6223.TW": "旺矽",
    "3363.TW": "上詮", "6442.TW": "光聖", "3163.TW": "波若威", "4979.TW": "華星光", "3081.TW": "聯亞"
}

def get_stock_name(ticker):
    if ticker in STOCK_MAP: return STOCK_MAP[ticker]
    try:
        s = yf.Ticker(ticker)
        name = s.info.get('shortName', ticker)
        for suffix in [" CORPORATION", " CO LTD", " INC.", " TECHNOLOGY"]:
            name = name.upper().replace(suffix, "")
        return name
    except: return ticker

# --- 2. 新聞抓取功能 (加入錯誤檢查) ---
def get_latest_news():
    rss_url = "https://tw.stock.yahoo.com/rss/economy"
    try:
        feed = feedparser.parse(rss_url)
        news_list = []
        if feed.entries:
            for entry in feed.entries[:4]: # 抓取前 4 篇
                codes = re.findall(r'\d{4}', entry.title)
                news_list.append({
                    "標題": entry.title,
                    "連結": entry.link,
                    "相關代碼": codes
                })
        return news_list
    except:
        return []

# --- 3. 側邊欄：持股管理 ---
st.sidebar.header("👤 個人持股管理")
query_params = st.query_params
default_stocks = query_params.get("stocks", "2330, 3017, 3450, NVDA")
my_input = st.sidebar.text_input("輸入股票代碼 (逗號隔開)", default_stocks)

if st.sidebar.button("💾 產生我的專屬記憶連結"):
    st.query_params["stocks"] = my_input
    st.sidebar.success("連結已產生！請將網址加入書籤。")

processed_my_stocks = []
for s in my_input.split(","):
    s = s.strip().upper()
    if not s: continue
    if s.isdigit() or (len(s) >= 4 and s[0:2] == "00"):
        if ".TW" not in s: s = f"{s}.TW"
    processed_my_stocks.append(s)

# --- 4. 核心分析函數 ---
@st.cache_data(ttl=3600)
def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="150d")
        if len(df) < 60: return None
        curr_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        pct = ((curr_price - prev_price) / prev_price) * 100
        ma5 = df['Close'].rolling(5).mean().iloc[-1]
        low_60 = df['Close'].tail(60).min()
        
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
        if is_bottom and curr_price > ma5 and chip_sum > 0: signal = "🔥 底部起漲"
        elif curr_price > ma5 and chip_sum > 0: signal = "🚀 多頭續強"
        elif curr_price < ma5 and chip_sum < 0: signal = "❄️ 轉弱觀望"
        else: signal = "☁️ 區間震盪"

        return {
            "股票標的": f"{ticker.replace('.TW','')} {get_stock_name(ticker)}",
            "現價": round(curr_price, 2),
            "漲跌幅(%)": round(pct, 2),
            "籌碼(K)": round(chip_sum, 1),
            "買賣建議": signal,
            "ticker": ticker
        }
    except: return None

# --- 5. 主介面 ---
st.title("🚀 AI 供應鏈投資決策系統")

# --- 修正後的新聞區塊 ---
st.subheader("📰 最新題材新聞 (自動偵測個股)")
news_data = get_latest_news()

if news_data:
    n_cols = st.columns(len(news_data))
    for i, n in enumerate(news_data):
        with n_cols[i]:
            st.markdown(f"**[{n['標題']}]({n['連結']})**")
            if n['相關代碼']:
                st.caption(f"提及個股: {', '.join(n['相關代碼'])}")
                if st.button(f"分析 {n['相關代碼'][0]}", key=f"news_btn_{i}"):
                    st.session_state.global_target = f"{n['相關代碼'][0]}.TW"
else:
    st.info("暫無最新新聞，請稍後再試。")

st.divider()

# 定義族群
WATCHLIST = {
    "我的持股": processed_my_stocks,
    "NVIDIA GB200 核心": ["2317.TW", "2382.TW", "6669.TW", "2308.TW", "3013.TW", "3324.TW", "3017.TW"],
    "CoWoS/先進封裝": ["3583.TW", "6187.TW", "3131.TW", "6223.TW", "2330.TW"],
    "IC設計/IP": ["3661.TW", "3443.TW", "2454.TW", "6643.TW", "3529.TW"],
    "矽光子/CPO": ["3450.TW", "3363.TW", "6442.TW", "3163.TW", "4979.TW"],
    "記憶體/載板": ["8299.TW", "2408.TW", "3260.TW", "3037.TW", "3189.TW"]
}

tabs = st.tabs(list(WATCHLIST.keys()))
all_tickers = []

for i, cat in enumerate(WATCHLIST.keys()):
    with tabs[i]:
        results = [analyze_stock(t) for t in WATCHLIST[cat] if analyze_stock(t)]
        df_summary = pd.DataFrame(results)
        if not df_summary.empty:
            def color_signal(v):
                if "買入" in v or "起漲" in v or "續強" in v: return 'color: #FF0000; font-weight: bold'
                if "賣出" in v or "轉弱" in v: return 'color: #00FF00; font-weight: bold'
                return ''
            st.dataframe(df_summary.style.applymap(color_signal, subset=['買賣建議']), use_container_width=True, hide_index=True)
            all_tickers.extend(WATCHLIST[cat])

# --- 6. 深度分析區 ---
st.divider()
if 'global_target' not in st.session_state: st.session_state.global_target = "2330.TW"
unique_tickers = list(dict.fromkeys(all_tickers))
if st.session_state.global_target not in unique_tickers:
    unique_tickers.insert(0, st.session_state.global_target)

target = st.selectbox("🎯 選擇分析標的：", unique_tickers, 
                      index=0,
                      format_func=lambda x: f"{x} {get_stock_name(x)}")

if target:
    s_obj = yf.Ticker(target)
    df_all = s_obj.history(period="1y")
    if not df_all.empty:
        for ma in [5, 10, 20, 60, 120]: df_all[f'MA{ma}'] = df_all['Close'].rolling(ma).mean()
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_all.index, open=df_all['Open'], high=df_all['High'], low=df_all['Low'], close=df_all['Close'], name="K線", increasing_line_color='#FF0000', decreasing_line_color='#00AA00'), row=1, col=1)
        ma_colors = {'MA5': '#FFD700', 'MA10': '#00BFFF', 'MA20': '#FF00FF', 'MA60': '#00FF00', 'MA120': '#FFFFFF'}
        for ma, color in ma_colors.items(): fig.add_trace(go.Scatter(x=df_all.index, y=df_all[ma], name=ma, line=dict(color=color, width=1.2)), row=1, col=1)
        vol_colors = ['#FF0000' if df_all['Close'].iloc[i] >= df_all['Open'].iloc[i] else '#00AA00' for i in range(len(df_all))]
        fig.add_trace(go.Bar(x=df_all.index, y=df_all['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

        try:
            q_fin = s_obj.quarterly_income_stmt.T
            if not q_fin.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("📊 獲利能力")
                    p_df = pd.DataFrame(index=q_fin.index)
                    rev = q_fin.get('Total Revenue', 0)
                    p_df['毛利率(%)'] = (q_fin.get('Gross Profit', 0) / rev * 100).round(2)
                    p_df['營益率(%)'] = (q_fin.get('Operating Income', 0) / rev * 100).round(2)
                    if 'Basic EPS' in q_fin.columns: p_df['EPS'] = q_fin['Basic EPS'].round(2)
                    p_df.index = [d.strftime('%Y-Q%q') for d in p_df.index]
                    st.table(p_df.head(4))
                with c2:
                    st.subheader("📈 營收走勢")
                    r_df = pd.DataFrame(index=q_fin.index)
                    r_df['季度營收'] = rev
                    r_df['YoY %'] = r_df['季度營收'].pct_change(-4).round(4) * 100
                    r_df.index = [d.strftime('%Y-Q%q') for d in r_df.index]
                    st.table(r_df.head(4).style.format({"季度營收": "{:,.0f}"}))
        except: st.write("財報讀取中...")
