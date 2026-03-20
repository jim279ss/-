import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from FinMind.data import DataLoader

# --- 頁面設定 ---
st.set_page_config(page_title="AI 高毛利產業追蹤", layout="wide")

# --- 1. 定義追蹤清單 (依您的需求分類) ---
WATCHLIST = {
    "全球指標": ["^SOX", "NVDA", "TSM", "AVGO", "ARM"],
    "IC設計/IP (高毛利)": ["3661.TW", "3443.TW", "2454.TW", "6643.TW", "3529.TW", "6415.TW"],
    "矽光子/CPO": ["3450.TW", "3363.TW", "6442.TW", "3163.TW", "4977.TW", "4908.TW"],
    "散熱/伺服器": ["3017.TW", "3324.TW", "6669.TW", "2382.TW", "2317.TW", "8996.TW"],
    "記憶體/HBM": ["8299.TW", "2408.TW", "3260.TW", "6223.TW", "6510.TW"],
    "載板/ABF": ["3037.TW", "3189.TW", "8046.TW"]
}

# --- 2. 資料抓取函數 ---
@st.cache_data(ttl=3600)
def get_stock_data(tickers):
    # 抓取兩天資料計算漲跌
    data = yf.download(tickers, period="5d", interval="1d")
    summary = []
    for ticker in tickers:
        try:
            curr_close = data['Close'][ticker].iloc[-1]
            prev_close = data['Close'][ticker].iloc[-2]
            change_pct = ((curr_close - prev_close) / prev_close) * 100
            vol = data['Volume'][ticker].iloc[-1]
            summary.append({
                "代碼": ticker,
                "現價": round(curr_close, 2),
                "漲跌幅(%)": round(change_pct, 2),
                "成交量": int(vol)
            })
        except:
            continue
    return pd.DataFrame(summary)

# --- 3. 籌碼資料 (FinMind 免費介面) ---
def get_chip_data(stock_id):
    dl = DataLoader()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    try:
        df = dl.taiwan_stock_institutional_investors(
            stock_id=stock_id.replace(".TW", ""),
            start_date=start_date,
            end_date=end_date
        )
        # 彙整三大法人合計 (單位：張)
        df['net_buy'] = (df['buy'] - df['sell']) / 1000 
        return df
    except:
        return pd.DataFrame()

# --- 4. 網頁介面 ---
st.title("🚀 AI 供應鏈 & 高毛利產業追蹤")
st.caption(f"最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (資料來源: Yahoo Finance / FinMind)")

# --- 第一區塊：全球風向球 ---
st.subheader("🌍 全球 AI 風向球")
global_data = get_stock_data(WATCHLIST["全球指標"])
cols = st.columns(len(global_data))
for i, row in global_data.iterrows():
    cols[i].metric(row['代碼'], f"{row['現價']}", f"{row['漲跌幅(%)']}%")

st.divider()

# --- 第二區塊：台股族群分頁 ---
st.subheader("🇹🇼 台股核心族群監控")
tabs = st.tabs(list(WATCHLIST.keys())[1:])

for i, category in enumerate(list(WATCHLIST.keys())[1:]):
    with tabs[i]:
        col_left, col_right = st.columns([2, 3])
        
        group_tickers = WATCHLIST[category]
        df_group = get_stock_data(group_tickers)
        
        with col_left:
            st.write(f"**{category} 即時行情**")
            st.dataframe(
                df_group.style.background_gradient(subset=['漲跌幅(%)'], cmap='RdYlGn'),
                use_container_width=True,
                hide_index=True
            )
        
        with col_right:
            # 預設顯示該族群第一檔標的的籌碼
            target = st.selectbox(f"選擇標的查看籌碼 (三大法人)", group_tickers, key=f"select_{category}")
            chip_df = get_chip_data(target)
            
            if not chip_df.empty:
                fig = go.Figure()
                for name in ['外資', '投信', '自營商']:
                    sub_df = chip_df[chip_df['name'] == name]
                    fig.add_trace(go.Bar(x=sub_df['date'], y=sub_df['net_buy'], name=name))
                
                fig.update_layout(
                    title=f"{target} 近期法人買賣超 (單位:千張)",
                    barmode='group',
                    height=350,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("今日籌碼資料尚未更新或該股無資料")

# --- 側邊欄：每日題材與筆記 ---
with st.sidebar:
    st.header("📝 每日追蹤筆記")
    st.info("💡 **高毛利觀察重點：**\n1. IC設計 > 40%\n2. 矽光子 > 30%\n3. 散熱液冷 > 25%")
    
    st.text_area("今日熱門題材流向：", placeholder="例如：資金從散熱流向矽光子...", height=150)
    st.text_area("關注指標股異動：", placeholder="例如：世芯-KY 突破月線...", height=150)
    
    if st.button("儲存今日觀察"):
        st.success("已記錄！(註：此為暫存，重新整理網頁會清空)")

    st.markdown("---")
    st.write("🔍 **常用工具連結：**")
    st.write("[玩股網-三大法人](https://www.wantgoo.com/stock/institutional-investors/summary)")
    st.write("[公開資訊觀測站](https://mops.twse.com.tw/mops/web/index)")
