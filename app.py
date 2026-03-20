import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="AI 供應鏈投資決策系統", layout="wide")

# --- 1. 股票名稱對照與自動抓取 ---
STOCK_MAP = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "3017.TW": "奇鋐", "3450.TW": "聯鈞",
    "3661.TW": "世芯-KY", "3443.TW": "創意", "6643.TW": "M31", "3529.TW": "力旺", 
    "2454.TW": "聯發科", "NVDA": "NVIDIA", "TSM": "台積電ADR", "^SOX": "費城半導體"
}

def get_stock_name(ticker):
    if ticker in STOCK_MAP:
        return STOCK_MAP[ticker]
    try:
        info = yf.Ticker(ticker).info
        name = info.get('shortName') or info.get('longName') or "未知"
        return name
    except:
        return "未知"

# --- 2. 側邊欄：持股管理 ---
st.sidebar.header("👤 個人持股管理")
my_input = st.sidebar.text_input("輸入股票代碼 (多筆用逗號隔開)", "2330, 3017, 3450, 00679B")

# 處理輸入代碼：如果是純數字或特定代碼則補上 .TW
processed_my_stocks = []
for s in my_input.split(","):
    s = s.strip().upper()
    if not s: continue
    if s.isdigit() or (len(s) >= 5 and s[0:2].isdigit()): # 處理 2330 或 00679B
        s = f"{s}.TW"
    processed_my_stocks.append(s)

# --- 3. 核心功能函數 ---
@st.cache_data(ttl=3600)
def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y")
    return stock, df

# --- 4. 主介面 ---
st.title("🚀 AI 供應鏈決策系統")

# 族群定義
WATCHLIST = {
    "我的持股": processed_my_stocks,
    "AI 核心指標": ["^SOX", "NVDA", "TSM", "2330.TW"],
    "IC設計/IP": ["3661.TW", "3443.TW", "2454.TW", "6643.TW", "3529.TW"],
    "矽光子/CPO": ["3450.TW", "3363.TW", "6442.TW", "3163.TW", "4979.TW"],
    "散熱/伺服器": ["3017.TW", "3324.TW", "6669.TW", "2382.TW", "3013.TW"]
}

tabs = st.tabs(list(WATCHLIST.keys()))
selected_stock = None

for i, cat in enumerate(WATCHLIST.keys()):
    with tabs[i]:
        tickers = WATCHLIST[cat]
        if not tickers:
            st.write("請在左側輸入持股代碼")
            continue
            
        # 簡易清單表格
        summary_data = []
        for t in tickers:
            try:
                s_obj, s_hist = fetch_stock_data(t)
                curr = s_hist['Close'].iloc[-1]
                prev = s_hist['Close'].iloc[-2]
                pct = ((curr - prev) / prev) * 100
                summary_data.append({
                    "股票標的": f"{t} {get_stock_name(t)}",
                    "現價": round(curr, 2),
                    "漲跌幅(%)": round(pct, 2),
                    "ticker": t
                })
            except: continue
        
        df_summary = pd.DataFrame(summary_data)
        
        def color_pct(v):
            if v > 0: return 'color: #FF0000; font-weight: bold'
            if v < 0: return 'color: #00AA00; font-weight: bold'
            return ''
        
        st.dataframe(df_summary.style.applymap(color_pct, subset=['漲跌幅(%)']), use_container_width=True, hide_index=True)
        selected_stock = st.selectbox(f"選擇分析標的 ({cat})", tickers, format_func=lambda x: f"{x} {get_stock_name(x)}", key=f"sb_{cat}")

# --- 5. 詳細分析區 (K線 + 財報) ---
if selected_stock:
    st.divider()
    stock_obj, df_all = fetch_stock_data(selected_stock)
    
    # 計算均線
    df_all['MA5'] = df_all['Close'].rolling(5).mean()
    df_all['MA10'] = df_all['Close'].rolling(10).mean()
    df_all['MA20'] = df_all['Close'].rolling(20).mean()
    df_all['MA60'] = df_all['Close'].rolling(60).mean()
    df_all['MA120'] = df_all['Close'].rolling(120).mean()

    # --- A. 專業 K 線圖 ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    # K線
    fig.add_trace(go.Candlestick(
        x=df_all.index, open=df_all['Open'], high=df_all['High'], low=df_all['Low'], close=df_all['Close'],
        name="K線", increasing_line_color='#FF0000', decreasing_line_color='#00AA00'
    ), row=1, col=1)
    
    # 均線配色 (對齊截圖)
    ma_colors = {'MA5': '#FFD700', 'MA10': '#00BFFF', 'MA20': '#FF00FF', 'MA60': '#00FF00', 'MA120': '#FFFFFF'}
    for ma, color in ma_colors.items():
        fig.add_trace(go.Scatter(x=df_all.index, y=df_all[ma], name=ma, line=dict(color=color, width=1.5)), row=1, col=1)
    
    # 成交量 (漲紅跌綠)
    colors = ['#FF0000' if df_all['Close'].iloc[i] >= df_all['Open'].iloc[i] else '#00AA00' for i in range(len(df_all))]
    fig.add_trace(go.Bar(x=df_all.index, y=df_all['Volume'], name="成交量", marker_color=colors), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # --- B. 財務報表區 ---
    st.header(f"📊 財務分析：{get_stock_name(selected_stock)}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("獲利能力 (季度)")
        try:
            q_fin = stock_obj.quarterly_financials.T
            q_bs = stock_obj.quarterly_balance_sheet.T
            
            # 計算比率
            profit_df = pd.DataFrame(index=q_fin.index)
            rev = q_fin.get('Total Revenue', 1)
            profit_df['毛利率(%)'] = (q_fin.get('Gross Profit', 0) / rev * 100).round(2)
            profit_df['營益率(%)'] = (q_fin.get('Operating Income', 0) / rev * 100).round(2)
            profit_df['淨利率(%)'] = (q_fin.get('Net Income Common Stockholders', 0) / rev * 100).round(2)
            profit_df['EPS'] = stock_obj.quarterly_earnings.iloc[:,0].values if hasattr(stock_obj, 'quarterly_earnings') else "N/A"
            
            st.dataframe(profit_df.head(6), use_container_width=True)
        except:
            st.write("暫無獲利能力數據")

    with col2:
        st.subheader("營收走勢 (季度)")
        try:
            rev_df = pd.DataFrame(index=q_fin.index)
            rev_df['季度營收'] = q_fin.get('Total Revenue', 0)
            rev_df['年增率(YoY)'] = rev_df['季度營收'].pct_change(-4).round(4) * 100 # 與去年同季比
            
            st.dataframe(rev_df.head(6).style.format({"季度營收": "{:,.0f}"}), use_container_width=True)
        except:
            st.write("暫無營收數據")

st.sidebar.markdown("---")
st.sidebar.write("💡 **操作提示**：")
st.sidebar.write("1. 輸入代碼如 `2330` 或 `NVDA`。")
st.sidebar.write("2. 下方表格點選股票後，會自動載入 K 線與財報。")
