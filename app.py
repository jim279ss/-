import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from FinMind.data import DataLoader

# --- 頁面設定 ---
st.set_page_config(page_title="AI 供應鏈投資決策系統", layout="wide")

# --- 1. 擴充版股票名稱對照表 (確保顯示中文) ---
STOCK_MAP = {
    # 核心指標
    "2330.TW": "台積電", "2317.TW": "鴻海", "3017.TW": "奇鋐", "3450.TW": "聯鈞",
    "NVDA": "NVIDIA", "TSM": "台積電ADR", "^SOX": "費城半導體",
    # 您截圖中的股票
    "2312.TW": "金寶", "2409.TW": "友達", "2520.TW": "冠德", "2609.TW": "陽明",
    "2634.TW": "漢翔", "2890.TW": "永豐金", "3051.TW": "鴻名", "3062.TW": "建漢",
    "4906.TW": "正文", "1216.TW": "統一", "2312.TW": "金寶", "2520.TW": "冠德",
    # NVIDIA GB200 供應鏈
    "2308.TW": "台達電", "2301.TW": "光寶科", "3013.TW": "晟銘電", "2382.TW": "廣達",
    "6669.TW": "緯穎", "3324.TW": "雙鴻", "3533.TW": "嘉澤", "2421.TW": "建準",
    "2059.TW": "川湖", "6274.TW": "台燿", "2368.TW": "金像電", "2376.TW": "技嘉",
    # IC設計/IP
    "3661.TW": "世芯-KY", "3443.TW": "創意", "6643.TW": "M31", "3529.TW": "力旺", 
    "2454.TW": "聯發科", "4966.TW": "譜瑞-KY", "3035.TW": "智原",
    # 矽光子/CPO
    "3363.TW": "上詮", "6442.TW": "光聖", "3163.TW": "波若威", "4979.TW": "華星光",
    # 記憶體/載板
    "8299.TW": "群聯", "2408.TW": "南亞科", "3260.TW": "威剛", "3037.TW": "欣興",
    "3189.TW": "景碩", "8046.TW": "南電", "6223.TW": "旺矽", "3583.TW": "辛耘"
}

def get_stock_name(ticker):
    # 優先從對照表找中文名
    if ticker in STOCK_MAP: return STOCK_MAP[ticker]
    try:
        # 如果找不到，從 Yahoo 抓取並清理名稱
        s = yf.Ticker(ticker)
        name = s.info.get('shortName', ticker)
        # 清理常見的英文後綴，讓畫面乾淨
        for suffix in [" CORPORATION", " CO LTD", " CO. LTD.", " INC.", " TECHNOLOGY", " ELECTRONICS"]:
            name = name.upper().replace(suffix, "")
        return name
    except: return ticker

# --- 2. 側邊欄：持股管理與記憶功能 ---
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

# --- 3. 核心分析函數 (籌碼 + 底部判斷) ---
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
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        low_60 = df['Close'].tail(60).min()
        
        chip_status = "未知"
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
                chip_status = "🔥 買進" if chip_sum > 0 else "❄️ 賣出"

        is_bottom = curr_price < (low_60 * 1.12)
        
        if is_bottom and curr_price > ma5 and chip_sum > 0:
            signal = "🔥 底部起漲"
        elif curr_price > ma5 > ma20 and chip_sum > 0:
            signal = "🚀 多頭續強"
        elif curr_price < ma5 and chip_sum < 0:
            signal = "❄️ 轉
