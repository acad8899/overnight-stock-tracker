import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ==============================================================================
# 1. 系統架構與客製化專業 UI 配置
# ==============================================================================
st.set_page_config(
    page_title="雙 AI 量化短空雷達監控系統 - Round 11",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 專業高對比深色戰情室樣式
st.markdown("""
<style>
    .metric-card-gemini {
        background: linear-gradient(135deg, #1E1E1E 0%, #2A1B1B 100%);
        border-radius: 8px;
        padding: 14px;
        border-left: 5px solid #FF4444;
        margin-bottom: 12px;
    }
    .metric-card-gpt {
        background: linear-gradient(135deg, #1E1E1E 0%, #1A2634 100%);
        border-radius: 8px;
        padding: 14px;
        border-left: 5px solid #1E88E5;
        margin-bottom: 12px;
    }
    .stDataFrame {
        border-radius: 6px;
    }
    .badge-short {
        background-color: #D32F2F;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-ban {
        background-color: #616161;
        color: #FFD54F;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. 官方公約常數與雙方帳戶狀態 (2026/09/16 R10 結算後正式凍結生效)
# ==============================================================================
R11_DATE = "2026/09/17"
DATA_BASE_DATE = "2026/09/16"

# 帳戶資本與風控額度
CAPITAL_GEMINI = 1620595
CAPITAL_CHATGPT = 1289681
LIMIT_GEMINI = int(CAPITAL_GEMINI * 0.20)    # NT$ 324,119
LIMIT_CHATGPT = int(CAPITAL_CHATGPT * 0.20)  # NT$ 257,936
NET_SPREAD = CAPITAL_GEMINI - CAPITAL_CHATGPT # NT$ 330,914

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
# 4. 雙方 Round 11 正式決戰封單名冊 (官方裁判室存證凍結標準)
# ==============================================================================
ORDERS_GEMINI = [
    {"rank": "🥇 首選 1", "ticker": "2455", "name": "全新(期)", "tool": "期貨", "size": "1口", "margin": 139050, "trigger": 512.0, "stop": 526.0, "t1": 498.0, "t2": 488.0, "shares": 2000, "reason": "逆勢收黑，外資砍1,700張，融資暴增+627張深套。"},
    {"rank": "🥈 首選 2", "ticker": "8039", "name": "台虹(期)", "tool": "期貨", "size": "2口", "margin": 110200, "trigger": 273.0, "stop": 280.0, "t1": 264.0, "t2": 258.0, "shares": 4000, "reason": "小摩單點倒13.9%，散戶融資連四日逆勢接刀。"},
    {"rank": "🥉 首選 3", "ticker": "6173", "name": "信昌電(期)", "tool": "期貨", "size": "2口", "margin": 170100, "trigger": 312.0, "stop": 322.0, "t1": 302.0, "t2": 295.0, "shares": 4000, "reason": "隔日沖重鎖2,600張，融資兩天增逾900張。"},
    {"rank": "4", "ticker": "3189", "name": "景碩(期)", "tool": "期貨", "size": "1口", "margin": 221400, "trigger": 814.0, "stop": 833.0, "t1": 792.0, "t2": 778.0, "shares": 2000, "reason": "融資暴增+720張居冠，大摩調節，認購大停損。"},
    {"rank": "5", "ticker": "2327", "name": "國巨*(期)", "tool": "期貨", "size": "1口", "margin": 144720, "trigger": 533.0, "stop": 544.0, "t1": 519.0, "t2": 508.0, "shares": 2000, "reason": "逆勢收黑，美林重砍2,640張，融資逆勢套牢。"}
]

ORDERS_CHATGPT = [
    {"rank": "🥇 1", "ticker": "2455", "name": "全新(期)", "tool": "期貨", "size": "1口", "margin": 139050, "trigger": 510.0, "stop": 524.0, "t1": 500.0, "t2": 492.0, "shares": 2000, "reason": "法人重賣＋融資大增，破510進場。"},
    {"rank": "🥈 2", "ticker": "8039", "name": "台虹(期)", "tool": "期貨", "size": "2口", "margin": 110200, "trigger": 271.0, "stop": 279.0, "t1": 263.0, "t2": 257.0, "shares": 4000, "reason": "法人連賣＋融資增加，破271進場。"},
    {"rank": "🥉 3", "ticker": "3189", "name": "景碩(期)", "tool": "期貨", "size": "1口", "margin": 221400, "trigger": 810.0, "stop": 832.0, "t1": 795.0, "t2": 780.0, "shares": 2000, "reason": "融資暴增＋高檔震盪，破810進場。"},
    {"rank": "4", "ticker": "2327", "name": "國巨(期)", "tool": "期貨", "size": "1口", "margin": 144720, "trigger": 526.0, "stop": 544.0, "t1": 518.0, "t2": 510.0, "shares": 2000, "reason": "外資巨量撤退，摜破昨低526才進場。"},
    {"rank": "5", "ticker": "3037", "name": "欣興(期)", "tool": "期貨", "size": "1口", "margin": 259470, "trigger": 940.0, "stop": 975.0, "t1": 925.0, "t2": 910.0, "shares": 2000, "reason": "高盛重砍，法人連續轉弱，破940進場。"}
]

# ==============================================================================
# 5. 量化引擎：不利撮合滑價、實體黑棒破線濾網與方案 A 結算器
# ==============================================================================
def execute_quant_settlement(order, k_open, k_close, k_low, k_high, next_k_open, exit_k_close=None):
    """
    官方執法標準：
    1. 實體黑棒收破確認：k_close < k_open 且 k_close < trigger_price
    2. 不利滑價成交價：min(k_close, next_k_open) (取較劣者)
    3. 方案 A 階梯鎖利：k_low <= t1_price 則全數依 T1 保底平倉
    4. 停損檢核：k_high >= stop_price 則以 stop_price 停損離場
    5. 尾盤強平：未達 T1 且未停損，以 exit_k_close (13:25) 強制平倉
    """
    trigger_p = float(order["trigger"])
    stop_p = float(order["stop"])
    t1_p = float(order["t1"])
    shares = order["shares"]
    
    # 1. 實體黑棒與破線檢核
    if not (k_close < k_open and k_close < trigger_p):
        return {
            "status": "⚪ 未觸發 (空手觀望)",
            "entry_price": None,
            "exit_price": None,
            "pnl_points": 0.0,
            "pnl_ntd": 0,
            "note": f"5分K實體未收破門檻 {trigger_p} 或非實體黑棒，風控濾網生效，空手避險。"
        }
    
    # 2. 不利滑價撮合
    entry_p = min(k_close, next_k_open)
    
    # 3. 停損判定 (優先於停利若同時發生)
    if k_high >= stop_p:
        pts = entry_p - stop_p
        ntd = int(pts * shares)
        return {
            "status": "❌ 停損平倉",
            "entry_price": entry_p,
            "exit_price": stop_p,
            "pnl_points": pts,
            "pnl_ntd": ntd,
            "note": f"盤中高點 {k_high} 穿破停損線 {stop_p}，嚴格停損離場。"
        }
        
    # 4. 方案 A 階梯鎖利判定
    if k_low <= t1_p:
        pts = entry_p - t1_p
        ntd = int(pts * shares)
        return {
            "status": "🎯 方案 A 停利 (命中 T1)",
            "entry_price": entry_p,
            "exit_price": t1_p,
            "pnl_points": pts,
            "pnl_ntd": ntd,
            "note": f"盤中低點 {k_low} 擊穿 T1 ({t1_p})，依方案 A 全數保底平倉落袋！"
        }
        
    # 5. 尾盤 13:25 強制平倉
    if exit_k_close is not None:
        pts = entry_p - exit_k_close
        ntd = int(pts * shares)
        return {
            "status": "⏰ 尾盤強制平倉",
            "entry_price": entry_p,
            "exit_price": exit_k_close,
            "pnl_points": pts,
            "pnl_ntd": ntd,
            "note": f"未達 T1 且未觸發停損，依公約於 13:25 以市價 {exit_k_close} 強制平倉。"
        }
        
    return {
        "status": "⏳ 部位持倉中",
        "entry_price": entry_p,
        "exit_price": None,
        "pnl_points": 0.0,
        "pnl_ntd": 0,
        "note": f"部位建立於不利滑價 {entry_p}，等待觸發 T1 或 13:25 結算。"
    }

# ==============================================================================
# 6. 側邊欄控制與雙方戰情儀表板
# ==============================================================================
st.sidebar.title("⚡ 短空雷達量化控制台")
st.sidebar.markdown(f"**決戰輪次**：`Round 11` ({R11_DATE})")
st.sidebar.markdown(f"**母池數據基準**：`{DATA_BASE_DATE}` 盤後大數據")

# 淨值儀表板
st.sidebar.markdown("---")
st.sidebar.subheader("🏆 賽事即時戰績榜")
st.sidebar.markdown(f"""
<div class="metric-card-gemini">
    <div style="font-size: 13px; color: #BBB;">🟥 Gemini 淨值 (7勝1負2平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_GEMINI:,}</div>
    <div style="font-size: 12px; color: #81C784;">R10 全數空手避軋 (損益 $0)</div>
</div>
<div class="metric-card-gpt">
    <div style="font-size: 13px; color: #BBB;">🟦 ChatGPT 淨值 (1勝7負2平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CHATGPT:,}</div>
    <div style="font-size: 12px; color: #81C784;">R10 全數空手避軋 (損益 $0)</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.info(f"🚩 **當前戰況**：Gemini 領先 **NT$ {NET_SPREAD:,}**\n\n**單檔配置上限**：\n• Gemini: NT$ {LIMIT_GEMINI:,}\n• ChatGPT: NT$ {LIMIT_CHATGPT:,}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📜 官方執法核心規範")
st.sidebar.caption(
    """
    1. **實體確認**：5分K收盤 < 開盤 且 收盤 < 進場價。
    2. **不利滑價**：成交價 = min(觸發K收, 次K開)。
    3. **方案 A 優先**：穿破 T1 立即全平保底。
    4. **尾盤強平**：13:25～13:30 強制平倉清算。
    """
)

# ==============================================================================
# 7. 主介面分頁架構
# ==============================================================================
st.title("🎯 雙 AI 當沖量化 PK 賽事｜Round 11 決戰戰情室")
st.caption(f"實時連線 OFFICIATING TERMINAL｜數據源：{DATA_BASE_DATE} 臺灣證券交易所/櫃買中心/30+主力分點/自營商權證")

tab_orders, tab_radar, tab_matcher, tab_live = st.tabs([
    "⚔️ R11 雙方正式封單陣列", 
    "📊 12檔母池三維籌碼雷達", 
    "🧮 官方不利撮合與方案A結算終端", 
    "📈 盤中 5分K 防線監控圖"
])

# ------------------------------------------------------------------------------
# TAB 1: R11 雙方正式封單陣列 (保證寬版不截斷外顯 T1/T2)
# ------------------------------------------------------------------------------
with tab_orders:
    st.subheader("⚔️ Round 11 官方決戰名冊陣列 (已完成資料庫凍結備查)")
    col_g, col_c = st.columns(2)
    
    with col_g:
        st.markdown("#### 🟥 Gemini 戰情室封單")
        st.caption(f"淨值：NT$ {CAPITAL_GEMINI:,}｜單檔上限：NT$ {LIMIT_GEMINI:,}")
        
        df_gem_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "停利 T1": f"{x['t1']:.1f}", "停利 T2": f"{x['t2']:.1f}", "規格/保證金": f"{x['size']} ({x['margin']//1000}K)"}
            for x in ORDERS_GEMINI
        ])
        st.dataframe(df_gem_ui, use_container_width=True, hide_index=True)
        
        with st.expander("🔍 審視 Gemini 籌碼依據與量化細節", expanded=True):
            for x in ORDERS_GEMINI:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']:.1f}`**")
                st.caption(f"└ 核心籌碼：{x['reason']}")
                
    with col_c:
        st.markdown("#### 🟦 ChatGPT 戰情室封單")
        st.caption(f"淨值：NT$ {CAPITAL_CHATGPT:,}｜單檔上限：NT$ {LIMIT_CHATGPT:,}")
        
        df_gpt_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "停利 T1": f"{x['t1']:.1f}", "停利 T2": f"{x['t2']:.1f}", "規格/保證金": f"{x['size']} ({x['margin']//1000}K)"}
            for x in ORDERS_CHATGPT
        ])
        st.dataframe(df_gpt_ui, use_container_width=True, hide_index=True)
        
        with st.expander("🔍 審視 ChatGPT 型態邏輯與作戰口令", expanded=True):
            for x in ORDERS_CHATGPT:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']:.1f}`**")
                st.caption(f"└ 作戰型態：{x['reason']}")

    st.markdown("---")
    st.subheader("🛑 Round 11 官方共識禁空名單（NO SHORT LIST）")
    cn1, cn2, cn3 = st.columns(3)
    cn1.error("🚫 **3406 玉晶光**\n\n強勢漲停鎖死在 1,005 元，多頭籌碼極端擁擠，官方公約維持絕對禁空，嚴防摸頂。")
    cn2.error("🚫 **2344 華邦電**\n\n外資高盛美林暴買 1.2 萬張，融資狂退 -2,056 張洗淨籌碼，空方肉身縮小，嚴禁追空。")
    cn3.error("🚫 **2408 南亞科**\n\n元大美林大摩反手狂買，股價飆漲 5.8%，融資大退 -741 張，結構由空翻多不可做空。")

# ------------------------------------------------------------------------------
# TAB 2: 12檔母池三維籌碼雷達
# ------------------------------------------------------------------------------
with tab_radar:
    st.subheader("📋 12 檔母池三維大數據全景表 (主力分點 × 融資 × 權證)")
    
    radar_rows = []
    for t_code, t_val in WATCHLIST_DB.items():
        radar_rows.append({
            "代號": t_code,
            "標的名稱": t_val["name"],
            "收盤價": f"{t_val['close']:.2f}",
            "漲跌": f"{t_val['change']:+.2f}",
            "成交量": f"{t_val['volume']:,}",
            "融資增減(張)": f"{t_val['margin_diff']:+d}",
            "近高(NH)": f"{t_val['nh']:.2f}",
            "全高(AH)": f"{t_val['ah']:.2f}",
            "認購增減(萬)": f"{t_val['warrant_call']:+d}",
            "偏空診斷評級": t_val["status"]
        })
    st.dataframe(pd.DataFrame(radar_rows), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🔎 主力分點進出與避險破綻深度探針")
    target_select = st.selectbox("選擇要檢驗籌碼分點的標的：", list(WATCHLIST_DB.keys()), format_func=lambda x: f"{x} {WATCHLIST_DB[x]['name']} ({WATCHLIST_DB[x]['status']})")
    
    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        st.markdown(f"### **{target_select} {WATCHLIST_DB[target_select]['name']}**")
        st.write(f"- **收盤價**：`{WATCHLIST_DB[target_select]['close']:.2f}` ({WATCHLIST_DB[target_select]['change']:+.2f})")
        st.write(f"- **融資增減**：`{WATCHLIST_DB[target_select]['margin_diff']:+d} 張`")
        st.write(f"- **權證認購增減**：`{WATCHLIST_DB[target_select]['warrant_call']:+d} 萬元`")
        st.write(f"- **系統評級**：`{WATCHLIST_DB[target_select]['status']}`")
    with col_d2:
        st.markdown(f"**核心量化診斷**：{WATCHLIST_DB[target_select]['diagnosis']}")
        info = WATCHLIST_DB[target_select]
        cb, cs = st.columns(2)
        with cb:
            st.markdown("**🟢 主力買超前三**")
            for b_name, b_vol, b_p in info["major_buy"]:
                st.markdown(f"- **{b_name}**：`+{b_vol:,} 張` (均價: `{b_p:.2f}`)")
        with cs:
            st.markdown("**🔴 主力賣超前三**")
            for s_name, s_vol, s_p in info["major_sell"]:
                st.markdown(f"- **{s_name}**：`{s_vol:,} 張` (均價: `{s_p:.2f}`)")

# ------------------------------------------------------------------------------
# TAB 3: 撮合與方案 A 結算終端
# ------------------------------------------------------------------------------
with tab_matcher:
    st.subheader("🧮 裁判室專用：5分K實體跌破撮合與方案 A 結算模擬器")
    st.caption("依據官方公約：取不利撮合價進場，盤中穿破 T1 即刻鎖利，未達條件者於 13:25 強制結算。")
    
    sim_c1, sim_c2 = st.columns(2)
    with sim_c1:
        st.markdown("**步驟 1：選擇審查選手與訂單**")
        selected_side = st.radio("參賽陣營：", ["🟥 Gemini 戰情室", "🟦 ChatGPT 戰情室"], horizontal=True)
        order_set = ORDERS_GEMINI if "Gemini" in selected_side else ORDERS_CHATGPT
        
        target_order = st.selectbox(
            "選擇審查標的封單：",
            order_set,
            format_func=lambda x: f"{x['rank']} {x['name']} (門檻 < {x['trigger']:.1f}, 停損: {x['stop']:.1f}, T1: {x['t1']:.1f})"
        )
        
        st.markdown("**步驟 2：輸入盤面 5 分 K 實體與走勢價位**")
        k_open_in = st.number_input("觸發 5 分 K 開盤價：", value=float(target_order["trigger"]) + 1.0, step=0.5)
        k_close_in = st.number_input("觸發 5 分 K 收盤價：", value=float(target_order["trigger"]) - 0.5, step=0.5)
        next_open_in = st.number_input("次一根 5 分 K 開盤價：", value=float(target_order["trigger"]) - 1.0, step=0.5)
        k_high_in = st.number_input("盤中最高價 (檢驗停損)：", value=float(target_order["stop"]) - 2.0, step=0.5)
        k_low_in = st.number_input("盤中最低價 (檢驗方案 A T1)：", value=float(target_order["t1"]) - 1.0, step=0.5)
        exit_close_in = st.number_input("13:25 尾盤強制平倉價 (備用)：", value=float(target_order["trigger"]) - 3.0, step=0.5)
        
    with sim_c2:
        st.markdown("**步驟 3：官方仲裁自動計算結果**")
        res = execute_quant_settlement(
            order=target_order,
            k_open=k_open_in,
            k_close=k_close_in,
            k_low=k_low_in,
            k_high=k_high_in,
            next_k_open=next_open_in,
            exit_k_close=exit_close_in
        )
        
        st.info(f"**判定狀態**：{res['status']}")
        if res["entry_price"] is not None:
            st.write(f"- **不利滑價撮合價**：`{res['entry_price']:.2f}` (取觸發K收盤 {k_close_in} 與次K開盤 {next_open_in} 較劣者)")
            if res["exit_price"] is not None:
                st.write(f"- **出場平倉價**：`{res['exit_price']:.2f}`")
                st.write(f"- **單股價差點數**：`{res['pnl_points']:+.2f} 點`")
                if res['pnl_ntd'] > 0:
                    st.success(f"💰 **核定結算總損益**：`+NT$ {res['pnl_ntd']:,}`")
                else:
                    st.error(f"📉 **核定結算總損益**：`-NT$ {abs(res['pnl_ntd']):,}`")
        st.caption(f"**仲裁備註**：{res['note']}")

# ------------------------------------------------------------------------------
# TAB 4: 盤中走勢即時圖表監控
# ------------------------------------------------------------------------------
with tab_live:
    st.subheader("📈 實時 5 分 K 線走勢圖與雙方作戰防線")
    
    live_ticker = st.selectbox("選擇要繪製圖表的標的：", list(WATCHLIST_DB.keys()), format_func=lambda x: f"{x} {WATCHLIST_DB[x]['name']}")
    market_suffix = ".TWO" if WATCHLIST_DB[live_ticker]["market"] == "OTC" else ".TW"
    full_ticker = f"{live_ticker}{market_suffix}"
    
    col_chart, col_rules = st.columns([3, 1])
    with col_chart:
        try:
            stock = yf.Ticker(full_ticker)
            k_hist = stock.history(period="3d", interval="5m")
            
            if not k_hist.empty:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
                fig.add_trace(go.Candlestick(
                    x=k_hist.index, open=k_hist['Open'], high=k_hist['High'], low=k_hist['Low'], close=k_hist['Close'],
                    name="5分K線"
                ), row=1, col=1)
                fig.add_trace(go.Bar(
                    x=k_hist.index, y=k_hist['Volume'], name="成交量", marker_color='rgba(100, 149, 237, 0.5)'
                ), row=2, col=1)
                
                # 疊加 Gemini 標記
                gm = next((x for x in ORDERS_GEMINI if x["ticker"] == live_ticker), None)
                if gm:
                    fig.add_hline(y=gm["trigger"], line_dash="dash", line_color="red", annotation_text=f"Gemini 進場: {gm['trigger']}", row=1, col=1)
                    fig.add_hline(y=gm["t1"], line_dash="dot", line_color="green", annotation_text=f"Gemini T1: {gm['t1']}", row=1, col=1)
                    fig.add_hline(y=gm["stop"], line_dash="dashdot", line_color="orange", annotation_text=f"Gemini 停損: {gm['stop']}", row=1, col=1)
                    
                # 疊加 GPT 標記
                cm = next((x for x in ORDERS_CHATGPT if x["ticker"] == live_ticker), None)
                if cm:
                    fig.add_hline(y=cm["trigger"], line_dash="dash", line_color="blue", annotation_text=f"GPT 進場: {cm['trigger']}", row=1, col=1)
                    fig.add_hline(y=cm["t1"], line_dash="dot", line_color="cyan", annotation_text=f"GPT T1: {cm['t1']}", row=1, col=1)
                    fig.add_hline(y=cm["stop"], line_dash="dashdot", line_color="purple", annotation_text=f"GPT 停損: {cm['stop']}", row=1, col=1)
                
                fig.update_layout(height=500, margin=dict(l=20, r=20, t=30, b=20), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("目前非盤中連線時段或尚無資料，請待開盤串接。")
        except Exception as e:
            st.error(f"連線載入圖表失敗：{e}")
            
    with col_rules:
        st.markdown("#### 🎯 雙方防線速覽")
        gm_info = next((x for x in ORDERS_GEMINI if x["ticker"] == live_ticker), None)
        cm_info = next((x for x in ORDERS_CHATGPT if x["ticker"] == live_ticker), None)
        
        if gm_info:
            st.markdown(f"**🟥 Gemini ({gm_info['rank']})**")
            st.write(f"- 門檻：`< {gm_info['trigger']:.1f}`")
            st.write(f"- 停損：`{gm_info['stop']:.1f}`")
            st.write(f"- **T1**：`{gm_info['t1']:.1f}`")
            st.write(f"- **T2**：`{gm_info['t2']:.1f}`")
        else:
            st.caption("🟥 Gemini：未入選 TOP 5")
            
        st.markdown("---")
        if cm_info:
            st.markdown(f"**🟦 ChatGPT ({cm_info['rank']})**")
            st.write(f"- 門檻：`< {cm_info['trigger']:.1f}`")
            st.write(f"- 停損：`{cm_info['stop']:.1f}`")
            st.write(f"- **T1**：`{cm_info['t1']:.1f}`")
            st.write(f"- **T2**：`{cm_info['t2']:.1f}`")
        else:
            st.caption("🟦 ChatGPT：未入選 TOP 5")

# ==============================================================================
# 8. 系統頁尾宣告
# ==============================================================================
st.markdown("---")
st.caption(f"雙 AI 當沖量化短空雷達系統 v11.0｜裁判室官方核定版｜執法標準：5分K實體破線 + 不利滑價撮合 + 方案A保底鎖利 + 13:25強平清算")
