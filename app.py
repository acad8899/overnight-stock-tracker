import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ==============================================================================
# 系統設定與頁面佈局
# ==============================================================================
st.set_page_config(
    page_title="台股隔日沖主力成本 × 短空決策雷達",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義 CSS
st.markdown("""
<style>
    .main-metric-card {
        background-color: #1E222D;
        border-radius: 8px;
        padding: 12px 16px;
        border: 1px solid #2A2E39;
    }
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2026-08-28 官方盤後最新主力籌碼資料庫 (適用 2026-08-31 交易日)
# ==============================================================================
DEFAULT_WATCHLIST = [
    {
        "code": "2492", "name": "華新科", "has_futures": True,
        "close": 313.50, "high": 313.50, "low": 295.50, "volume": 52649,
        "main_buy_vol": 11055, "main_buy_cost": 312.38, "main_ratio": 21.00,
        "top_brokers": ["富邦", "凱基-城中", "凱基-台北", "國票-安和", "國票-敦北法人", "統一", "統一-城中", "摩根大通"],
        "top_seller": "國泰-敦南 (-646張)",
        "margin_diff": 1420, "margin_label": "融資大增 (浮額沉重/易多殺多)",
        "short_ratio": 4.1, "score": 95,
        "nh": 321.0, "ah": 329.0, "status": "待開盤"
    },
    {
        "code": "3406", "name": "玉晶光", "has_futures": True,
        "close": 917.00, "high": 917.00, "low": 831.00, "volume": 14487,
        "main_buy_vol": 3077, "main_buy_cost": 886.82, "main_ratio": 21.24,
        "top_brokers": ["美林", "富邦", "美商高盛", "群益金鼎-台北", "國泰", "新加坡商瑞銀", "永豐金-敦南", "凱基-台北"],
        "top_seller": "國票-安和 (-492張)",
        "margin_diff": -883, "margin_label": "融資退潮 (散戶離場/高檔軋空)",
        "short_ratio": 3.4, "score": 88,
        "nh": 932.0, "ah": 948.0, "status": "待開盤"
    },
    {
        "code": "2408", "name": "南亞科", "has_futures": True,
        "close": 540.00, "high": 569.00, "low": 531.00, "volume": 77043,
        "main_buy_vol": 4913, "main_buy_cost": 548.91, "main_ratio": 6.38,
        "top_brokers": ["新加坡商瑞銀", "美商高盛", "法銀巴黎", "台灣摩根士丹利", "玉山-城中", "凱基-站前"],
        "top_seller": "元大 (-3,203張)",
        "margin_diff": -412, "margin_label": "融資退潮 (反彈測均線)",
        "short_ratio": 2.8, "score": 78,
        "nh": 556.0, "ah": 569.0, "status": "待開盤"
    },
    {
        "code": "8039", "name": "台虹", "has_futures": True,
        "close": 343.50, "high": 364.00, "low": 335.00, "volume": 58749,
        "main_buy_vol": 2678, "main_buy_cost": 348.05, "main_ratio": 4.56,
        "top_brokers": ["台灣摩根士丹利", "美林", "美商高盛", "新光", "國泰-敦南", "永豐金"],
        "top_seller": "凱基-台北 (-1,628張)",
        "margin_diff": -1669, "margin_label": "融資退潮 (散戶停損多殺多)",
        "short_ratio": 5.2, "score": 72,
        "nh": 354.0, "ah": 362.0, "status": "待開盤"
    },
    {
        "code": "2313", "name": "華通", "has_futures": True,
        "close": 241.00, "high": 260.00, "low": 240.50, "volume": 87191,
        "main_buy_vol": 4644, "main_buy_cost": 246.45, "main_ratio": 5.33,
        "top_brokers": ["美林", "美商高盛", "永豐金-忠孝", "台新", "台新-城東", "兆豐", "凱基-市府"],
        "top_seller": "凱基-台北 (-2,623張)",
        "margin_diff": 4315, "margin_label": "融資大增 (浮額沉重/易多殺多)",
        "short_ratio": 3.9, "score": 65,
        "nh": 249.5, "ah": 258.0, "status": "待開盤"
    },
    {
        "code": "2615", "name": "萬海", "has_futures": True,
        "close": 111.50, "high": 113.50, "low": 108.50, "volume": 21942,
        "main_buy_vol": 2971, "main_buy_cost": 110.81, "main_ratio": 13.54,
        "top_brokers": ["凱基-台北", "香港上海匯豐", "美林", "永豐金-匯立", "台灣摩根士丹利", "元大"],
        "top_seller": "美商高盛 (-863張)",
        "margin_diff": -277, "margin_label": "融資微幅退潮",
        "short_ratio": 5.7, "score": 60,
        "nh": 113.5, "ah": 115.5, "status": "待開盤"
    },
    {
        "code": "2344", "name": "華邦電", "has_futures": True,
        "close": 181.50, "high": 192.00, "low": 180.50, "volume": 153443,
        "main_buy_vol": 5581, "main_buy_cost": 185.34, "main_ratio": 3.64,
        "top_brokers": ["新加坡商瑞銀", "國泰-敦南", "台新-安南", "台新-新莊", "元大-桃興", "凱基-文心"],
        "top_seller": "元大 (-9,647張)",
        "margin_diff": 5844, "margin_label": "融資大增 (浮額過度渙散)",
        "short_ratio": 2.1, "score": 55,
        "nh": 188.0, "ah": 194.0, "status": "待開盤"
    },
    {
        "code": "3189", "name": "景碩", "has_futures": True,
        "close": 899.00, "high": 933.00, "low": 867.00, "volume": 21576,
        "main_buy_vol": 390, "main_buy_cost": 903.62, "main_ratio": 1.81,
        "top_brokers": ["國泰-敦南", "凱基-城中", "新光", "兆豐-嘉義", "群益金鼎-大安"],
        "top_seller": "美商高盛 (-931張)",
        "margin_diff": 634, "margin_label": "融資微增 (外資大倒貨)",
        "short_ratio": 1.8, "score": 45,
        "nh": 926.0, "ah": 945.0, "status": "待開盤"
    },
    {
        "code": "2426", "name": "鼎元", "has_futures": True,
        "close": 96.10, "high": 99.20, "low": 93.20, "volume": 61918,
        "main_buy_vol": 1227, "main_buy_cost": 96.48, "main_ratio": 1.98,
        "top_brokers": ["永豐金-松山", "永豐金-信義", "富邦-嘉義", "台新-宜蘭", "康和-台中", "凱基-板橋"],
        "top_seller": "美商高盛 (-2,417張)",
        "margin_diff": 3106, "margin_label": "融資大增 (外資主力狂倒)",
        "short_ratio": 1.5, "score": 40,
        "nh": 98.2, "ah": 100.5, "status": "待開盤"
    },
    {
        "code": "3260", "name": "威剛", "has_futures": True,
        "close": 412.00, "high": 418.50, "low": 407.00, "volume": 6969,
        "main_buy_vol": 542, "main_buy_cost": 411.96, "main_ratio": 7.78,
        "top_brokers": ["兆豐-南京", "日茂", "凱基-台北", "元大-復北", "國泰-敦南"],
        "top_seller": "台灣摩根士丹利 (-660張)",
        "margin_diff": 205, "margin_label": "融資微增",
        "short_ratio": 3.8, "score": 35,
        "nh": 418.0, "ah": 424.0, "status": "待開盤"
    }
]

# ==============================================================================
# 風控與評級判斷
# ==============================================================================
def get_risk_label(item):
    if item["score"] >= 90:
        return "🟢 適合短空 (首選狙擊)"
    elif item["score"] >= 80:
        return "🟢 適合短空 (低軋空風險)"
    elif item["score"] >= 65:
        return "🟡 觀察右側破線 (反彈測壓)"
    else:
        return "🔴 風險偏高 / 肉身空間小"

# ==============================================================================
# 頁面頂部資訊
# ==============================================================================
st.markdown("## 🎯 盤後全市場隔日沖 × 主力成本 × 鎖碼決策表 (勝率降序排列)")
st.caption("最新盤後結算日期：2026-08-28 ｜ 決策適用交易日：2026-08-31 (一)")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📅 最新結算日期", "2026-08-28")
with col2:
    st.metric("🎯 明日短空鎖碼標的", f"{len(DEFAULT_WATCHLIST)} 檔")
with col3:
    st.metric("🏛️ 追蹤主力分點", "30 家 (全台30大)")
with col4:
    st.metric("💧 流動性達標股 (均量≥1500張)", "10 檔 (100% 達標)")

st.markdown("---")

# ==============================================================================
# 總覽決策表格
# ==============================================================================
rows = []
for item in DEFAULT_WATCHLIST:
    rows.append({
        "短空勝率分": item["score"],
        "股票代號": item["code"],
        "股票名稱": item["name"],
        "個期": "期" if item["has_futures"] else "無",
        "現價": f"{item['close']:.2f}",
        "即時信號": f"⏳ {item['status']}",
        "出貨進度(%)": 0,
        "隔日沖分點清單": "、".join(item["top_brokers"][:4]) + (" 等" if len(item["top_brokers"]) > 4 else ""),
        "融資增減(張)": f"{item['margin_diff']:+d}",
        "融資力道評估": item["margin_label"],
        "主力合計佔比(%)": f"{item['main_ratio']:.2f}%",
        "主力合計買超": f"{item['main_buy_vol']:,}",
        "主力加權成本": f"{item['main_buy_cost']:.2f}",
        "賣超第一分點": item["top_seller"],
        "核心壓力(NH)": f"{item['nh']:.1f}",
        "極限壓力(AH)": f"{item['ah']:.1f}",
        "風控評級": get_risk_label(item)
    })

df_all = pd.DataFrame(rows)
df_all = df_all.sort_values(by="短空勝率分", ascending=False).reset_index(drop=True)

st.dataframe(
    df_all,
    use_container_width=True,
    height=420,
    hide_index=True
)

st.markdown("---")

# ==============================================================================
# 個股深度戰略微結構 (5分K 決策線圖模擬)
# ==============================================================================
st.markdown("### 🔍 個股短空決策線圖 [5分K (主力出手關鍵)]")

selected_stock_name = st.selectbox(
    "選擇欲深度檢視之標的：",
    options=[f"{x['code']} {x['name']} (勝率 {x['score']}分)" for x in DEFAULT_WATCHLIST]
)

stock_code = selected_stock_name.split(" ")[0]
current_stock = next(item for item in DEFAULT_WATCHLIST if item["code"] == stock_code)

c_left, c_right = st.columns([1, 3])

with c_left:
    st.markdown(f"#### 📌 {current_stock['name']} ({current_stock['code']}) 期")
    st.markdown(f"**短空勝率評分：** `{current_stock['score']} 分`")
    st.markdown(f"**收盤結算價：** `{current_stock['close']:.1f} 元`")
    st.markdown(f"**5日均量：** `{current_stock['volume'] // 5:,} 張`")
    st.markdown(f"**主力加權價：** `{current_stock['main_buy_cost']:.2f} 元`")
    st.markdown(f"**明日核心壓力 (NH)：** `{current_stock['nh']:.1f} 元`")
    st.markdown(f"**明日極限壓力 (AH)：** `{current_stock['ah']:.1f} 元`")
    st.markdown(f"**主力可倒貨總量：** `{current_stock['main_buy_vol']:,} 張 ({current_stock['main_ratio']:.2f}%)`")
    st.markdown(f"**融資增減：** `{current_stock['margin_diff']:+d} 張`")
    st.markdown(f"**風控評級：** {get_risk_label(current_stock)}")

with c_right:
    # 建立多層決策線圖 (Plotly)
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=("K線 & CDP 決策均線", "5分K 成交量", "主力分點買賣超 (張)", "大戶多空淨力道")
    )

    # 模擬 5 分 K 走勢數據 (以 8/28 實戰結構建立)
    times = pd.date_range("2026-08-28 09:00", "2026-08-28 13:30", freq="5min")
    np.random.seed(int(stock_code))
    
    base_price = current_stock["close"]
    prices = [base_price * (1 + np.sin(i / 5) * 0.015) for i in range(len(times))]
    
    # 1. 主圖 K 線與均線
    fig.add_trace(go.Scatter(x=times, y=prices, mode='lines+markers', name='價格走勢', line=dict(color='#00E5FF', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=times, y=[current_stock["nh"]]*len(times), mode='lines', name=f'核心壓力(NH) {current_stock["nh"]}', line=dict(color='#FF9800', dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=times, y=[current_stock["main_buy_cost"]]*len(times), mode='lines', name=f'主力均價 {current_stock["main_buy_cost"]:.2f}', line=dict(color='#00E676', dash='dot')), row=1, col=1)
    
    # 2. 成交量
    vols = np.random.randint(50, 800, size=len(times))
    fig.add_trace(go.Bar(x=times, y=vols, name='成交量', marker_color='#E0E0E0'), row=2, col=1)
    
    # 3. 分點進出
    net_power = np.random.randint(-200, 200, size=len(times))
    colors = ['#FF5252' if p > 0 else '#00E676' for p in net_power]
    fig.add_trace(go.Bar(x=times, y=net_power, name='分點力道', marker_color=colors), row=3, col=1)
    
    # 4. 累積淨力道
    cum_power = np.cumsum(net_power)
    fig.add_trace(go.Scatter(x=times, y=cum_power, name='累積淨差', line=dict(color='#FFD600', width=2)), row=4, col=1)

    fig.update_layout(
        height=650,
        margin=dict(l=10, r=10, t=25, b=10),
        template="plotly_dark",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# 下週一（8/31）操盤軍律
# ==============================================================================
st.markdown("---")
st.markdown("### 🛡️ 2026-08-31 (一) 實戰短空作戰守則")
col_a, col_b = st.columns(2)

with col_a:
    st.info(
        "**🔥 核心狙擊首選：華新科 (2492) — 勝率 95 分**\n\n"
        "* **主力結構**：富邦 (3,346張)、凱基城中 (2,756張)、凱基台北 (2,161張) 三大隔日沖重鎖逾 8,200 張。\n"
        "* **加權買進成本**：**312.38 元**（收盤 313.50 元）。\n"
        "* **作戰指引**：早盤衝高至 **318～321 元 (NH 壓力區)** 出現滯漲，5分K 實體摜破 **312.5 元** 為最佳右側進場點。"
    )

with col_b:
    st.warning(
        "**⚠️ 高檔戒備妖股：玉晶光 (3406) — 勝率 88 分**\n\n"
        "* **主力結構**：美林單一席位重買 1,442 張（均價 886.38 元），富邦買超 542 張（均價 894.67 元）。\n"
        "* **作戰守則**：妖股慣性強烈，**嚴禁早盤左側摸頂**，必須等待 5分K 實體長黑跌破 **900 元整數關卡** 後才可嘗試順勢短空。"
    )
