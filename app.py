import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="AI 供應鏈投資決策系統", layout="wide")

# --- 1. 股票名稱對照表 ---
STOCK_MAP = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "3017.TW": "奇鋐", "3450.TW": "聯鈞",
    "3661.TW": "世芯-KY", "3443.TW": "創意", "6643.TW": "M31", "3529.TW": "力旺", 
    "2454.TW": "聯發科", "NVDA": "NVIDIA", "TSM": "台積電ADR", "^SOX": "費城半導體"
}

def get_stock_name(ticker):
    if ticker in STOCK_MAP: return STOCK_MAP[ticker]
    try:
        s = yf.Ticker(ticker)
        return s.info.get('shortName', ticker)
    except: return ticker

# --- 2. 側邊欄：持股管理 ---
st.sidebar.header("👤 個人持股管理")
my_input = st.sidebar.text_input("輸入股票代碼 (多筆用逗號隔開)", "2330, 3017, 3450, NVDA")

# 處理輸入代碼
processed_my_stocks = []
for s in my_input.split(","):
    s = s.strip().upper()
    if not s: continue
    if s.isdigit() or (len(s) >= 4 and s[0:2] == "00"):
        if ".TW" not in s: s = f"{s}.TW"
    processed_my_stocks.append(s)

# --- 3. 資料抓取函數 (加入快取與錯誤處理) ---
@st.cache_data(ttl=600)
def get_summary_data(tickers):
    results = []
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            df = stock.history(period="2d")
            if len(df) < 2: continue
            curr = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            pct = ((curr - prev) / prev) * 100
            results.append({
                "股票標的": f"{t} {get_stock_name(t)}",
                "現價": round(curr, 2),
                "漲跌幅(%)": round(pct, 2),
                "ticker": t
            })
        except: continue
    return pd.DataFrame(results)

# --- 4. 主介面 ---
st.title("🚀 AI 供應鏈決策系統")

WATCHLIST = {
    "我的持股": processed_my_stocks,
    "AI 核心指標": ["^SOX", "NVDA", "TSM", "2330.TW"],
    "IC設計/IP": ["3661.TW", "3443.TW", "2454.TW", "6643.TW", "3529.TW"],
    "矽光子/CPO": ["3450.TW", "3363.TW", "6442.TW", "3163.TW", "4979.TW"],
    "散熱/伺服器": ["3017.TW", "3324.TW", "6669.TW", "2382.TW", "3013.TW"]
}

# 建立分頁
tabs = st.tabs(list(WATCHLIST.keys()))
selected_stock = None

for i, cat in enumerate(WATCHLIST.keys()):
    with tabs[i]:
        with st.spinner(f'正在讀取 {cat} 資料...'):
            df_summary = get_summary_data(WATCHLIST[cat])
            
            if not df_summary.empty:
                # 漲跌顏色設定
                def color_pct(v):
                    if v > 0: return 'color: #FF0000; font-weight: bold'
                    if v < 0: return 'color: #00AA00; font-weight: bold'
                    return ''
                
                st.dataframe(df_summary.style.applymap(color_pct, subset=['漲跌幅(%)']), use_container_width=True, hide_index=True)
                
                # 選擇分析標的
                sel = st.selectbox("點擊選擇要分析的股票", df_summary['ticker'].tolist(), 
                                   format_func=lambda x: f"{x} {get_stock_name(x)}", key=f"sel_{cat}")
                if sel: selected_stock = sel
            else:
                st.warning(f"目前 {cat} 暫無資料，請確認代碼是否正確。")

# --- 5. 詳細分析區 (K線 + 財報) ---
if selected_stock:
    st.divider()
    st.header(f"🔍 深度分析：{selected_stock} {get_stock_name(selected_stock)}")
    
    with st.spinner('正在繪製 K 線圖與抓取財報...'):
        s_obj = yf.Ticker(selected_stock)
        df_all = s_obj.history(period="1y")
        
        if not df_all.empty:
            # 計算均線
            for ma in [5, 10, 20, 60, 120]:
                df_all[f'MA{ma}'] = df_all['Close'].rolling(ma).mean()

            # --- A. 專業 K 線圖 ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(
                x=df_all.index, open=df_all['Open'], high=df_all['High'], low=df_all['Low'], close=df_all['Close'],
                name="K線", increasing_line_color='#FF0000', decreasing_line_color='#00AA00'
            ), row=1, col=1)
            
            ma_colors = {'MA5': '#FFD700', 'MA10': '#00BFFF', 'MA20': '#FF00FF', 'MA60': '#00FF00', 'MA120': '#FFFFFF'}
            for ma, color in ma_colors.items():
                fig.add_trace(go.Scatter(x=df_all.index, y=df_all[ma], name=ma, line=dict(color=color, width=1.2)), row=1, col=1)
            
            vol_colors = ['#FF0000' if df_all['Close'].iloc[i] >= df_all['Open'].iloc[i] else '#00AA00' for i in range(len(df_all))]
            fig.add_trace(go.Bar(x=df_all.index, y=df_all['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)
            
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

            # --- B. 財務報表區 ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 獲利能力 (季度)")
                try:
                    q_fin = s_obj.quarterly_income_stmt.T
                    if not q_fin.empty:
                        p_df = pd.DataFrame(index=q_fin.index)
                        rev = q_fin.get('Total Revenue', 0)
                        p_df['毛利率(%)'] = (q_fin.get('Gross Profit', 0) / rev * 100).round(2)
                        p_df['營益率(%)'] = (q_fin.get('Operating Income', 0) / rev * 100).round(2)
                        p_df['稅後淨利率(%)'] = (q_fin.get('Net Income', 0) / rev * 100).round(2)
                        if 'Basic EPS' in q_fin.columns: p_df['EPS(元)'] = q_fin['Basic EPS'].round(2)
                        p_df.index = [d.strftime('%Y-Q%q') if hasattr(d, 'strftime') else d for d in p_df.index]
                        st.table(p_df.head(6))
                    else: st.write("無財報數據")
                except: st.write("財報讀取失敗")

            with col2:
                st.subheader("📈 營收走勢 (季度)")
                try:
                    r_df = pd.DataFrame(index=q_fin.index)
                    r_df['季度營收'] = rev
                    r_df['年增率(YoY %)'] = r_df['季度營收'].pct_change(-4).round(4) * 100
                    r_df.index = [d.strftime('%Y-Q%q') if hasattr(d, 'strftime') else d for d in r_df.index]
                    st.table(r_df.head(6).style.format({"季度營收": "{:,.0f}"}))
                except: st.write("營收數據讀取失敗")
        else:
            st.error("無法載入該股票的歷史資料。")

st.sidebar.markdown("---")
st.sidebar.write("🔴 **紅漲** | 🟢 **綠跌**")
if st.sidebar.button("手動重新整理資料"):
    st.cache_data.clear()
    st.rerun()
