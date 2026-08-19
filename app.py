import streamlit as st
import pandas as pd
import datetime

# 頁面標題與排版設定
st.set_page_config(page_title="隔日沖主力短空監控雷達", layout="wide", page_icon="🎯")

st.title("🎯 每日隔日沖主力出手標的（短空觀察名單）")
st.caption("自動追蹤知名隔日沖分點（凱基台北、美林、元大土城永寧、富邦建國等）鎖碼強勢股，作為隔日早盤短空策略依據。")

# 知名隔日沖主力分點清單
TARGET_BROKERS = [
    "凱基-台北", 
    "美商美林", 
    "元大-土城永寧", 
    "富邦-建國", 
    "元大-總公司", 
    "統一-敦南"
]

# 側邊欄篩選設定
st.sidebar.header("🔍 篩選條件設定")
min_ratio = st.sidebar.slider("隔日沖買超佔成交量比例 (%) 門檻：", min_value=5, max_value=40, value=10, step=1)
selected_brokers = st.sidebar.multiselect("監控主力分點：", options=TARGET_BROKERS, default=TARGET_BROKERS)

# 模擬/示範資料生成函數（上線後可替換為券商API/證交所盤後爬蟲）
def get_daily_overnight_data():
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # 範例結構：展示當日鎖碼大戶
    data = [
        {"股票代號": "2492", "股票名稱": "華新科", "收盤價": 298.5, "漲跌幅": "+9.94%", "隔日沖分點": "凱基-台北", "買超張數": 3850, "佔成交量比例(%)": 18.5, "融券餘額變化": "+120", "軋空風險": "中"},
        {"股票代號": "4551", "股票名稱": "智伸科", "收盤價": 142.0, "漲跌幅": "+8.40%", "隔日沖分點": "美商美林", "買超張數": 1200, "佔成交量比例(%)": 12.3, "融券餘額變化": "-45", "軋空風險": "低"},
        {"股票代號": "3037", "股票名稱": "欣興", "收盤價": 185.5, "漲跌幅": "+9.76%", "隔日沖分點": "元大-土城永寧", "買超張數": 4200, "佔成交量比例(%)": 15.1, "融券餘額變化": "+890", "軋空風險": "高 (慎防軋空)"},
        {"股票代號": "2383", "股票名稱": "台光電", "收盤價": 465.0, "漲跌幅": "+6.20%", "隔日沖分點": "富邦-建國", "買超張數": 980, "佔成交量比例(%)": 8.7, "融券餘額變化": "+15", "軋空風險": "低"},
    ]
    return pd.DataFrame(data), today_str

df, update_date = get_daily_overnight_data()

# 篩選資料
filtered_df = df[
    (df["佔成交量比例(%)"] >= min_ratio) & 
    (df["隔日沖分點"].isin(selected_brokers))
]

# 顯示數據指標
col1, col2, col3 = st.columns(3)
col1.metric("更新日期", update_date)
col2.metric("符合條件標的數", f"{len(filtered_df)} 檔")
col3.metric("監控主力分點數", f"{len(selected_brokers)} 家")

st.markdown("---")

# 顯示主表格
st.subheader("📊 盤後篩選結果")
if not filtered_df.empty:
    st.dataframe(
        filtered_df.style.highlight_max(axis=0, subset=["佔成交量比例(%)"], color="#ffcdd2"),
        use_container_width=True
    )
else:
    st.warning("目前沒有符合設定門檻的標的。")

st.markdown("---")

# 短空操作 SOP 提示卡
st.subheader("💡 隔日早盤短空 SOP 紀律提醒")
st.info("""
1. **09:00~09:15 觀察開盤**：若開高 2%~4% 但第一根 5 分 K 爆量收長黑跌破開盤價，可順勢進場。
2. **均價線防守**：股價跌破當日分時均價線（VWAP）才確認轉弱；若帶量突破當日高點，**嚴格立即停損**。
3. **避開高軋空標的**：標註「高軋空風險」的股票，隔日可能繼續被鎖漲停，切勿逆勢摸頂。
""")
