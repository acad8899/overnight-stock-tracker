# -*- coding: utf-8 -*-
"""
雙 AI 量化當沖 PK 賽事 ｜ Round 14 旗艦戰情室 (v14.0 完整版面)
==============================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# 1. 頁面配置
st.set_page_config(
    page_title="雙 AI 量化當沖 PK 賽事 ｜ Round 14 旗艦戰情室",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定義樣式
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card-gemini {
        background-color: #2b131a;
        border-left: 4px solid #ff4b4b;
        padding: 12px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .metric-card-gpt {
        background-color: #132238;
        border-left: 4px solid #1e90ff;
        padding: 12px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1c24;
        border-radius: 4px 4px 0 0;
        padding: 6px 14px;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2d3139 !important;
        color: #ffffff !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 2. 核心數據：已切換為 2026/09/21 盤後最新大數據
DATA_DATE = "9/21"

WATCHLIST_DATA = [
    {"代號": "2408", "名稱": "南亞科", "昨收": 516.0, "開盤": 525.0, "最高": 528.0, "最低": 513.0, "收盤": 516.0, "勝率": 99, "融資增": 34, "主力": "凱基-台北倒貨/自營認售冠軍"},
    {"代號": "2344", "名稱": "華邦電", "昨收": 174.0, "開盤": 180.0, "最高": 180.0, "最低": 174.0, "收盤": 174.0, "勝率": 97, "融資增": 1400, "主力": "外資踩踏砍1.9萬張/瑞銀大出"},
    {"代號": "2313", "名稱": "華通",   "昨收": 222.0, "開盤": 228.0, "最高": 228.5, "最低": 219.0, "收盤": 222.0, "勝率": 95, "融資增": 344, "主力": "美商高盛狂賣17.4%/破線下殺"},
    {"代號": "3406", "名稱": "玉晶光", "昨收": 952.0, "開盤": 973.0, "最高": 1005.0, "最低": 925.0, "收盤": 952.0, "勝率": 92, "融資增": -184, "主力": "認售第3名/失守千元心理關卡"},
    {"代號": "6173", "名稱": "信昌電", "昨收": 308.0, "開盤": 311.0, "最高": 318.5, "最低": 308.0, "收盤": 308.0, "勝率": 89, "融資增": -105, "主力": "衝高留長上影收最低/逆價差"},
    {"代號": "8039", "名稱": "台虹",   "昨收": 265.0, "開盤": 270.0, "最高": 272.0, "最低": 262.5, "收盤": 265.0, "勝率": 84, "融資增": 58, "主力": "高盛小買富邦大倒/整理格局"},
    {"代號": "3189", "名稱": "景碩",   "昨收": 827.0, "開盤": 849.0, "最高": 878.0, "最低": 824.0, "收盤": 827.0, "勝率": 81, "融資增": 611, "主力": "開高殺低/外資高盛賣超3.3%"},
    {"代號": "2492", "名稱": "華新科", "昨收": 308.5, "開盤": 311.5, "最高": 326.0, "最低": 307.5, "收盤": 308.5, "勝率": 76, "融資增": 323, "主力": "小摩賣超5.8%/高盛承接"},
    {"代號": "2327", "名稱": "國巨*",  "昨收": 557.0, "開盤": 556.0, "最高": 579.0, "最低": 556.0, "收盤": 557.0, "勝率": 65, "融資增": 1067, "主力": "認購大增但認售第5名對沖"},
    {"代號": "2455", "名稱": "全新",   "昨收": 572.0, "開盤": 571.0, "最高": 590.0, "最低": 545.0, "收盤": 572.0, "勝率": 58, "融資增": 138, "主力": "創高590/外資換手多頭續強"},
    {"代號": "3260", "名稱": "威剛",   "昨收": 389.0, "開盤": 385.5, "最高": 392.0, "最低": 383.0, "收盤": 389.0, "勝率": 42, "融資增": -323, "主力": "🛑富邦鎖單11.9%/賣認售第1禁空"},
    {"代號": "3037", "名稱": "欣興",   "昨收": 1020.0, "開盤": 999.0, "最高": 1055.0, "最低": 999.0, "收盤": 1020.0, "勝率": 25, "融資增": -25, "主力": "🛑大摩/兆豐/高盛推破千元禁空"}
]

# 3. 左側側邊欄：依裁判長指示結算 R13 後的全新數據
with st.sidebar:
    st.markdown("### ⚡ 短空雷達量化控制台")
    st.caption(f"**決戰輪次**：Round 14 (2026/09/22 明日早盤)")
    st.caption(f"**母池籌碼基準**：2026/09/21 盤後最新大數據")
    st.markdown("---")
    
    st.markdown("#### 🏆 賽事累計淨值儀表板")
    
    # Gemini 淨值卡
    st.markdown("""
    <div class="metric-card-gemini">
        <span style="color:#ff4b4b; font-size:12px; font-weight:bold;">🟥 Gemini 總淨值 (9勝1負2平)</span>
        <h3 style="color:#ffffff; margin:4px 0;">NT$ 1,697,595</h3>
        <span style="color:#8b949e; font-size:11px;">R13 台虹平價保本出場 (損益 $0)</span>
    </div>
    """, unsafe_allow_html=True)
    
    # GPT 淨值卡 (計入 R13 獲利 +36,000)
    st.markdown("""
    <div class="metric-card-gpt">
        <span style="color:#1e90ff; font-size:12px; font-weight:bold;">🟦 ChatGPT 總淨值 (2勝9負2平)</span>
        <h3 style="color:#ffffff; margin:4px 0;">NT$ 1,321,681</h3>
        <span style="color:#8b949e; font-size:11px;">R13 玉晶光+威剛達標 (+NT$ 36,000)</span>
    </div>
    """, unsafe_allow_html=True)
    
    # 領先差距與單檔風控
    diff = 1697595 - 1321681
    st.markdown(f"""
    <div style="background-color:#161b22; padding:10px; border-radius:4px; border:1px solid #30363d; margin-bottom:10px;">
        <span style="color:#00ffcc; font-size:12px; font-weight:bold;">🚩 雙方差距：Gemini 領先 NT$ {diff:,}</span><br>
        <span style="color:#c9d1d9; font-size:12px;">單檔上限 (20%)：</span><br>
        <span style="color:#8b949e; font-size:11px;">• Gemini: NT$ 339,519<br>• GPT: NT$ 264,336</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("⚖️ **裁判長拍定新規**：\n單筆最大停損 ≤ NT$ 20,000（2萬金盾）；T1 觸及即啟動方案 A 全數保底！")

# 4. 主工作區標題
st.title("🎯 雙 AI 量化當沖 PK 賽事 ｜ Round 14 旗艦戰情室")
st.caption("數據基準：2026/09/21 臺灣證券交易所/櫃買中心/主力分點/自營商權證三維大數據")

# 5. 完整 7 大標籤頁面（維持您截圖的完整功能排版）
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🖥️ 專業操盤工作台 (K線與分點)",
    "⚔️ R14 官方決戰封單名冊",
    "🧮 官方撮合與方案A結算模擬器",
    "📋 12檔母池籌碼雷達全景表",
    "📈 R1-R13 淨值儀表板",
    "📊 融資增減(動態表頭已修復)",
    "🏛️ 主力分點"
])

# -----------------------------------------------------------------------------
# TAB 1: 專業操盤工作台 (與您截圖一模一樣的排版，更新至 9/21)
# -----------------------------------------------------------------------------
with tab1:
    col_left, col_right = st.columns([1, 2.5])
    
    with col_left:
        st.markdown("#### 📋 短空鎖碼清單")
        st.caption("依勝率客觀對齊，可選擇切換標的：")
        
        # 標的選單列表
        selected_code = st.radio(
            "選擇標的：",
            [f"[{x['勝率']}分] {x['代號']} {x['名稱']} ({x['昨收']})" for x in WATCHLIST_DATA],
            index=0,
            label_visibility="collapsed"
        )
        current_code = selected_code.split("] ")[1].split()[0]
        cur_stock = next(s for s in WATCHLIST_DATA if s["代號"] == current_code)
        
        st.markdown(f"""
        <div style="background-color:#1c1917; border-left:4px solid #f97316; padding:10px; border-radius:4px; margin-top:15px;">
            <span style="color:#f97316; font-weight:bold;">★ {cur_stock['名稱']} ({cur_stock['代號']})</span>
            <span style="background-color:#991b1b; color:#fff; font-size:11px; padding:1px 5px; border-radius:3px; float:right;">勝率 {cur_stock['勝率']}分</span><br>
            <span style="color:#a8a29e; font-size:12px;">收盤價：{cur_stock['昨收']} 元</span><br>
            <span style="color:#a8a29e; font-size:12px;">籌碼特徵：{cur_stock['主力']}</span>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        c_p1, c_p2 = st.columns([2, 1])
        with c_p1:
            period = st.selectbox("週期切換：", ["5分K (主力關鍵)", "1分K", "15分K", "日K"], index=0)
        with c_p2:
            bars = st.number_input("K棒根數：", min_value=30, max_value=200, value=60)
            
        st.markdown(f"##### **{cur_stock['代號']} {cur_stock['名稱']} ｜ 短空決策線圖 [{period}]**")
        
        # 模擬 5 分 K 線圖（包含均線與成交量）
        np.random.seed(int(cur_stock["代號"]))
        base_p = cur_stock["昨收"]
        closes = [base_p + np.random.normal(0, base_p * 0.004) for _ in range(bars)]
        highs = [c + abs(np.random.normal(0, base_p * 0.002)) for c in closes]
        lows = [c - abs(np.random.normal(0, base_p * 0.002)) for c in closes]
        opens = [(h + l) / 2 for h, l in zip(highs, lows)]
        volumes = [int(np.random.uniform(50, 400)) for _ in range(bars)]
        
        fig = go.Figure(data=[go.Candlestick(
            x=list(range(bars)), open=opens, high=highs, low=lows, close=closes,
            increasing_line_color='#ef4444', decreasing_line_color='#22c55e'
        )])
        fig.add_hline(y=base_p * 1.015, line_dash="dash", line_color="#a855f7", annotation_text=f"主力防線: {base_p*1.015:.1f}")
        fig.update_layout(height=420, template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 2: R14 官方決戰封單名冊 (雙方陣營名單)
# -----------------------------------------------------------------------------
with tab2:
    st.markdown("### ⚔️ Round 14 雙 AI 官方封單名冊")
    st.caption("本輪裁判長裁定公約：單筆停損上限 NT$ 20,000，盤中達 T1 即刻方案 A 全數平倉保底。")
    
    col_g, col_p = st.columns(2)
    with col_g:
        st.markdown("#### 🟥 Gemini 戰情室｜極致量化版")
        st.table(pd.DataFrame([
            {"順位": "1", "標的": "2408 南亞科", "口數": "1", "進場門檻": "< 513.0", "停損": "523.0", "T1": "503.0", "T2": "495.0"},
            {"順位": "2", "標的": "2344 華邦電", "口數": "2", "進場門檻": "< 173.0", "停損": "178.0", "T1": "168.0", "T2": "162.0"},
            {"順位": "3", "標的": "2313 華通",   "口數": "2", "進場門檻": "< 219.0", "停損": "224.0", "T1": "213.0", "T2": "207.0"},
            {"順位": "4", "標的": "3406 玉晶光", "口數": "1", "進場門檻": "< 945.0", "停損": "955.0", "T1": "935.0", "T2": "925.0"},
            {"順位": "5", "標的": "6173 信昌電", "口數": "2", "進場門檻": "< 306.0", "停損": "311.0", "T1": "297.0", "T2": "290.0"}
        ]))
        
    with col_p:
        st.markdown("#### 🟦 ChatGPT 戰情室｜主力籌碼版")
        st.table(pd.DataFrame([
            {"順位": "1", "標的": "2344 華邦電", "口數": "2", "進場門檻": "< 172.0", "停損": "177.0", "T1": "166.0", "T2": "160.0"},
            {"順位": "2", "標的": "8039 台虹",   "口數": "2", "進場門檻": "< 262.0", "停損": "267.0", "T1": "256.0", "T2": "250.0"},
            {"順位": "3", "標的": "3189 景碩",   "口數": "2", "進場門檻": "< 815.0", "停損": "820.0", "T1": "805.0", "T2": "795.0"},
            {"順位": "4", "標的": "3406 玉晶光", "口數": "1", "進場門檻": "< 945.0", "停損": "955.0", "T1": "935.0", "T2": "925.0"},
            {"順位": "5", "標的": "3260 威剛",   "口數": "2", "進場門檻": "< 383.0", "停損": "388.0", "T1": "375.0", "T2": "368.0"}
        ]))

# -----------------------------------------------------------------------------
# TAB 3: 官方撮合與方案A結算模擬器
# -----------------------------------------------------------------------------
with tab3:
    st.markdown("### 🧮 方案 A 保底停利撮合模擬器")
    st.write("設定撮合點位與出場條件，自動精算實質損益（扣除手續費與稅）：")
    c_m1, c_m2, c_m3 = st.columns(3)
    entry_p = c_m1.number_input("進場撮合價 (不利滑價)：", value=265.5)
    exit_p = c_m2.number_input("出場平倉價 (T1/市價/停損)：", value=258.0)
    shares = c_m3.selectbox("合約股數 (口數)：", [2000, 4000, 6000], index=1)
    
    diff_pt = entry_p - exit_p
    gross_pnl = diff_pt * shares
    fee_tax = 200  # 預估摩擦成本
    net_pnl = gross_pnl - fee_tax
    st.metric("試算淨損益 (NTD)", f"{net_pnl:,.0f} 元", f"{diff_pt:+.2f} 點")

# -----------------------------------------------------------------------------
# TAB 4: 12檔母池籌碼雷達全景表
# -----------------------------------------------------------------------------
with tab4:
    st.markdown(f"### 📋 12 檔母池籌碼大數據全覽 ({DATA_DATE} 盤後最新)")
    df_all = pd.DataFrame(WATCHLIST_DATA)
    st.dataframe(df_all[["代號", "名稱", "昨收", "勝率", "融資增", "主力"]], use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: R1-R13 歷輪淨值儀表板 (含 R13 結算)
# -----------------------------------------------------------------------------
with tab5:
    st.markdown("### 📈 歷輪 13 戰淨值走勢演變")
    rounds_df = pd.DataFrame(ROUNDS_HISTORY)
    st.dataframe(rounds_df, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 6: 融資增減 (動態表頭已修復)
# -----------------------------------------------------------------------------
with tab6:
    st.markdown(f"### 📊 12 檔母池 {DATA_DATE} 最新融資增減熱力排行榜 (按增減張數降序)")
    st.success("✅ **動態標題已修復**：表頭日期現已完全綁定後端變數，自動跟隨每日更新！")
    df_margin = pd.DataFrame(WATCHLIST_DATA).sort_values(by="融資增", ascending=False)
    st.table(df_margin[["代號", "名稱", "昨收", "融資增"]].rename(columns={"融資增": f"{DATA_DATE} 融資增減(張)"}))

# -----------------------------------------------------------------------------
# TAB 7: 主力分點
# -----------------------------------------------------------------------------
with tab7:
    st.markdown(f"### 🏛️ {DATA_DATE} 主力分點關鍵進出追蹤")
    st.write("• **2344 華邦電**：新加坡瑞銀大倒 -5,831張，外資合砍 1.9 萬張。")
    st.write("• **2408 南亞科**：凱基-台北大賣 -2,229張，認售權證買超高達 +914萬奪冠。")
    st.write("• **2313 華通**：美商高盛單點瘋砍 -3,953張（佔比 17.4%）。")
