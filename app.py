import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from FinMind.data import DataLoader

# --- 頁面設定 ---
st.set_page_config(page_title="AI 供應鏈投資決策儀表板", layout="wide")

# --- 1. 擴充版追蹤清單 (含名稱對照) ---
STOCK_MAP = {
    # 我的持股 (請在此自行修改代碼)
    "2330.TW": "台積電", "2317.TW": "鴻海", "3017.TW": "奇鋐",
    # IC設計/IP
    "3661.TW": "世芯-KY", "3443.TW": "創意", "6643.TW": "M31", "3529.TW": "力旺", "2454.TW": "聯發科", "6415.TW": "矽力*-KY", "8054.TW": "安國", "6666.TW": "羅昇",
    # 矽光子
    "3450.TW": "聯鈞", "3363.TW": "上詮", "6442.TW": "光聖", "3163.TW": "波若威", "4977.TW": "眾達-KY", "4908.TW": "前鼎", "3081.TW": "聯亞",
    # 散熱/伺服器
    "3324.TW": "雙鴻", "6669.TW": "緯穎", "2382.TW": "廣達", "2376.TW": "技嘉", "8996.TW": "高力", "3013.TW": "晟銘電", "3533.TW": "嘉澤",
    # 記憶體/載板
    "8299.TW": "群聯", "2408.TW": "南亞科", "3260.TW": "威剛", "6223.TW": "旺矽", "3037.TW": "欣興", "3189.TW": "景碩", "8046.TW": "南電",
    # 全球指標
    "^SOX": "費城半導體", "NVDA": "NVIDIA", "TSM": "台積電ADR"
}

WATCHLIST = {
    "我的持股": ["2330.TW", "3017.TW"], # <--- 這裡填入您手上的股票
    "IC設計/IP": ["3661.TW", "3443.TW", "2454.TW", "6643.TW", "3529.TW", "8054.TW"],
    "矽光子/CPO": ["3450.TW", "3363.TW", "6442.TW", "3163.TW", "4977.TW", "3081.TW"],
    "散熱/伺服器": ["3017.TW", "3324.TW", "6669.TW", "2382.TW", "2376.TW", "3013.TW", "3533.TW"],
    "記憶體/載板": ["8299.TW", "2408.TW", "3260.TW", "6223.TW", "3037.TW", "3189.TW", "8046.TW"]
}

# --- 2. 核心功能：判斷買賣點 ---
def get_signal(df_hist, chip_df):
    """
    簡單邏輯：
    買入：股價 > 5MA 且 5MA > 20MA (多頭) + 法人近三日買超
    賣出：股價 < 5MA 且 5MA < 20MA (空頭) + 法人近三日賣超
    """
    try:
        curr_price = df_hist['Close'].iloc[-1]
        ma5 = df_hist['Close'].rolling(5).mean().iloc[-1]
        ma20 = df_hist['Close'].rolling(20).mean().iloc[-1]
        
        # 籌碼判斷 (近3日法人合計)
        chip_sum = 0
        if not chip_df.empty:
            chip_sum = chip_df.tail(9)['net_buy'].sum() # 3天*3大法人
            
        if curr_price > ma5 > ma20 and chip_sum > 0:
            return "🔥 建議買入 (多頭+籌碼集中)"
        elif curr_price < ma5 < ma20 and chip_sum < 0:
            return "❄️ 建議觀望 (空頭+籌碼流失)"
        else:
            return "☁️ 持平/震盪"
    except:
        return "資料不足"

# --- 3. 資料抓取 ---
@st.cache_data(ttl=3600)
def fetch_data(tickers):
    data = yf.download(tickers, period="60d", interval="1d")
    summary = []
    dl = DataLoader()
    
    for ticker in tickers:
        try:
            hist = data.loc[:, (slice(None), ticker)]
            hist.columns = hist.columns.droplevel(1)
            
            curr_close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change = curr_close - prev_close
            change_pct = (change / prev_close) * 100
            
            # 抓取籌碼
            chip_df = pd.DataFrame()
            if ".TW" in ticker:
                start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
                chip_df = dl.taiwan_stock_institutional_investors(
                    stock_id=ticker.replace(".TW", ""),
                    start_date=start_date,
                    end_date=datetime.now().strftime('%Y-%m-%d')
                )
                chip_df['net_buy'] = (chip_df['buy'] - chip_df['sell']) / 1000

            signal = get_signal(hist, chip_df)
            
            summary.append({
                "代碼": ticker,
                "名稱": STOCK_MAP.get(ticker, "未知"),
                "現價": float(f"{curr_close:.2f}"),
                "漲跌": float(f"{change:.2f}"),
                "漲跌幅(%)": float(f"{change_pct:.2f}"),
                "建議訊號": signal
            })
        except:
            continue
    return pd.DataFrame(summary)

# --- 4. 網頁介面 ---
st.title("📈 AI 供應鏈決策儀表板")

# 全球指標 (置頂)
st.subheader("🌍 全球市場風向")
global_df = fetch_data(["^SOX", "NVDA", "TSM"])
cols = st.columns(len(global_df))
for i, row in global_data := global_df.iterrows():
    # 台股配色：漲紅跌綠
    color = "inverse" if row['漲跌幅(%)'] >= 0 else "normal" 
    cols[i].metric(f"{row['名稱']} ({row['代碼']})", f"{row['現價']}", f"{row['漲跌幅(%)']}%", delta_color=color)

st.divider()

# 族群監控
tabs = st.tabs(list(WATCHLIST.keys()))

for i, category in enumerate(list(WATCHLIST.keys())):
    with tabs[i]:
        df = fetch_data(WATCHLIST[category])
        
        # 自定義表格樣式 (台股配色)
        def color_df(val):
            if isinstance(val, float):
                if val > 0: return 'color: #FF0000; font-weight: bold' # 紅色
                if val < 0: return 'color: #008000; font-weight: bold' # 綠色
            return 'color: white'

        st.dataframe(
            df.style.applymap(color_df, subset=['漲跌', '漲跌幅(%)']),
            use_container_width=True,
            hide_index=True,
            column_config={
                "現價": st.column_config.NumberColumn(format="%.2f"),
                "漲跌": st.column_config.NumberColumn(format="%.2f"),
                "漲跌幅(%)": st.column_config.NumberColumn(format="%.2f"),
            }
        )

st.sidebar.header("💡 投資心法")
st.sidebar.write("""
**買入邏輯：**
1. 下跌後底部放量。
2. 股價站上 5MA 且 5MA 向上穿過 20MA。
3. 三大法人(尤其是投信)開始連買。

**賣出邏輯：**
1. 股價跌破 5MA 且 5MA 向下。
2. 法人高檔大額調節。
""")

st.sidebar.warning("⚠️ 本工具僅供參考，投資前請自行評估風險。")
