import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from FinMind.data import DataLoader

# --- 頁面設定 ---
st.set_page_config(page_title="AI 供應鏈投資決策系統", layout="wide")

# --- 1. 股票名稱對照表 ---
STOCK_MAP = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "3017.TW": "奇鋐", "3450.TW": "聯鈞",
    "3661.TW": "世芯-KY", "3443.TW": "創意", "6643.TW": "M31", "3529.TW": "力旺", 
    "2454.TW": "聯發科", "6415.TW": "矽力*-KY", "8054.TW": "安國", "6666.TW": "羅昇",
    "3035.TW": "智原", "8227.TW": "巨有科技", "6533.TW": "晶心科", "3363.TW": "上詮", 
    "6442.TW": "光聖", "3163.TW": "波若威", "4977.TW": "眾達-KY", "4908.TW": "前鼎", 
    "3081.TW": "聯亞", "4979.TW": "華星光", "3324.TW": "雙鴻", "6669.TW": "緯穎", 
    "2382.TW": "廣達", "2376.TW": "技嘉", "8996.TW": "高力", "3013.TW": "晟銘電", 
    "3533.TW": "嘉澤", "2301.TW": "光寶科", "2421.TW": "建準", "6230.TW": "超眾",
    "8299.TW": "群聯", "2408.TW": "南亞科", "3260.TW": "威剛", "6223.TW": "旺矽", 
    "3037.TW": "欣興", "3189.TW": "景碩", "8046.TW": "南電", "3583.TW": "辛耘",
    "^SOX": "費城半導體", "NVDA": "NVIDIA", "TSM": "台積電ADR"
}

# 預設追蹤清單
DEFAULT_WATCHLIST = {
    "IC設計/IP": ["3661.TW", "3443.TW", "2454.TW", "6643.TW", "3529.TW", "8054.TW"],
    "矽光子/CPO": ["3450.TW", "3363.TW", "6442.TW", "3163.TW", "4979.TW"],
    "散熱/伺服器": ["3017.TW", "3324.TW", "6669.TW", "2382.TW", "3013.TW", "3533.TW"],
    "記憶體/載板": ["8299.TW", "2408.TW", "3260.TW", "6223.TW", "3037.TW", "3189.TW"]
}

# --- 2. 側邊欄：持股管理 ---
st.sidebar.header("👤 個人持股管理")
my_input = st.sidebar.text_input("輸入股票代碼 (逗號隔開)", "2330,3017,3450")
my_stocks = [f"{s.strip()}.TW" for s in my_input.split(",") if s.strip()]

# --- 3. 核心功能函數 ---
def get_signal(df_hist, chip_df):
    try:
        curr_price = df_hist['Close'].iloc[-1]
        ma5 = df_hist['Close'].rolling(5).mean().iloc[-1]
        low_60 = df_hist['Close'].tail(60).min()
        chip_sum = chip_df.tail(9)['net_buy'].sum() if not chip_df.empty else 0
        
        if curr_price > ma5 and chip_sum > 0 and (curr_price < low_60 * 1.15):
            return "🔥 建議買入"
        elif curr_price < ma5 and chip_sum < 0:
            return "❄️ 建議賣出"
        return "☁️ 觀望"
    except: return "計算中"

@st.cache_data(ttl=3600)
def fetch_summary(tickers):
    data = yf.download(tickers, period="150d", interval="1d")
    summary = []
    dl = DataLoader()
    for ticker in tickers:
        try:
            hist = data.loc[:, (slice(None), ticker)] if len(tickers) > 1 else data
            hist.columns = hist.columns.droplevel(1) if len(tickers) > 1 else hist.columns
            
            curr_close = hist['Close'].iloc[-1]
            change_pct = ((curr_close - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
            
            chip_df = pd.DataFrame()
            if ".TW" in ticker:
                chip_df = dl.taiwan_stock_institutional_investors(
                    stock_id=ticker.replace(".TW", ""),
                    start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
                    end_date=datetime.now().strftime('%Y-%m-%d')
                )
                chip_df['net_buy'] = (chip_df['buy'] - chip_df['sell']) / 1000

            summary.append({
                "股票標的": f"{ticker.replace('.TW','')} {STOCK_MAP.get(ticker, '未知')}",
                "現價": round(curr_close, 2),
                "漲跌幅(%)": round(change_pct, 2),
                "建議訊號": get_signal(hist, chip_df),
                "raw_ticker": ticker
            })
        except: continue
    return pd.DataFrame(summary)

# --- 4. 主介面 ---
st.title("🚀 AI 供應鏈決策系統")

# 全球指標
g_df = fetch_summary(["^SOX", "NVDA", "TSM"])
cols = st.columns(3)
for i, row in g_df.iterrows():
    color = "inverse" if row['漲跌幅(%)'] >= 0 else "normal"
    cols[i].metric(row['股票標的'], row['現價'], f"{row['漲跌幅(%)']}%", delta_color=color)

st.divider()

# 族群表格
all_categories = {"我的持股": my_stocks}
all_categories.update(DEFAULT_WATCHLIST)
tabs = st.tabs(list(all_categories.keys()))

selected_stock = None

for i, cat in enumerate(all_categories.keys()):
    with tabs[i]:
        df = fetch_summary(all_categories[cat])
        def color_val(v):
            if isinstance(v, float):
                if v > 0: return 'color: #FF0000'
                if v < 0: return 'color: #00AA00'
            return ''
        
        st.write("💡 點擊下方股票代碼可查看詳細 K 線與財報")
        st.dataframe(df.style.applymap(color_val, subset=['漲跌幅(%)']), use_container_width=True, hide_index=True)
        selected_stock = st.selectbox(f"選擇要分析的股票 ({cat})", all_categories[cat], format_func=lambda x: f"{x} {STOCK_MAP.get(x,'')}")

# --- 5. 詳細分析區 (K線 + 財報) ---
if selected_stock:
    st.divider()
    st.header(f"🔍 詳細分析：{selected_stock} {STOCK_MAP.get(selected_stock,'')}")
    
    # 抓取歷史資料
    df_all = yf.download(selected_stock, period="1y", interval="1d")
    
    # 計算均線
    for ma in [5, 10, 20, 60, 120]:
        df_all[f'MA{ma}'] = df_all['Close'].rolling(ma).mean()
    
    # 繪製 K 線圖
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # K線
    fig.add_trace(go.Candlestick(x=df_all.index, open=df_all['Open'], high=df_all['High'], low=df_all['Low'], close=df_all['Close'], name="K線"), row=1, col=1)
    
    # 均線
    for ma in [5, 10, 20, 60, 120]:
        fig.add_trace(go.Scatter(x=df_all.index, y=df_all[f'MA{ma}'], name=f'{ma}MA', line=dict(width=1)), row=1, col=1)
    
    # 成交量
    fig.add_trace(go.Bar(x=df_all.index, y=df_all['Volume'], name="成交量", marker_color='gray'), row=2, col=1)
    
    fig.update_layout(height=600, title=f"{selected_stock} 日K線圖 (含均線與成交量)", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # 財報區
    st.subheader("📊 核心財報數據")
    stock_info = yf.Ticker(selected_stock)
    
    try:
        # 抓取年度財務數據
        fin = stock_info.financials.T
        if not fin.empty:
            display_fin = fin[['Total Revenue', 'Net Income']].copy()
            display_fin.columns = ['總營收', '淨利']
            st.write("**年度損益簡表 (單位: 元)**")
            st.table(display_fin.head(4))
        else:
            st.warning("無法取得該標的之詳細財報數據。")
    except:
        st.error("財報資料抓取失敗。")

st.sidebar.markdown("---")
st.sidebar.write("🔴 **紅漲** | 🟢 **綠跌**")
