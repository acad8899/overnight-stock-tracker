import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ==============================================================================
# 1. 系統架構與頁面基本配置
# ==============================================================================
st.set_page_config(
    page_title="短空雷達量化監控系統 - Round 11 決戰版",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自訂 CSS 保證全螢幕寬表格不跑版、文字緊湊易讀
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        border-radius: 8px;
        padding: 12px;
        border-left: 4px solid #FF4B4B;
        margin-bottom: 10px;
    }
    .metric-gpt {
        border-left: 4px solid #1E88E5 !important;
    }
    .stDataFrame {
        border-radius: 6px;
    }
    .status-badge {
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. 官方公約常數與雙方帳戶狀態 (2026/09/16 結算後凍結生效)
# ==============================================================================
R11_DATE = "2026/09/17"
LAST_DATA_DATE = "2026/09/16"

CAPITAL_GEMINI = 1620595
CAPITAL_CHATGPT = 1289681
LIMIT_GEMINI = int(CAPITAL_GEMINI * 0.20)    # NT$ 324,119
LIMIT_CHATGPT = int(CAPITAL_CHATGPT * 0.20)  # NT$ 257,936
NET_DIFF = CAPITAL_GEMINI - CAPITAL_CHATGPT  # NT$ 330,914

# ==============================================================================
# 3. 官方 12 檔母池大數據庫 (2026/09/16 盤後完整三維籌碼數據)
# ==============================================================================
WATCHLIST_DB = {
    "2455": {
        "name": "全新", "market": "TW", "close": 515.0, "change": -5.0, "volume": 19718,
        "margin_diff": 627,
        "major_buy": [("台灣摩根士丹利", 301, 519.53), ("元大崇德", 220, 518.07), ("國票安和", 187, 522.05)],
        "major_sell": [("美林", -584, 515.97), ("富邦", -443, 522.60), ("新加坡商瑞銀", -406, 519.49)],
        "warrant_call": 0, "warrant_put": 0, "nh": 534.0, "ah": 545.0,
        "status": "🚨 空方首選", "diagnosis": "逆勢收黑跌破均線，外資聯手砍殺1,700張，散戶融資暴增+627張接刀深套。"
    },
    "8039": {
        "name": "台虹", "market": "TW", "close": 275.5, "change": 5.5, "volume": 12424,
        "margin_diff": 390,
        "major_buy": [("台灣摩根士丹利", 488, 274.66), ("元大信義安和", 250, 277.26), ("凱基台北", 221, 273.61)],
        "major_sell": [("摩根大通", -1731, 274.42), ("永豐金", -319, 275.03), ("美商高盛", -259, 274.46)],
        "warrant_call": 0, "warrant_put": 0, "nh": 278.0, "ah": 285.0,
        "status": "🚨 空方首選", "diagnosis": "摩根大通單點暴砍1,731張(佔比13.93%)，散戶融資連四日逆勢接刀，高檔出貨。"
    },
    "6173": {
        "name": "信昌電", "market": "OTC", "close": 315.0, "change": 20.5, "volume": 28232,
        "margin_diff": 551,
        "major_buy": [("統一", 890, 311.10), ("富邦台北", 871, 313.17), ("凱基台北", 470, 306.80)],
        "major_sell": [("國泰敦南", -266, 307.54), ("大昌桃園", -189, 310.28), ("群益金鼎大安", -153, 308.00)],
        "warrant_call": 0, "warrant_put": 0, "nh": 323.0, "ah": 323.0,
        "status": "🚨 隔日沖狙擊", "diagnosis": "統一、富邦、康和鎖單逾2,600張，融資連兩天暴增逾900張，嚴防早盤出貨踩踏。"
    },
    "3189": {
        "name": "景碩", "market": "TW", "close": 820.0, "change": 25.0, "volume": 10957,
        "margin_diff": 720,
        "major_buy": [("富邦新店", 331, 823.52), ("統一", 318, 820.14), ("美商高盛", 283, 814.57)],
        "major_sell": [("永豐金匯立", -283, 813.46), ("台灣摩根士丹利", -254, 812.07), ("元大", -233, 813.31)],
        "warrant_call": -460, "warrant_put": 0, "nh": 832.0, "ah": 835.0,
        "status": "🚨 浮額超載", "diagnosis": "融資狂增720張居全市場榜首，衝832留上影線，大摩小摩調節，認購大退。"
    },
    "2327": {
        "name": "國巨*", "market": "TW", "close": 536.0, "change": -1.0, "volume": 27854,
        "margin_diff": 55,
        "major_buy": [("永豐金", 292, 533.40), ("國泰敦南", 283, 533.69), ("凱基台北", 241, 533.64)],
        "major_sell": [("美林", -2640, 532.80), ("新加坡商瑞銀", -865, 534.33), ("摩根大通", -765, 534.05)],
        "warrant_call": 0, "warrant_put": -164, "nh": 543.0, "ah": 558.0,
        "status": "偏空破綻", "diagnosis": "逆勢收黑跌破均線，美林單點狂倒2,640張(佔比9.5%)，融資逆勢套牢。"
    },
    "3037": {
        "name": "欣興", "market": "TW", "close": 961.0, "change": 10.0, "volume": 11860,
        "margin_diff": 56,
        "major_buy": [("富邦", 882, 963.55), ("新加坡商瑞銀", 491, 954.86), ("元大", 467, 957.54)],
        "major_sell": [("美商高盛", -1560, 952.32), ("凱基", -730, 953.29), ("摩根大通", -529, 956.71)],
        "warrant_call": 0, "warrant_put": 0, "nh": 971.0, "ah": 986.0,
        "status": "偏空觀察", "diagnosis": "美商高盛單點重砍1,560張(佔比13.15%)，外資大提款近3,000張，反彈承壓。"
    },
    "2492": {
        "name": "華新科", "market": "TW", "close": 307.5, "change": 7.5, "volume": 15103,
        "margin_diff": -391,
        "major_buy": [("凱基台北", 931, 302.56), ("台灣摩根士丹利", 641, 301.40), ("美林", 240, 302.01)],
        "major_sell": [("新加坡商瑞銀", -534, 302.82), ("元大", -513, 301.86), ("富邦", -394, 302.98)],
        "warrant_call": 0, "warrant_put": 0, "nh": 307.5, "ah": 315.5,
        "status": "中立震盪", "diagnosis": "凱基台北大買931張拉高，融資連退-391張，早盤防隔日沖賣壓。"
    },
    "2313": {
        "name": "華通", "market": "TW", "close": 225.0, "change": 6.5, "volume": 18970,
        "margin_diff": -22,
        "major_buy": [("元大", 636, 221.89), ("永豐金", 502, 221.94), ("國票敦北", 359, 223.01)],
        "major_sell": [("摩根大通", -797, 221.13), ("台灣摩根士丹利", -703, 219.72), ("美林", -426, 220.49)],
        "warrant_call": 0, "warrant_put": 0, "nh": 225.0, "ah": 228.0,
        "status": "中立觀察", "diagnosis": "外資小摩大摩調節近2,000張，本土大戶低接護盤，多空膠著。"
    },
    "3260": {
        "name": "威剛", "market": "TW", "close": 399.5, "change": 11.0, "volume": 3365,
        "margin_diff": -194,
        "major_buy": [("美好富順", 294, 394.44), ("永豐金", 229, 397.49), ("合庫", 187, 394.19)],
        "major_sell": [("台灣摩根士丹利", -247, 393.75), ("玉山", -106, 393.39), ("元大大同", -105, 389.74)],
        "warrant_call": 1580, "warrant_put": 0, "nh": 399.5, "ah": 402.0,
        "status": "⚠️ 禁空觀察", "diagnosis": "本土買盤強推收最高399.5，認購權證買超高達1,580萬，嚴禁摸空。"
    },
    "2344": {
        "name": "華邦電", "market": "TW", "close": 169.0, "change": 9.5, "volume": 83218,
        "margin_diff": -2056,
        "major_buy": [("美商高盛", 4925, 166.79), ("美林", 3953, 166.70), ("凱基台北", 3261, 166.97)],
        "major_sell": [("摩根大通", -2543, 167.86), ("國泰敦南", -916, 166.68), ("富邦", -692, 167.59)],
        "warrant_call": 0, "warrant_put": -207, "nh": 169.5, "ah": 172.0,
        "status": "🛑 官方共識禁空", "diagnosis": "高盛美林暴買1.2萬張軋空，融資狂減2,056張籌碼徹底洗淨，嚴禁逆勢追空。"
    },
    "2408": {
        "name": "南亞科", "market": "TW", "close": 492.5, "change": 27.0, "volume": 36437,
        "margin_diff": -741,
        "major_buy": [("元大", 1924, 484.67), ("美林", 1094, 483.74), ("台灣摩根士丹利", 1002, 483.73)],
        "major_sell": [("永豐金", -897, 485.66), ("國泰敦南", -371, 484.98), ("台新", -332, 485.16)],
        "warrant_call": 0, "warrant_put": 0, "nh": 495.0, "ah": 500.0,
        "status": "🛑 官方共識禁空", "diagnosis": "元大美林大摩反手狂補，大漲5.8%，融資大退741張，結構轉多不可放空。"
    },
    "3406": {
        "name": "玉晶光", "market": "TW", "close": 1005.0, "change": 90.0, "volume": 4089,
        "margin_diff": 153,
        "major_buy": [("富邦", 556, 1003.82), ("元大", 349, 991.48), ("統一城中", 140, 1005.00)],
        "major_sell": [("永豐金", -107, 984.80), ("凱基", -58, 986.15), ("中國信託", -57, 1005.00)],
        "warrant_call": 0, "warrant_put": 71, "nh": 1005.0, "ah": 1005.0,
        "status": "🛑 官方共識禁空", "diagnosis": "強勢漲停鎖死在1,005元，多頭極度強勢，官方維持絕對禁空公約。"
    }
}

# ==============================================================================
# 4. 雙方 Round 11 正式封單陣列 (防截斷規格)
# ==============================================================================
ORDERS_GEMINI = [
    {"rank": "🥇 首選 1", "ticker": "2455", "name": "全新(期)", "tool": "期貨", "size": "1口", "margin": 139050, "trigger": 512.0, "stop": 526.0, "t1": 498.0, "t2": 488.0, "reason": "逆勢收黑，外資砍1,700張，融資暴增+627張深套。"},
    {"rank": "🥈 首選 2", "ticker": "8039", "name": "台虹(期)", "tool": "期貨", "size": "2口", "margin": 110200, "trigger": 273.0, "stop": 280.0, "t1": 264.0, "t2": 258.0, "reason": "小摩單點倒13.9%，散戶融資連四日逆勢接刀。"},
    {"rank": "🥉 首選 3", "ticker": "6173", "name": "信昌電(期)", "tool": "期貨", "size": "2口", "margin": 170100, "trigger": 312.0, "stop": 322.0, "t1": 302.0, "t2": 295.0, "reason": "隔日沖重鎖2,600張，融資兩天增逾900張。"},
    {"rank": "4", "ticker": "3189", "name": "景碩(期)", "tool": "期貨", "size": "1口", "margin": 221400, "trigger": 814.0, "stop": 833.0, "t1": 792.0, "t2": 778.0, "reason": "融資暴增+720張居冠，大摩調節，認購大停損。"},
    {"rank": "5", "ticker": "2327", "name": "國巨*(期)", "tool": "期貨", "size": "1口", "margin": 144720, "trigger": 533.0, "stop": 544.0, "t1": 519.0, "t2": 508.0, "reason": "逆勢收黑，美林重砍2,640張，融資逆勢套牢。"}
]

ORDERS_CHATGPT = [
    {"rank": "🥇 1", "ticker": "2455", "name": "全新(期)", "tool": "期貨", "size": "1口", "margin": 139050, "trigger": 510.0, "stop": 524.0, "t1": 500.0, "t2": 492.0, "reason": "法人重賣＋融資大增，破510進場。"},
    {"rank": "🥈 2", "ticker": "8039", "name": "台虹(期)", "tool": "期貨", "size": "2口", "margin": 110200, "trigger": 271.0, "stop": 279.0, "t1": 263.0, "t2": 257.0, "reason": "法人連賣＋融資增加，破271進場。"},
    {"rank": "🥉 3", "ticker": "3189", "name": "景碩(期)", "tool": "期貨", "size": "1口", "margin": 221400, "trigger": 810.0, "stop": 832.0, "t1": 795.0, "t2": 780.0, "reason": "融資暴增＋高檔震盪，破810進場。"},
    {"rank": "4", "ticker": "2327", "name": "國巨(期)", "tool": "期貨", "size": "1口", "margin": 144720, "trigger": 526.0, "stop": 544.0, "t1": 518.0, "t2": 510.0, "reason": "外資巨量撤退，摜破昨低526才進場。"},
    {"rank": "5", "ticker": "3037", "name": "欣興(期)", "tool": "期貨", "size": "1口", "margin": 259470, "trigger": 940.0, "stop": 975.0, "t1": 925.0, "t2": 910.0, "reason": "高盛重砍，法人連續轉弱，破940進場。"}
]

# ==============================================================================
# 5. 核心演算法：不利滑價撮合、方案 A 階梯鎖利與券商分析模組
# ==============================================================================
def calculate_execution(trigger_price, trigger_k_close, next_k_open, current_low, stop_loss, t1_price, t2_price):
    """
    公約撮合演算法：
    1. 實體跌破判定：trigger_k_close < trigger_price
    2. 不利滑價撮合成交價：min(trigger_k_close, next_k_open) (對空方較差者)
    3. 方案 A 觸發判定：current_low <= t1_price
    """
    if trigger_k_close >= trigger_price:
        return {"status": "未觸發", "entry_price": None, "exit_price": None, "points": 0, "result": "未跌破實體門檻，空手防守"}
    
    # 計算不利滑價撮合價
    entry_price = min(trigger_k_close, next_k_open)
    
    # 方案 A 保底檢驗
    if current_low <= t1_price:
        return {
            "status": "已平倉 (方案 A 命中)",
            "entry_price": entry_price,
            "exit_price": t1_price,
            "points": entry_price - t1_price,
            "result": f"盤中低點 {current_low} 穿破 T1 ({t1_price})，依方案 A 全數保底鎖利！"
        }
    else:
        return {
            "status": "在倉持股中",
            "entry_price": entry_price,
            "exit_price": None,
            "points": 0,
            "result": "部位持倉中，等待跌破 T1 或 13:25 尾盤強平結算。"
        }

def render_broker_table(ticker):
    """繪製前三大買賣超分點詳細數據"""
    info = WATCHLIST_DB[ticker]
    cb, cs = st.columns(2)
    with cb:
        st.markdown("**🟢 主力買超前三大分點**")
        for b_name, b_vol, b_price in info["major_buy"]:
            st.markdown(f"- **{b_name}**：`+{b_vol:,} 張` (均價: `{b_price:.2f}`)")
    with cs:
        st.markdown("**🔴 主力賣超前三大分點**")
        for s_name, s_vol, s_price in info["major_sell"]:
            st.markdown(f"- **{s_name}**：`{s_vol:,} 張` (均價: `{s_price:.2f}`)")

# ==============================================================================
# 6. 側邊欄導航與戰績即時看板
# ==============================================================================
st.sidebar.title("⚡ 短空雷達量化控制台")
st.sidebar.markdown(f"**決戰輪次**：`Round 11` ({R11_DATE})")
st.sidebar.markdown(f"**母池籌碼基準**：`{LAST_DATA_DATE}` 盤後大數據")

# 淨值儀表板
st.sidebar.markdown("---")
st.sidebar.subheader("🏆 賽事实時累積淨值")
st.sidebar.markdown(f"""
<div class="metric-card">
    <div style="font-size: 13px; color: #BBB;">🟥 Gemini 總淨值 (7勝1負2平)</div>
    <div style="font-size: 22px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_GEMINI:,}</div>
    <div style="font-size: 12px; color: #AAA;">R10 空手避開強軋 (0損益)</div>
</div>
<div class="metric-card metric-gpt">
    <div style="font-size: 13px; color: #BBB;">🟦 ChatGPT 總淨值 (1勝7負2平)</div>
    <div style="font-size: 22px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CHATGPT:,}</div>
    <div style="font-size: 12px; color: #AAA;">R10 空手避開強軋 (0損益)</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.info(f"🚩 **淨值差距**：Gemini 領先 **NT$ {NET_DIFF:,}**")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📜 R11 官方執法公約")
st.sidebar.caption("1. **進場唯一標準**：5分K實體黑棒收盤價 < 觸發價。\n2. **撮合防滑價**：不利撮合價 = min(觸發K收盤, 次K開盤)。\n3. **階梯結算**：方案 A 優先，盤中低點穿破 T1 即刻全數保底鎖利平倉。\n4. **強制清算**：未破停損亦未達 T1 者，一律於 13:25～13:30 強制平倉結算。")

# ==============================================================================
# 7. 主頁面：四大功能分頁
# ==============================================================================
st.title("🎯 雙 AI 當沖量化 PK 賽事｜Round 11 決戰戰情室")
st.caption(f"即時連線監控中心｜數據來源：{LAST_DATA_DATE} 臺灣證券交易所/櫃買中心/30+券商分點")

tab_radar, tab_orders, tab_matcher, tab_live = st.tabs([
    "📊 12檔母池籌碼雷達", 
    "⚔️ R11 雙方正式封單", 
    "🧮 不利撮合與方案A結算器", 
    "📈 盤中 5分K 實時監控"
])

# ------------------------------------------------------------------------------
# TAB 1: 12檔母池籌碼雷達 (含主力分析摘要)
# ------------------------------------------------------------------------------
with tab_radar:
    st.subheader("📋 12 檔母池大數據總覽 (三維交叉驗證)")
    
    radar_rows = []
    for t_code, t_val in WATCHLIST_DB.items():
        radar_rows.append({
            "代號": t_code,
            "標的名稱": t_val["name"],
            "收盤價": f"{t_val['close']:.2f}",
            "漲跌": f"{t_val['change']:+.2f}",
            "成交量": f"{t_val['volume']:,}",
            "融資增減(張)": f"{t_val['margin_diff']:+d}",
            "近高壓力(NH)": f"{t_val['nh']:.2f}",
            "全高壓力(AH)": f"{t_val['ah']:.2f}",
            "認購增減(萬)": f"{t_val['warrant_call']:+d}",
            "偏空診斷狀態": t_val["status"]
        })
    st.dataframe(pd.DataFrame(radar_rows), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🔍 標的主力分點進出與避險破綻深度檢驗")
    target_select = st.selectbox("選擇要檢視籌碼分點的標的：", list(WATCHLIST_DB.keys()), format_func=lambda x: f"{x} {WATCHLIST_DB[x]['name']} - {WATCHLIST_DB[x]['status']}")
    
    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        st.markdown(f"### **{target_select} {WATCHLIST_DB[target_select]['name']}**")
        st.write(f"- **最新收盤**：`{WATCHLIST_DB[target_select]['close']}` ({WATCHLIST_DB[target_select]['change']:+.2f})")
        st.write(f"- **融資增減**：`{WATCHLIST_DB[target_select]['margin_diff']:+d} 張`")
        st.write(f"- **權證認購增減**：`{WATCHLIST_DB[target_select]['warrant_call']:+d} 萬元`")
        st.write(f"- **狀態評估**：`{WATCHLIST_DB[target_select]['status']}`")
    with col_d2:
        st.markdown(f"**核心破綻摘要**：{WATCHLIST_DB[target_select]['diagnosis']}")
        render_broker_table(target_select)

# ------------------------------------------------------------------------------
# TAB 2: R11 雙方正式封單 (防截斷規格)
# ------------------------------------------------------------------------------
with tab_orders:
    st.subheader("⚔️ Round 11 官方決戰名冊陣列 (已完成資料庫凍結)")
    col_g, col_c = st.columns(2)
    
    with col_g:
        st.markdown("#### 🟥 Gemini 戰情室封單")
        st.caption(f"淨值：NT$ {CAPITAL_GEMINI:,}｜單檔上限：NT$ {LIMIT_GEMINI:,}")
        
        df_gem_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']}", "停損": x["stop"], "停利 T1": x["t1"], "停利 T2": x["t2"], "規格": f"{x['size']} ({x['margin']//1000}K)"}
            for x in ORDERS_GEMINI
        ])
        st.dataframe(df_gem_ui, use_container_width=True, hide_index=True)
        
        with st.expander("查看 Gemini 籌碼依據與量化細節", expanded=True):
            for x in ORDERS_GEMINI:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']}` ｜ 停損 `{x['stop']}` ｜ **T1 `{x['t1']}`**")
                st.caption(f"└ 籌碼依據：{x['reason']}")
                
    with col_c:
        st.markdown("#### 🟦 ChatGPT 戰情室封單")
        st.caption(f"淨值：NT$ {CAPITAL_CHATGPT:,}｜單檔上限：NT$ {LIMIT_CHATGPT:,}")
        
        df_gpt_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']}", "停損": x["stop"], "停利 T1": x["t1"], "停利 T2": x["t2"], "規格": f"{x['size']} ({x['margin']//1000}K)"}
            for x in ORDERS_CHATGPT
        ])
        st.dataframe(df_gpt_ui, use_container_width=True, hide_index=True)
        
        with st.expander("查看 ChatGPT 型態邏輯與量化細節", expanded=True):
            for x in ORDERS_CHATGPT:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']}` ｜ 停損 `{x['stop']}` ｜ **T1 `{x['t1']}`**")
                st.caption(f"└ 作戰型態：{x['reason']}")

    st.markdown("---")
    st.subheader("🛑 Round 11 官方共識禁空名單（NO SHORT）")
    cn1, cn2, cn3 = st.columns(3)
    cn1.error("🚫 **3406 玉晶光**：強勢漲停鎖死 1,005 元，多頭極度強烈，維持絕對禁空。")
    cn2.error("🚫 **2344 華邦電**：高盛美林暴買 1.2 萬張軋空，融資大退 -2,056 張洗淨，嚴禁追空。")
    cn3.error("🚫 **2408 南亞科**：元大美林大摩反手大補，單日飆 5.8%，結構翻多不可摸空。")

# ------------------------------------------------------------------------------
# TAB 3: 撮合與方案 A 階梯結算器 (實務裁判工具)
# ------------------------------------------------------------------------------
with tab_matcher:
    st.subheader("🧮 裁判室專用：5分K實體跌破撮合與方案 A 結算模擬器")
    st.caption("依據官方公約：取不利撮合價進場，盤中穿破 T1 即刻鎖利，未達條件者於 13:25 強制結算。")
    
    sim_col1, sim_col2 = st.columns(2)
    
    with sim_col1:
        st.markdown("**步驟 1：選擇審查部位與輸入盤面 5 分 K 數據**")
        side_selected = st.radio("選擇選手：", ["🟥 Gemini", "🟦 ChatGPT"], horizontal=True)
        active_list = ORDERS_GEMINI if "Gemini" in side_selected else ORDERS_CHATGPT
        
        selected_order = st.selectbox(
            "選擇審查訂單：", 
            active_list, 
            format_func=lambda x: f"{x['rank']} {x['name']} (門檻 < {x['trigger']}, T1: {x['t1']})"
        )
        
        input_trigger_k = st.number_input("觸發 5 分 K 實體收盤價：", value=float(selected_order["trigger"]) - 0.5, step=0.5)
        input_next_k = st.number_input("次一 5 分 K 開盤價：", value=float(selected_order["trigger"]) - 1.0, step=0.5)
        input_low = st.number_input("盤中最低價 (5 分 K 最低點)：", value=float(selected_order["t1"]) - 1.0, step=0.5)
        
    with sim_col2:
        st.markdown("**步驟 2：官方裁判室自動撮合結算結果**")
        sim_result = calculate_execution(
            trigger_price=selected_order["trigger"],
            trigger_k_close=input_trigger_k,
            next_k_open=input_next_k,
            current_low=input_low,
            stop_loss=selected_order["stop"],
            t1_price=selected_order["t1"],
            t2_price=selected_order["t2"]
        )
        
        st.info(f"**部位狀態**：{sim_result['status']}")
        if sim_result["entry_price"] is not None:
            st.write(f"- **不利滑價撮合進場價**：`{sim_result['entry_price']:.2f}` (取 {input_trigger_k} 與 {input_next_k} 較劣者)")
            if sim_result["exit_price"] is not None:
                st.write(f"- **平倉價格 (T1)**：`{sim_result['exit_price']:.2f}`")
                st.write(f"- **單股獲利點數**：`+{sim_result['points']:.2f} 點`")
                # 假設期貨 1 口 2000 股
                shares = 2000 * (int(selected_order["size"].replace("口", "")) if "口" in selected_order["size"] else 1)
                total_pnl = sim_result["points"] * shares
                st.success(f"💰 **結算總損益**：`+NT$ {int(total_pnl):,}`")
            else:
                st.warning("部位仍在倉浮動中，未觸發 T1 平倉。")
        st.caption(f"**詳細執法判定備註**：{sim_result['result']}")

# ------------------------------------------------------------------------------
# TAB 4: 盤中走勢即時監控 (yFinance 串接)
# ------------------------------------------------------------------------------
with tab_live:
    st.subheader("📈 實時 5 分 K 線走勢圖與雙方防線對照")
    
    chart_ticker = st.selectbox("選擇要載入實時圖表的標的：", list(WATCHLIST_DB.keys()), format_func=lambda x: f"{x} {WATCHLIST_DB[x]['name']}")
    market_ext = ".TWO" if WATCHLIST_DB[chart_ticker]["market"] == "OTC" else ".TW"
    full_code = f"{chart_ticker}{market_ext}"
    
    col_k1, col_k2 = st.columns([3, 1])
    
    with col_k1:
        try:
            stock_data = yf.Ticker(full_code)
            k_df = stock_data.history(period="3d", interval="5m")
            
            if not k_df.empty:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
                fig.add_trace(go.Candlestick(
                    x=k_df.index, open=k_df['Open'], high=k_df['High'], low=k_df['Low'], close=k_df['Close'],
                    name="5分K"
                ), row=1, col=1)
                fig.add_trace(go.Bar(
                    x=k_df.index, y=k_df['Volume'], name="成交量", marker_color='rgba(100, 149, 237, 0.6)'
                ), row=2, col=1)
                
                # 繪製 Gemini 與 GPT 門檻線
                g_match = next((x for x in ORDERS_GEMINI if x["ticker"] == chart_ticker), None)
                c_match = next((x for x in ORDERS_CHATGPT if x["ticker"] == chart_ticker), None)
                
                if g_match:
                    fig.add_hline(y=g_match["trigger"], line_dash="dash", line_color="red", annotation_text=f"Gemini 門檻: {g_match['trigger']}", row=1, col=1)
                    fig.add_hline(y=g_match["t1"], line_dash="dot", line_color="green", annotation_text=f"Gemini T1: {g_match['t1']}", row=1, col=1)
                if c_match:
                    fig.add_hline(y=c_match["trigger"], line_dash="dash", line_color="blue", annotation_text=f"GPT 門檻: {c_match['trigger']}", row=1, col=1)
                    fig.add_hline(y=c_match["t1"], line_dash="dot", line_color="cyan", annotation_text=f"GPT T1: {c_match['t1']}", row=1, col=1)
                    
                fig.update_layout(height=480, margin=dict(l=20, r=20, t=30, b=20), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"目前無即時 K 線數據，待盤中連線撮合。")
        except Exception as err:
            st.error(f"連線異常：{err}")
            
    with col_k2:
        st.markdown("#### 🎯 雙方門檻對照")
        g_rule = next((x for x in ORDERS_GEMINI if x["ticker"] == chart_ticker), None)
        c_rule = next((x for x in ORDERS_CHATGPT if x["ticker"] == chart_ticker), None)
        
        if g_rule:
            st.markdown(f"**🟥 Gemini ({g_rule['rank']})**")
            st.write(f"- 進場：`< {g_rule['trigger']}`")
            st.write(f"- 停損：`{g_rule['stop']}`")
            st.write(f"- **T1**：`{g_rule['t1']}`")
            st.write(f"- **T2**：`{g_rule['t2']}`")
        else:
            st.caption("🟥 Gemini：未選入 TOP 5 / 空手")
            
        st.markdown("---")
        if c_rule:
            st.markdown(f"**🟦 ChatGPT ({c_rule['rank']})**")
            st.write(f"- 進場：`< {c_rule['trigger']}`")
            st.write(f"- 停損：`{c_rule['stop']}`")
            st.write(f"- **T1**：`{c_rule['t1']}`")
            st.write(f"- **T2**：`{c_rule['t2']}`")
        else:
            st.caption("🟦 ChatGPT：未選入 TOP 5 / 空手")

# ==============================================================================
# 8. 系統頁尾
# ==============================================================================
st.markdown("---")
st.caption(f"短空雷達量化監控系統 v11.0｜Round 11 決戰專用版｜執法公約：5分K實體跌破 + 不利撮合滑價 + 方案A鎖利 + 13:25強平結算")
