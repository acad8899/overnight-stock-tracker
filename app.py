# -*- coding: utf-8 -*-
"""
雙 AI 量化短空雷達 (Season 2 Round 1 開幕戰旗艦裁判長版) - app.py (v21.1)
==============================================================================
版本更新重點：
1. 完整整合：恢復「🖥️ 專業操盤工作台」，包含即時 5 分 K 線（雙均線+VWAP+量能+主力力道）與互動懸浮抬頭顯示器。
2. 賽季晉級：正式進入 Season 2 Round 1 (S2-R1)，基準日為 2026/10/02 三維大數據。
3. 起始淨值：雙方起始資金歸零重置為各 NT$ 1,000,000 (單檔 20% 上限 NT$ 200,000)。
4. 官方封單：完整收錄 S2-R1 雙方定案名冊（Gemini TOP 5 與 ChatGPT 官方封存名冊）。
5. 融資與權證：同步 10/02 融資 (華邦電+2478, 台虹+2220, 信昌電-1100) 與權證小哥獨門金流。
6. 七大分頁：工作台、封單陣列、撮合結算器、母池雷達、首季名人堂、融資增減走勢、主力分點明細全數回歸。
==============================================================================
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import datetime
import unicodedata
import json
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==============================================================================
# 1. 頁面排版與深色戰情室外觀設定
# ==============================================================================
st.set_page_config(
    page_title="雙 AI 量化短空雷達 (S2-R1 旗艦裁判長版)", 
    layout="wide", 
    page_icon="⚔️", 
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card-gemini {
        background: linear-gradient(135deg, #1E1E1E 0%, #2A1818 100%);
        border-radius: 8px;
        padding: 12px;
        border-left: 5px solid #FF4444;
        margin-bottom: 10px;
    }
    .metric-card-gpt {
        background: linear-gradient(135deg, #1E1E1E 0%, #162436 100%);
        border-radius: 8px;
        padding: 12px;
        border-left: 5px solid #1E88E5;
        margin-bottom: 10px;
    }
    .stDataFrame {
        border-radius: 6px;
    }
    div[role="radiogroup"] {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. 第二場公約常數與雙方帳戶狀態 (2026/10/05 開賽重置)
# ==============================================================================
S2_R1_DATE = "2026/10/05"
DATA_BASE_DATE = "2026/10/02"
MARGIN_DISPLAY_DATE = "10/02"

CAPITAL_GEMINI = 1000000     # Season 2 重置起始本金
CAPITAL_CHATGPT = 1000000    # Season 2 重置起始本金
LIMIT_GEMINI = int(CAPITAL_GEMINI * 0.20)    # NT$ 200,000
LIMIT_CHATGPT = int(CAPITAL_CHATGPT * 0.20)  # NT$ 200,000
NET_SPREAD = CAPITAL_GEMINI - CAPITAL_CHATGPT # NT$ 0

MAX_STOP_LOSS_NTD = 20000

STOCK_FUTURES_SET = {
    "2408", "3042", "2449", "3231", "2327", "2376", "6488", "2313", "2492",
    "2330", "2317", "2454", "2382", "2603", "2609", "2344", "3037", "2368", "3017",
    "2383", "1519", "8210", "2059", "4551", "5289", "8299", "3406",
    "2615", "8039", "5314", "2489", "3006", "2337", "8046", "2426", "2455", "3189",
    "3374", "6239", "6173"
}

STOCK_NAME_DICT = {
    "2327": "國巨*", "2455": "全新", "2492": "華新科", "8039": "台虹", "3189": "景碩",
    "3037": "欣興", "2408": "南亞科", "2313": "華通", "3406": "玉晶光", "2344": "華邦電",
    "3042": "晶技", "6173": "信昌電"
}
NAME_TO_CODE_DICT = {v: k for k, v in STOCK_NAME_DICT.items()}

# ==============================================================================
# 3. 2026-10-02 盤後 12 檔母池三維大數據庫 (分點 + 官方融資 + 權證金流)
# ==============================================================================
DEFAULT_WATCHLIST_S2R1 = [
    {
        "代號": "6173", "名稱": "信昌電", "昨收": 303.00, "昨日鎖碼量": 24376, "融資增減(張)": -1100, "券資比": 4.0, "權證認售(萬)": 138, "權證認購(萬)": 0,
        "最高價": 322.50, "最低價": 299.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 2078, "均價": 313.97, "佔比": 8.52},
            {"分點": "富邦", "買超": 592, "均價": 311.05, "佔比": 2.43},
            {"分點": "群益金鼎", "買超": -781, "均價": 309.20, "佔比": -3.20},
            {"分點": "凱基", "買超": -341, "均價": 314.06, "佔比": -1.40},
            {"分點": "國泰", "買超": -182, "均價": 314.45, "佔比": -0.75}
        ]
    },
    {
        "代號": "2344", "名稱": "華邦電", "昨收": 179.00, "昨日鎖碼量": 74491, "融資增減(張)": 2478, "券資比": 2.5, "權證認售(萬)": -27, "權證認購(萬)": 0,
        "最高價": 184.00, "最低價": 177.50,
        "主力分點": [
            {"分點": "元大", "買超": 3007, "均價": 179.75, "佔比": 4.04},
            {"分點": "台灣摩根士丹利", "買超": 1403, "均價": 179.81, "佔比": 1.88},
            {"分點": "凱基-站前", "買超": -10092, "均價": 178.73, "佔比": -13.55},
            {"分點": "富邦", "買超": -3825, "均價": 179.05, "佔比": -5.13},
            {"分點": "美林", "買超": -1230, "均價": 179.17, "佔比": -1.65}
        ]
    },
    {
        "代號": "8039", "名稱": "台虹", "昨收": 296.00, "昨日鎖碼量": 19171, "融資增減(張)": 2220, "券資比": 4.8, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 296.00, "最低價": 280.50,
        "主力分點": [
            {"分點": "新光", "買超": 424, "均價": 291.83, "佔比": 2.21},
            {"分點": "凱基-信義", "買超": 329, "均價": 294.80, "佔比": 1.72},
            {"分點": "國票-敦北法人", "買超": -566, "均價": 283.78, "佔比": -2.95},
            {"分點": "摩根大通", "買超": -429, "均價": 293.09, "佔比": -2.24},
            {"分點": "統一", "買超": -409, "均價": 283.98, "佔比": -2.13}
        ]
    },
    {
        "代號": "3042", "名稱": "晶技", "昨收": 230.50, "昨日鎖碼量": 43452, "融資增減(張)": 1121, "券資比": 3.8, "權證認售(萬)": 0, "權證認購(萬)": -2065,
        "最高價": 232.50, "最低價": 217.50,
        "主力分點": [
            {"分點": "凱基", "買超": 1603, "均價": 228.71, "佔比": 3.69},
            {"分點": "群益金鼎", "買超": 801, "均價": 227.44, "佔比": 1.84},
            {"分點": "凱基-台北", "買超": -672, "均價": 224.91, "佔比": -1.55},
            {"分點": "元大", "買超": -509, "均價": 225.26, "佔比": -1.17},
            {"分點": "摩根大通", "買超": -318, "均價": 223.61, "佔比": -0.73}
        ]
    },
    {
        "代號": "2455", "名稱": "全新", "昨收": 580.00, "昨日鎖碼量": 4299, "融資增減(張)": -274, "券資比": 4.5, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 580.00, "最低價": 551.00,
        "主力分點": [
            {"分點": "美商高盛", "買超": 666, "均價": 569.23, "佔比": 15.49},
            {"分點": "台灣摩根士丹利", "買超": 488, "均價": 567.71, "佔比": 11.35},
            {"分點": "群益金鼎", "買超": -909, "均價": 563.11, "佔比": -21.14},
            {"分點": "群益金鼎-大安", "買超": -136, "均價": 571.56, "佔比": -3.16},
            {"分點": "國泰-敦南", "買超": -72, "均價": 571.10, "佔比": -1.67}
        ]
    },
    {
        "代號": "2313", "名稱": "華通", "昨收": 226.00, "昨日鎖碼量": 8635, "融資增減(張)": -190, "券資比": 3.0, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 228.00, "最低價": 224.00,
        "主力分點": [
            {"分點": "元大", "買超": 480, "均價": 226.61, "佔比": 5.56},
            {"分點": "凱基-台北", "買超": 449, "均價": 226.33, "佔比": 5.20},
            {"分點": "宏遠", "買超": -528, "均價": 225.43, "佔比": -6.11},
            {"分點": "港商野村", "買超": -128, "均價": 225.98, "佔比": -1.48},
            {"分點": "富邦-南員林", "買超": -65, "均價": 228.00, "佔比": -0.75}
        ]
    },
    {
        "代號": "2327", "名稱": "國巨*", "昨收": 626.00, "昨日鎖碼量": 106667, "融資增減(張)": 579, "券資比": 3.5, "權證認售(萬)": 112, "權證認購(萬)": 2981,
        "最高價": 647.00, "最低價": 598.00,
        "主力分點": [
            {"分點": "美林", "買超": 2184, "均價": 624.35, "佔比": 2.05},
            {"分點": "花旗環球", "買超": 2099, "均價": 636.74, "佔比": 1.97},
            {"分點": "摩根大通", "買超": -3946, "均價": 628.11, "佔比": -3.70},
            {"分點": "元大", "買超": -3315, "均價": 625.87, "佔比": -3.11},
            {"分點": "富邦-新店", "買超": -2468, "均價": 613.18, "佔比": -2.31}
        ]
    },
    {
        "代號": "2492", "名稱": "華新科", "昨收": 361.50, "昨日鎖碼量": 55788, "融資增減(張)": -1196, "券資比": 3.0, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 361.50, "最低價": 329.00,
        "主力分點": [
            {"分點": "美商高盛", "買超": 3819, "均價": 347.73, "佔比": 6.85},
            {"分點": "凱基-台北", "買超": 3079, "均價": 352.21, "佔比": 5.52},
            {"分點": "元大", "買超": -3623, "均價": 345.76, "佔比": -6.49},
            {"分點": "富邦", "買超": -2512, "均價": 339.87, "佔比": -4.50},
            {"分點": "凱基-信義", "買超": -1142, "均價": 346.42, "佔比": -2.05}
        ]
    },
    {
        "代號": "3037", "名稱": "欣興", "昨收": 1305.00, "昨日鎖碼量": 18635, "融資增減(張)": 699, "券資比": 4.5, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 1305.00, "最低價": 1215.00,
        "主力分點": [
            {"分點": "美林", "買超": 2145, "均價": 1267.48, "佔比": 11.51},
            {"分點": "美商高盛", "買超": 1879, "均價": 1262.82, "佔比": 10.08},
            {"分點": "國泰-敦南", "買超": -218, "均價": 1261.78, "佔比": -1.17},
            {"分點": "永豐金", "買超": -204, "均價": 1252.24, "佔比": -1.09},
            {"分點": "富邦", "買超": -189, "均價": 1256.17, "佔比": -1.01}
        ]
    },
    {
        "代號": "3189", "名稱": "景碩", "昨收": 1050.00, "昨日鎖碼量": 18823, "融資增減(張)": -1566, "券資比": 3.9, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 1070.00, "最低價": 1005.00,
        "主力分點": [
            {"分點": "永豐金", "買超": 1696, "均價": 1040.54, "佔比": 9.01},
            {"分點": "台灣摩根士丹利", "買超": 810, "均價": 1035.33, "佔比": 4.30},
            {"分點": "元大", "買超": -871, "均價": 1038.28, "佔比": -4.63},
            {"分點": "美商高盛", "買超": -319, "均價": 1048.28, "佔比": -1.69},
            {"分點": "凱基-台南", "買超": -227, "均價": 1029.95, "佔比": -1.21}
        ]
    },
    {
        "代號": "2408", "名稱": "南亞科", "昨收": 526.00, "昨日鎖碼量": 36677, "融資增減(張)": -342, "券資比": 3.2, "權證認售(萬)": 71, "權證認購(萬)": -2724,
        "最高價": 534.00, "最低價": 521.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 3220, "均價": 528.50, "佔比": 8.78},
            {"分點": "美商高盛", "買超": 1862, "均價": 529.22, "佔比": 5.08},
            {"分點": "凱基-站前", "買超": -1045, "均價": 525.95, "佔比": -2.85},
            {"分點": "國泰-敦南", "買超": -455, "均價": 528.14, "佔比": -1.24},
            {"分點": "兆豐-城中", "買超": -242, "均價": 529.70, "佔比": -0.66}
        ]
    },
    {
        "代號": "3406", "名稱": "玉晶光", "昨收": 961.00, "昨日鎖碼量": 4816, "融資增減(張)": 208, "券資比": 4.1, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 974.00, "最低價": 929.00,
        "主力分點": [
            {"分點": "統一", "買超": 360, "均價": 956.26, "佔比": 7.48},
            {"分點": "台新", "買超": 59, "均價": 957.87, "佔比": 1.23},
            {"分點": "凱基-台北", "買超": -237, "均價": 949.84, "佔比": -4.92},
            {"分點": "元大", "買超": -176, "均價": 950.04, "佔比": -3.65},
            {"分點": "花旗環球", "買超": -95, "均價": 952.25, "佔比": -1.97}
        ]
    }
]

# ==============================================================================
# 4. 第二場 Round 1 雙方正式定案封單陣列
# ==============================================================================
ORDERS_GEMINI_S2R1 = [
    {"rank": "🥇 1", "ticker": "6173", "name": "信昌電(期)", "tool": "個股期", "size": "2口", "trigger": 298.5, "stop": 303.5, "t1": 291.0, "shares": 4000, "max_loss": 20000, "reason": "認售連三日奪全市場第一名(+138萬)，衝322.5留長上影，融資大退-1100張潰逃！"},
    {"rank": "🥈 2", "ticker": "2344", "name": "華邦電(期)", "tool": "個股期", "size": "2口", "trigger": 176.5, "stop": 181.5, "t1": 170.0, "shares": 4000, "max_loss": 20000, "reason": "凱基站前天量倒貨-10092張，散戶融資大接刀+2478張，高檔沉重套牢！"},
    {"rank": "🥉 3", "ticker": "8039", "name": "台虹(期)", "tool": "個股期", "size": "2口", "trigger": 291.0, "stop": 296.0, "t1": 282.0, "shares": 4000, "max_loss": 20000, "reason": "尾盤急拉引爆融資單日暴增+2220張，外資主力趁急拉全線提款出逃！"},
    {"rank": "4", "ticker": "3042", "name": "晶技(期)", "tool": "個股期", "size": "2口", "trigger": 227.0, "stop": 232.0, "t1": 219.0, "shares": 4000, "max_loss": 20000, "reason": "認購大賣-2065萬居全市場第3，自營商避險買盤將在盤中轉為回吐賣壓！"},
    {"rank": "5", "ticker": "2455", "name": "全新(期)", "tool": "個股期", "size": "1口", "trigger": 568.0, "stop": 578.0, "t1": 554.0, "shares": 2000, "max_loss": 20000, "reason": "群益金鼎單日暴砍-909張(佔比21%)，處置無承接買盤，一旦外資買盤歇息即破線！"}
]

ORDERS_CHATGPT_S2R1 = [
    {"rank": "🥇 1", "ticker": "2344", "name": "華邦電(期)", "tool": "個股期", "size": "2口", "trigger": 178.0, "stop": 183.0, "t1": 168.0, "shares": 4000, "max_loss": 20000, "reason": "站前萬張賣壓壓頂，融資+2478張散戶接刀，5分K實體跌破178追多殺多。"},
    {"rank": "🥈 2", "ticker": "8039", "name": "台虹(期)", "tool": "個股期", "size": "2口", "trigger": 280.5, "stop": 285.5, "t1": 270.5, "shares": 4000, "max_loss": 20000, "reason": "融資暴增2220張多殺多未爆彈，實體跌破280.5確認二次破底展開。"},
    {"rank": "🥉 3", "ticker": "3042", "name": "晶技(期)", "tool": "個股期", "size": "2口", "trigger": 217.5, "stop": 222.5, "t1": 207.5, "shares": 4000, "max_loss": 20000, "reason": "認購權證賣超2065萬避險回吐，實體破217.5追擊短線假突破回測。"},
    {"rank": "4", "ticker": "2455", "name": "全新(期)", "tool": "個股期", "size": "2口", "trigger": 551.0, "stop": 556.0, "t1": 541.0, "shares": 4000, "max_loss": 20000, "reason": "本土大戶提款兩成，實體摜破551確認處置流動性枯竭崩跌。"},
    {"rank": "5", "ticker": "2327", "name": "國巨(期)", "tool": "個股期", "size": "2口", "trigger": 598.0, "stop": 603.0, "t1": 588.0, "shares": 4000, "max_loss": 20000, "reason": "高檔爆量10萬張分歧換手，實體破598回測短均，603嚴格停損。"}
]

# ==============================================================================
# 5. 技術分析與動態 K 線指標模組 (核心 4 層繪圖引擎)
# ==============================================================================
def pad_display_text(text, target_display_width):
    current_width = 0
    for ch in str(text):
        if unicodedata.east_asian_width(ch) in ('F', 'W', 'A'):
            current_width += 2
        else:
            current_width += 1
    return str(text) + (" " * max(target_display_width - current_width, 0))

def calculate_pro_short_indicators(df):
    if df is None or df.empty: return pd.DataFrame()
    df = df.copy()
    closes = [float(x) for x in df["收盤"]]
    highs = [float(x) for x in df["最高"]]
    lows = [float(x) for x in df["最低"]]
    volumes = [float(x) for x in df["成交量"]]
    opens = [float(x) for x in df["開盤"]]
    
    df["5MA"] = df["收盤"].rolling(5, min_periods=1).mean().round(2)
    df["12MA"] = df["收盤"].rolling(12, min_periods=1).mean().round(2)
    df["20MA"] = df["收盤"].rolling(20, min_periods=1).mean().round(2)
    df["VOL_5MA"] = df["成交量"].rolling(5, min_periods=1).mean().round(0)

    tp = (df["最高"] + df["最低"] + df["收盤"]) / 3.0
    cum_v = df["成交量"].cumsum().replace(0, 1)
    df["VWAP"] = ((tp * df["成交量"]).cumsum() / cum_v).round(2)

    df["主力買賣超"] = [int(v * 0.18 * (1 if c >= o else -0.85)) for v, c, o in zip(volumes, closes, opens)]
    df["大戶淨力道"] = [int(round(v * (((c - l) - (h - c)) / max(h - l, 0.01)) * 0.35)) for h, l, c, o, v in zip(highs, lows, closes, opens, volumes)]
    df["累積大戶淨差"] = df["大戶淨力道"].cumsum()
    return df

@st.cache_data(ttl=180)
def fetch_real_kline(stock_code, interval="5m"):
    code_str = str(stock_code).strip()
    syms = [f"{code_str}.TWO", f"{code_str}.TW"]
    for sym in syms:
        try:
            t = yf.Ticker(sym)
            raw = t.history(period="5d", interval=interval)
            if raw is not None and not raw.empty and len(raw) >= 3:
                raw = raw.reset_index()
                tc = "Datetime" if "Datetime" in raw.columns else "Date"
                records = []
                for _, r in raw.iterrows():
                    d_str = r[tc].strftime('%m/%d %H:%M') if interval != "1d" else r[tc].strftime('%Y/%m/%d')
                    records.append({
                        "日期": d_str, "開盤": round(float(r["Open"]), 2),
                        "最高": round(float(r["High"]), 2), "最低": round(float(r["Low"]), 2),
                        "收盤": round(float(r["Close"]), 2), "成交量": int(r["Volume"]) // 1000
                    })
                df_res = pd.DataFrame(records)
                return calculate_pro_short_indicators(df_res)
        except Exception: continue
    return pd.DataFrame()

def render_interactive_kline_chart(df_k, stock_code, stock_name, broker_cost, nh_res, limit_up_price, timeframe_label):
    last = df_k.iloc[-1]
    prev_close = df_k["收盤"].iloc[-2] if len(df_k) > 1 else last["收盤"]
    change = round(float(last["收盤"]) - float(prev_close), 2)
    change_pct = round((change / float(prev_close)) * 100, 2) if float(prev_close) else 0.0
    
    chg_color = "#FF3333" if change >= 0 else "#00CC00"
    chg_symbol = "↑" if change >= 0 else "↓"
    fut_badge_html = "<span style='background-color:#1E88E5; color:#FFF; padding:1px 5px; border-radius:4px; font-weight:bold; font-size:12px; margin-left:6px;'>期</span>" if stock_code in STOCK_FUTURES_SET else ""
    
    default_info_html = (
        f"<span style='color: #FFFF00;'>{timeframe_label} {last['日期']}</span> "
        f"<span style='color: #00CC00;'>開 <span style='color:#FFF;'>{last['開盤']}</span></span> "
        f"<span style='color: #FF3333;'>高 <span style='color:#FFF;'>{last['最高']}</span></span> "
        f"<span style='color: #00CC00;'>低 <span style='color:#FFF;'>{last['最低']}</span></span> "
        f"<span style='color: {chg_color}; font-weight:bold;'>收 {last['收盤']} {chg_symbol}{change:+0.2f} ({change_pct}%)</span> "
        f"<span style='color: #FFCC00;'>5MA: {last.get('5MA', '-')}</span> "
        f"<span style='color: #33CCFF;'>20MA: {last.get('20MA', '-')}</span> "
        f"<span style='color: #FF00FF; font-weight:bold;'>VWAP: {last.get('VWAP', '-')}</span>"
    )

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.48, 0.16, 0.16, 0.20],
        subplot_titles=(
            "",
            f"<span style='color:#FF3333; font-size:11px;'>成交量: {int(last.get('成交量', 0))} 張</span>",
            f"<span style='color:#00E5FF; font-size:11px;'>主力分點買賣超: {int(last.get('主力買賣超', 0))} 張</span>",
            f"<span style='color:#FF9900; font-size:11px;'>主力大戶淨力道: {int(last.get('大戶淨力道', 0)):+} 張</span>"
        )
    )
    
    kline_lookup_dict = {}
    for i in range(len(df_k)):
        r = df_k.iloc[i]
        d_key = str(r["日期"])
        p_val = float(df_k["收盤"].iloc[i-1]) if i > 0 else float(r["收盤"])
        c_val = float(r["收盤"])
        chg = round(c_val - p_val, 2)
        pct = round((chg / p_val) * 100, 2) if p_val else 0.0
        kline_lookup_dict[d_key] = (
            f"<span style='color: #FFFF00;'>{timeframe_label} {d_key}</span> "
            f"<span style='color: #00CC00;'>開 <span style='color:#FFF;'>{r['開盤']}</span></span> "
            f"<span style='color: #FF3333;'>高 <span style='color:#FFF;'>{r['最高']}</span></span> "
            f"<span style='color: #00CC00;'>低 <span style='color:#FFF;'>{r['最低']}</span></span> "
            f"<span style='color: {'#FF3333' if pct>=0 else '#00CC00'}; font-weight:bold;'>收 {r['收盤']} ({pct:+}%)</span> "
            f"<span style='color: #FFCC00;'>5MA: {r.get('5MA', '-')}</span> "
            f"<span style='color: #33CCFF;'>20MA: {r.get('20MA', '-')}</span> "
            f"<span style='color: #FF00FF; font-weight:bold;'>VWAP: {r.get('VWAP', '-')}</span>"
        )

    fig.add_trace(go.Candlestick(
        x=df_k['日期'], open=df_k['開盤'], high=df_k['最高'], low=df_k['最低'], close=df_k['收盤'],
        name='K線', hoverinfo='none', increasing_line_color='#FF3333', decreasing_line_color='#00CC00'
    ), row=1, col=1)
    
    if '5MA' in df_k.columns: fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['5MA'], line=dict(color='#FFCC00', width=1.2), hoverinfo='none'), row=1, col=1)
    if '20MA' in df_k.columns: fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['20MA'], line=dict(color='#33CCFF', width=1.5), hoverinfo='none'), row=1, col=1)
    if 'VWAP' in df_k.columns: fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['VWAP'], line=dict(color='#FF00FF', width=1.8), hoverinfo='none'), row=1, col=1)

    if isinstance(nh_res, (int, float)):
        fig.add_hline(y=float(nh_res), line=dict(color="#FF8800", width=1.4, dash="dot"), annotation_text=f" 核心壓力(NH): {nh_res} ", row=1, col=1)
    if isinstance(broker_cost, (int, float)):
        fig.add_hline(y=float(broker_cost), line=dict(color="#00E5FF", width=1.2, dash="dash"), annotation_text=f" 主力均價: {broker_cost} ", row=1, col=1)

    vol_colors = ['#FF3333' if float(c) >= float(o) else '#00CC00' for c, o in zip(df_k['收盤'], df_k['開盤'])]
    fig.add_trace(go.Bar(x=df_k['日期'], y=df_k['成交量'], marker_color=vol_colors, hoverinfo='none'), row=2, col=1)
    if 'VOL_5MA' in df_k.columns: fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['VOL_5MA'], line=dict(color='#FFFF00', width=1), hoverinfo='none'), row=2, col=1)

    if '主力買賣超' in df_k.columns:
        b_colors = ['#FF3333' if int(v) >= 0 else '#00CC00' for v in df_k['主力買賣超']]
        fig.add_trace(go.Bar(x=df_k['日期'], y=df_k['主力買賣超'], marker_color=b_colors, hoverinfo='none'), row=3, col=1)

    if '大戶淨力道' in df_k.columns:
        f_colors = ['#FF3333' if int(v) >= 0 else '#00CC00' for v in df_k['大戶淨力道']]
        fig.add_trace(go.Bar(x=df_k['日期'], y=df_k['大戶淨力道'], marker_color=f_colors, hoverinfo='none'), row=4, col=1)

    fig.update_layout(
        template="plotly_dark", plot_bgcolor="#000000", paper_bgcolor="#000000",
        xaxis_rangeslider_visible=False, showlegend=False, height=720,
        margin=dict(l=35, r=35, t=10, b=15), hovermode="x"
    )
    fig.update_xaxes(type='category', gridcolor="#222222", showspikes=True, spikemode="across", spikethickness=1, spikedash="dash")
    fig.update_yaxes(gridcolor="#222222", side="right", showspikes=True, spikemode="across", spikethickness=1, spikedash="dash")

    plotly_html = fig.to_html(include_plotlyjs='cdn', full_html=False, config={'displayModeBar': False})
    lookup_json = json.dumps(kline_lookup_dict)

    custom_component = f"""
    <div style="background-color:#000; font-family: monospace; border:1px solid #333; padding:6px 10px; margin-bottom:4px;">
        <div style="text-align: center; color: #FFF; font-size: 15px; font-weight: bold; margin-bottom: 3px;">
            {stock_code} {stock_name} {fut_badge_html} 短空決策線圖 [{timeframe_label}]
        </div>
        <div id="dynamic-kline-header-bar" style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; font-size: 12px;">
            {default_info_html}
        </div>
    </div>
    <div id="plotly-container">{plotly_html}</div>
    <script>
    (function() {{
        var defHtml = `{default_info_html}`;
        var lData = {lookup_json};
        function attachHover() {{
            var plotEl = document.querySelector('.plotly-graph-div');
            var headEl = document.getElementById('dynamic-kline-header-bar');
            if (!plotEl || !headEl) {{ setTimeout(attachHover, 80); return; }}
            plotEl.on('plotly_hover', function(d) {{
                if (!d || !d.points || d.points.length === 0) return;
                var x = d.points[0].x;
                if (x && lData[x]) headEl.innerHTML = lData[x];
            }});
            plotEl.on('plotly_unhover', function() {{ headEl.innerHTML = defHtml; }});
        }}
        attachHover();
    }})();
    </script>
    """
    return custom_component

# ==============================================================================
# 6. 量化撮合與方案 A 階梯結算引擎 (2萬金盾與 T1 保底)
# ==============================================================================
def execute_quant_settlement(order, k_open, k_close, k_low, k_high, next_k_open, exit_k_close=None):
    trigger_p = float(order["trigger"])
    stop_p = float(order["stop"])
    t1_p = float(order["t1"])
    shares = order["shares"]
    
    if not (k_close < k_open and k_close < trigger_p):
        return {
            "status": "⚪ 未觸發 (空手防守)", "entry_price": None, "exit_price": None,
            "pnl_points": 0.0, "pnl_ntd": 0, "note": f"5分K未收黑破門檻 {trigger_p}，空手觀望。"
        }
    
    entry_p = min(k_close, next_k_open)
    
    if k_high >= stop_p:
        pts = entry_p - stop_p
        loss_ntd = int(pts * shares)
        effective_loss = max(loss_ntd, -MAX_STOP_LOSS_NTD)
        return {
            "status": "❌ 停損平倉 (2萬金盾風控鎖定)", "entry_price": entry_p, "exit_price": stop_p,
            "pnl_points": pts, "pnl_ntd": effective_loss, "note": f"盤中突破停損價 {stop_p}，依 2 萬金盾紀律立即停損出場。"
        }
    if k_low <= t1_p:
        pts = entry_p - t1_p
        return {
            "status": "🎯 方案 A 停利 (命中 T1)", "entry_price": entry_p, "exit_price": t1_p,
            "pnl_points": pts, "pnl_ntd": int(pts * shares), "note": f"盤中低點穿破 T1 ({t1_p})，依方案 A 全數平倉保底！"
        }
    if exit_k_close is not None:
        pts = entry_p - exit_k_close
        return {
            "status": "⏰ 尾盤強制平倉", "entry_price": entry_p, "exit_price": exit_k_close,
            "pnl_points": pts, "pnl_ntd": int(pts * shares), "note": f"未達 T1 且未停損，13:25 以市價 {exit_k_close} 強平。"
        }
    return {
        "status": "⏳ 部位持倉中", "entry_price": entry_p, "exit_price": None,
        "pnl_points": 0.0, "pnl_ntd": 0, "note": f"部位建立於不利滑價 {entry_p}，等待觸發 T1 或 13:25 結算。"
    }

# ==============================================================================
# 7. 融資大數據模組 (同步 10/02 官方數據庫)
# ==============================================================================
LOCAL_MARGIN_HISTORY_10D_S2 = {
    "6173": [
        {"date": "09/18", "buy": 1450, "sell": 1300, "change": 150, "balance": 11600},
        {"date": "09/21", "buy": 1200, "sell": 1400, "change": -200, "balance": 11400},
        {"date": "09/22", "buy": 1300, "sell": 1250, "change": 50, "balance": 11450},
        {"date": "09/23", "buy": 1680, "sell": 1420, "change": 260, "balance": 11710},
        {"date": "09/24", "buy": 1850, "sell": 1365, "change": 485, "balance": 12195},
        {"date": "09/29", "buy": 1720, "sell": 1191, "change": 529, "balance": 12724},
        {"date": "09/30", "buy": 1420, "sell": 3080, "change": -1660, "balance": 11064},
        {"date": "10/01", "buy": 1560, "sell": 2417, "change": -857, "balance": 10207},
        {"date": "10/02", "buy": 1240, "sell": 2340, "change": -1100, "balance": 9107}
    ],
    "2344": [
        {"date": "09/18", "buy": 2100, "sell": 2300, "change": -200, "balance": 35200},
        {"date": "09/21", "buy": 1800, "sell": 2100, "change": -300, "balance": 34900},
        {"date": "09/22", "buy": 1950, "sell": 1800, "change": 150, "balance": 35050},
        {"date": "09/23", "buy": 2200, "sell": 1900, "change": 300, "balance": 35350},
        {"date": "09/24", "buy": 2400, "sell": 2200, "change": 200, "balance": 35550},
        {"date": "09/29", "buy": 2100, "sell": 2719, "change": -619, "balance": 34931},
        {"date": "09/30", "buy": 2800, "sell": 2650, "change": 150, "balance": 35081},
        {"date": "10/01", "buy": 2100, "sell": 4601, "change": -2501, "balance": 32580},
        {"date": "10/02", "buy": 5890, "sell": 3412, "change": 2478, "balance": 35058}
    ],
    "8039": [
        {"date": "09/18", "buy": 1600, "sell": 1400, "change": 200, "balance": 19000},
        {"date": "09/21", "buy": 1300, "sell": 1500, "change": -200, "balance": 18800},
        {"date": "09/22", "buy": 1450, "sell": 1300, "change": 150, "balance": 18950},
        {"date": "09/23", "buy": 1500, "sell": 1400, "change": 100, "balance": 19050},
        {"date": "09/24", "buy": 1400, "sell": 1350, "change": 50, "balance": 19100},
        {"date": "09/29", "buy": 2200, "sell": 1415, "change": 785, "balance": 19885},
        {"date": "09/30", "buy": 3500, "sell": 1632, "change": 1868, "balance": 21753},
        {"date": "10/01", "buy": 2980, "sell": 2051, "change": 929, "balance": 22682},
        {"date": "10/02", "buy": 4650, "sell": 2430, "change": 2220, "balance": 24902}
    ]
}

@st.cache_data(ttl=300)
def fetch_stock_margin_10d(stock_code):
    code_str = str(stock_code).strip()
    fallback_data = LOCAL_MARGIN_HISTORY_10D_S2.get(code_str, [
        {"date": "09/22", "buy": 1100, "sell": 1250, "change": -150, "balance": 15100},
        {"date": "09/23", "buy": 1050, "sell": 1150, "change": -100, "balance": 15000},
        {"date": "09/24", "buy": 1250, "sell": 1100, "change": 150, "balance": 15150},
        {"date": "09/29", "buy": 1500, "sell": 1200, "change": 300, "balance": 15450},
        {"date": "09/30", "buy": 1200, "sell": 1300, "change": -100, "balance": 15350},
        {"date": "10/01", "buy": 1300, "sell": 1350, "change": -50, "balance": 15300},
        {"date": "10/02", "buy": 1450, "sell": 1350, "change": 100, "balance": 15400}
    ])
    return pd.DataFrame(fallback_data)

# ==============================================================================
# 8. 母池數據加載 (S2-R1 短空評分)
# ==============================================================================
def load_radar_market_data(pool_list):
    enhanced = []
    for item in pool_list:
        code = item.get("代號")
        name = item.get("名稱", STOCK_NAME_DICT.get(code, f"個股_{code}"))
        close_p = float(item.get("昨收", 100.0))
        high_p = float(item.get("最高價", close_p))
        low_p = float(item.get("最低價", close_p * 0.96))
        prev_close = round(close_p * 0.99, 2)
        margin_change = item.get("融資增減(張)", 0)
        put_val = item.get("權證認售(萬)", 0)
        call_val = item.get("權證認購(萬)", 0)
        tot_vol = int(item.get("昨日鎖碼量", 10000))

        limit_up = round(prev_close * 1.10, 2)
        cdp = round((high_p + low_p + 2.0 * close_p) / 4.0, 2)
        nh_res = round(min(2.0 * cdp - low_p, limit_up), 2)
        ah_res = round(min(cdp + (high_p - low_p), limit_up), 2)

        raw_brokers = item.get("主力分點", [])
        detailed_brokers = []
        tot_buy_shares = 0
        tot_cost_amount = 0.0
        tot_ratio = 0.0

        for b in raw_brokers:
            b_name = b.get("分點")
            b_vol = int(b.get("買超", 0))
            b_cost = float(b.get("均價", close_p))
            b_ratio = float(b.get("佔比", round((abs(b_vol) / max(tot_vol, 1)) * 100, 2)))
            
            p_rate = round(((close_p - b_cost) / b_cost) * 100, 2) if b_cost > 0 else 0.0
            profit_wan = int(round(((close_p - b_cost) * b_vol * 1000) / 10000)) if b_cost > 0 else 0
            
            if b_vol > 0:
                tot_buy_shares += b_vol
                tot_cost_amount += b_cost * b_vol * 1000
                tot_ratio += b_ratio

            detailed_brokers.append({
                "分點名稱": b_name, "買超張數": b_vol, "佔比(%)": b_ratio,
                "收盤價": close_p, "預估成本": b_cost, "預估獲利(萬)": profit_wan,
                "報酬率(%)": p_rate, "倒貨意願": "🔴 極高" if (p_rate >= 1.0 and b_vol > 0) else ("🟡 普通" if b_vol > 0 else ("🟢 停損摜壓" if p_rate < 0 else "🟢 波段出貨"))
            })

        avg_cost = round(tot_cost_amount / (tot_buy_shares * 1000), 2) if tot_buy_shares > 0 else close_p
        
        # S2-R1 專用短空評分
        score_dict = {
            "6173": 99, "2344": 98, "8039": 95, "3042": 92, "2455": 89, 
            "2313": 85, "2327": 60, "3406": 55, "2408": 50, "3189": 40, "3037": 10, "2492": 5
        }
        score = score_dict.get(code, 50)
        alert_tag = "⚡ 待機狙擊" if score >= 88 else ("⚡ 次選觀察" if score >= 60 else "🛑 官方禁空")
        alert_desc = f"【{alert_tag}】10/02 融資: {margin_change:+d} 張，認售: {put_val:+d} 萬"
        
        enhanced.append({
            "股票代號": code, "股票名稱": name, "個期": "期" if code in STOCK_FUTURES_SET else "—",
            "現價": close_p, "昨收": prev_close, "漲跌": round(close_p - prev_close, 2),
            "漲跌幅(%)": round(((close_p - prev_close) / prev_close) * 100, 2),
            "近高壓力(NH)": nh_res, "最高壓力(AH)": ah_res, "主力加權成本": avg_cost,
            "主力合計買超": tot_buy_shares, "主力合計佔比(%)": round(tot_ratio, 2),
            "融資增減(張)": margin_change, "權證認售(萬)": put_val, "權證認購(萬)": call_val,
            "短空勝率分": score, "即時信號": alert_tag, "盤中警報": alert_desc,
            "各分點清單": detailed_brokers, "5日均量(張)": tot_vol
        })
    return pd.DataFrame(enhanced).sort_values(by="短空勝率分", ascending=False).reset_index(drop=True)

df_display = load_radar_market_data(DEFAULT_WATCHLIST_S2R1)
df_display.index = range(1, len(df_display) + 1)

# ==============================================================================
# 9. 側邊欄控制台
# ==============================================================================
st.sidebar.title("⚔️ S2 控制台 (開幕戰)")
st.sidebar.markdown(f"**決戰輪次**：`Season 2 Round 1` ({S2_R1_DATE})")
st.sidebar.markdown(f"**母池籌碼基準**：`{DATA_BASE_DATE}` 三維完整大數據")

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 第二季起跑淨值儀表板")
st.sidebar.markdown(f"""
<div class="metric-card-gemini">
    <div style="font-size: 13px; color: #BBB;">🟥 Gemini 起始淨值 (首季總冠軍)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_GEMINI:,}</div>
    <div style="font-size: 12px; color: #FFD700;">第 2 季平手重新起跑</div>
</div>
<div class="metric-card-gpt">
    <div style="font-size: 13px; color: #BBB;">🟦 ChatGPT 起始淨值 (首季亞軍)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CHATGPT:,}</div>
    <div style="font-size: 12px; color: #FFD700;">第 2 季平手重新起跑</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.info(f"🚩 **起跑差距**：NT$ 0 (完全平手)\n\n**單檔部位上限 (20%)**：\n• 雙方各 NT$ {LIMIT_GEMINI:,}\n\n🛡️ **風控硬公約**：\n單筆最大停損 **≤ NT$ 20,000** ｜ **命中 T1 全平保底**")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📜 官方執法核心規範 (S2 實戰版)")
st.sidebar.caption(
    """
    1. **實體破線確認**：5分K收盤 < 開盤 且 收盤 < 進場價。
    2. **不利滑價撮合**：成交價 = min(觸發K收, 次K開)。
    3. **2萬金盾鎖定**：單筆停損上限嚴守 NT$ 20,000。
    4. **方案 A 優先**：穿破 T1 即刻 100% 全數平倉保底。
    5. **尾盤強平**：未達 T1 且未停損者，13:25～13:30 強平。
    """
)

# ==============================================================================
# 10. 主頁面七大核心分頁 (完全恢復操盤工作台)
# ==============================================================================
st.title("⚔️ 雙 AI 量化短空競賽｜第二場（Season 2）Round 1 旗艦戰情室")
st.caption(f"數據庫基準：{DATA_BASE_DATE} 臺灣證券交易所官方融資券/主力分點/自營商權證金流三維大數據")

tab_workspace, tab_orders, tab_matcher, tab_radar, tab_s1_hall, tab_margin, tab_broker = st.tabs([
    "🖥️ 專業操盤工作台 (K線與分點)",
    "⚔️ S2-R1 官方決戰封單名冊", 
    "🧮 官方撮合與方案A結算模擬器",
    "📊 12檔母池籌碼雷達全景表",
    "👑 Season 1 榮譽總冠軍名人堂",
    "📈 融資增減 (10/02 官方增減排行)",
    "🏢 主力分點 (10/02 真實買賣超)"
])

# ------------------------------------------------------------------------------
# TAB 1: 專業操盤工作台 (即時 5 分 K 線核心繪圖引擎)
# ------------------------------------------------------------------------------
with tab_workspace:
    left_side, right_side = st.columns([1.35, 3.65], gap="medium")
    
    with left_side:
        st.markdown("### 📋 短空鎖碼清單")
        st.caption("💡 嚴格等寬對齊，可使用 **↑ / ↓ 鍵** 快速切換標的")
        
        stock_list_options = []
        for rank, (_, r) in enumerate(df_display.iterrows(), 1):
            c_sym = "+" if float(r.get('漲跌', 0)) > 0 else ""
            badge = "👑" if rank == 1 else ("⭐" if rank <= 3 else "🎯")
            chg_color = "red" if float(r.get('漲跌', 0)) >= 0 else "green"
            
            score_padded = f"[{r['短空勝率分']:>2}分]"
            code_padded = f"{r['股票代號']:<4} "
            name_padded = pad_display_text(r['股票名稱'], 8)
            fut_symbol = "[期]" if str(r['股票代號']) in STOCK_FUTURES_SET else "    "
            price_padded = f"{float(r['現價']):>6.1f}"
            pct_padded = f"{c_sym}{float(r.get('漲跌幅(%)', 0)):>5.2f}%"
            paren_text = f":{chg_color}[({price_padded}|{pct_padded})]"
            
            stock_list_options.append(f"{badge} {score_padded} {code_padded} {name_padded} {fut_symbol} {paren_text}")

        if "selected_stock_code" not in st.session_state or str(st.session_state["selected_stock_code"]) not in [str(x) for x in df_display["股票代號"].values]:
            st.session_state["selected_stock_code"] = str(df_display.iloc[0]["股票代號"])

        current_code = str(st.session_state["selected_stock_code"])
        current_idx = next((i for i, opt in enumerate(stock_list_options) if f" {current_code} " in opt), 0)

        selected_option = st.radio(
            "選擇股票：", options=stock_list_options, index=current_idx,
            label_visibility="collapsed", key="workspace_radio_selector"
        )
        target_code = selected_option.split("] ")[1].split(" ")[0]
        st.session_state["selected_stock_code"] = target_code
        target_row = df_display[df_display["股票代號"] == target_code].iloc[0]

        st.markdown(f"""
        <div style="background-color: #1E1E1E; border: 1px solid #333; border-radius: 8px; padding: 14px; margin-top: 10px; font-family: monospace;">
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding-bottom: 6px; margin-bottom: 8px;">
                <span style="font-size: 15px; font-weight: bold; color: #FFF;">📌 {target_row['股票名稱']} ({target_code})</span>
                <span style="background-color: #D32F2F; color: #FFF; font-size: 12px; font-weight: bold; padding: 2px 6px; border-radius: 4px;">勝率 {target_row['短空勝率分']}分</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px;">
                <span style="color: #AAA;">收盤價：</span><span style="font-weight: bold; color: #FFF;">{target_row['現價']} 元</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px;">
                <span style="color: #AAA;">主力均價：</span><span style="font-weight: bold; color: #00E5FF;">{target_row['主力加權成本']} 元</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px;">
                <span style="color: #FF8800; font-weight: bold;">核心壓力(NH)：</span><span style="font-weight: bold; color: #FF8800;">{target_row['近高壓力(NH)']} 元</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px;">
                <span style="color: #AAA;">10/02 官方融資：</span><span style="font-weight: bold; color: {'#FF4444' if target_row['融資增減(張)']>=0 else '#00FF66'};">{target_row['融資增減(張)']:+,} 張</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px;">
                <span style="color: #AAA;">認售權證買超：</span><span style="font-weight: bold; color: {'#FF4444' if target_row['權證認售(萬)']>0 else '#FFF'};">{target_row['權證認售(萬)']:+,} 萬元</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with right_side:
        target_name = target_row["股票名稱"]
        c_tf1, c_tf2 = st.columns([1, 1])
        with c_tf1:
            timeframe_options = {"5分K (主力關鍵)": "5m", "1分K": "1m", "30分K": "30m", "日線": "1d"}
            selected_tf_label = st.selectbox("週期切換：", list(timeframe_options.keys()), index=0)
            selected_interval = timeframe_options[selected_tf_label]
        with c_tf2:
            k_count = st.number_input("K 棒根數：", min_value=10, max_value=300, value=60, step=10)

        stock_k_df = fetch_real_kline(target_code, interval=selected_interval)
        if stock_k_df is not None and not stock_k_df.empty:
            chart_html = render_interactive_kline_chart(
                stock_k_df.tail(int(k_count)).reset_index(drop=True),
                target_code, target_name, target_row["主力加權成本"], target_row["近高壓力(NH)"],
                round(target_row["昨收"] * 1.1, 2), selected_tf_label
            )
            components.html(chart_html, height=790, scrolling=False)
        else:
            st.warning("暫無該標的即時線圖資料。")

        st.markdown(f"#### 🏢 【{target_name}】主力分點鎖碼持倉明細 (10/02)")
        b_list = target_row.get("各分點清單", [])
        if b_list:
            df_b = pd.DataFrame(b_list)
            df_b.index = range(1, len(df_b) + 1)
            st.dataframe(df_b, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: S2-R1 雙方正式決戰封單名冊
# ------------------------------------------------------------------------------
with tab_orders:
    st.subheader("⚔️ S2-R1 雙 AI 官方 TOP 5 決戰名冊陣列 (第二場開幕戰)")
    st.caption("公證核定：雙方本金重置為各 NT$ 1,000,000；單筆最大停損 ≤ NT$ 20,000；命中 T1 方案 A 立即全平保底。")
    col_g, col_c = st.columns(2)
    
    with col_g:
        st.markdown("#### 🟥 Gemini 戰情室 S2-R1 官方封單")
        st.caption(f"起始本金：NT$ {CAPITAL_GEMINI:,}｜單檔上限：NT$ {LIMIT_GEMINI:,}｜單筆停損 ≤ NT$ 20,000")
        
        df_gem_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "口數": x['size'], "最大風險": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_GEMINI_S2R1
        ])
        st.dataframe(df_gem_ui, use_container_width=True, hide_index=True)
        
        with st.expander("🔍 查看 Gemini S2-R1 籌碼依據與量化細節", expanded=True):
            for x in ORDERS_GEMINI_S2R1:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1保利 `{x['t1']:.1f}`**")
                st.caption(f"└ 核心籌碼：{x['reason']}")
                
    with col_c:
        st.markdown("#### 🟦 ChatGPT 戰情室 S2-R1 官方封單 (核定封存版)")
        st.caption(f"起始本金：NT$ {CAPITAL_CHATGPT:,}｜單檔上限：NT$ {LIMIT_CHATGPT:,}｜單筆停損 ≤ NT$ 20,000")
        
        df_gpt_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "口數": x['size'], "最大風險": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_CHATGPT_S2R1
        ])
        st.dataframe(df_gpt_ui, use_container_width=True, hide_index=True)
        
        with st.expander("🔍 查看 ChatGPT S2-R1 策略邏輯與不空名單", expanded=True):
            for x in ORDERS_CHATGPT_S2R1:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1保利 `{x['t1']:.1f}`**")
                st.caption(f"└ 作戰定位：{x['reason']}")
            st.markdown("---")
            st.caption("🚫 **GPT R1 不空名單**：2492華新科、3189景碩、3037欣興、6173信昌電、2408南亞科、3406玉晶光")

    st.markdown("---")
    st.subheader("🛑 S2-R1 官方絕對禁空名單（NO SHORT LIST）")
    cn1, cn2, cn3 = st.columns(3)
    cn1.error("🚫 **2327 國巨\* (626.0元)**\n\n10萬張天量換手，認購爆買+2,981萬(全市場第2)，多頭軋空未止，嚴禁摸頭！")
    cn2.error("🚫 **2492 華新科 (361.5元)**\n\n強攻漲停，高盛/凱基台北狂買6,800張鎖碼，融資被軋退-1,196張，絕對禁空！")
    cn3.error("🚫 **3037 欣興 (1305.0元)**\n\n美林與高盛合力掃盤逾4,000張，大漲7.4%多頭排列，絕對禁空！")

# ------------------------------------------------------------------------------
# TAB 3: 官方撮合與方案 A 結算模擬器
# ------------------------------------------------------------------------------
with tab_matcher:
    st.subheader("🧮 裁判室專用：5分K實體跌破撮合與方案 A 結算模擬器")
    st.caption("依據官方公約：取不利撮合價進場，盤中穿破 T1 即刻鎖利全平，未達條件者於 13:25 強制結算。")
    
    sim_c1, sim_c2 = st.columns(2)
    with sim_c1:
        st.markdown("**步驟 1：選擇審查陣營與封單**")
        selected_side = st.radio("參賽陣營：", ["🟥 Gemini 戰情室", "🟦 ChatGPT 戰情室"], horizontal=True)
        order_set = ORDERS_GEMINI_S2R1 if "Gemini" in selected_side else ORDERS_CHATGPT_S2R1
        
        target_order = st.selectbox(
            "選擇審查封單：", order_set,
            format_func=lambda x: f"{x['rank']} {x['name']} (門檻 < {x['trigger']:.1f}, 停損: {x['stop']:.1f}, T1保利: {x['t1']:.1f})"
        )
        
        st.markdown("**步驟 2：輸入盤面 5 分 K 實體與走勢價位**")
        k_open_in = st.number_input("觸發 5 分 K 開盤價：", value=float(target_order["trigger"]) + 1.0, step=0.5)
        k_close_in = st.number_input("觸發 5 分 K 收盤價：", value=float(target_order["trigger"]) - 0.5, step=0.5)
        next_open_in = st.number_input("次一根 5 分 K 開盤價：", value=float(target_order["trigger"]) - 1.0, step=0.5)
        k_high_in = st.number_input("盤中最高價 (檢驗停損)：", value=float(target_order["stop"]) - 1.0, step=0.5)
        k_low_in = st.number_input("盤中最低價 (檢驗方案 A T1)：", value=float(target_order["t1"]) - 1.0, step=0.5)
        exit_close_in = st.number_input("13:25 尾盤強制平倉價 (備用)：", value=float(target_order["trigger"]) - 2.0, step=0.5)
        
    with sim_c2:
        st.markdown("**步驟 3：官方仲裁自動計算結果**")
        res = execute_quant_settlement(
            order=target_order,
            k_open=k_open_in, k_close=k_close_in, k_low=k_low_in, k_high=k_high_in,
            next_k_open=next_open_in, exit_k_close=exit_close_in
        )
        
        st.info(f"**判定狀態**：{res['status']}")
        if res["entry_price"] is not None:
            st.write(f"- **不利滑價撮合價**：`{res['entry_price']:.2f}` (取觸發K收盤 {k_close_in} 與次K開盤 {next_open_in} 較劣者)")
            if res["exit_price"] is not None:
                st.write(f"- **平倉結算價**：`{res['exit_price']:.2f}`")
                st.write(f"- **單股價差點數**：`{res['pnl_points']:+.2f} 點`")
                if res['pnl_ntd'] > 0:
                    st.success(f"💰 **核定結算總損益**：`+NT$ {res['pnl_ntd']:,}`")
                else:
                    st.error(f"📉 **核定結算總損益**：`-NT$ {abs(res['pnl_ntd']):,}` (嚴格鎖定在 2 萬金盾內)")
        st.caption(f"**仲裁備註**：{res['note']}")

# ------------------------------------------------------------------------------
# TAB 4: 12檔母池籌碼雷達全景表
# ------------------------------------------------------------------------------
with tab_radar:
    st.subheader(f"📋 12 檔母池三維大數據全景表 ({DATA_BASE_DATE} 官方融資與權證校正版)")
    preferred_cols = [
        "短空勝率分", "股票代號", "股票名稱", "個期", "現價", "即時信號",
        "融資增減(張)", "權證認售(萬)", "權證認購(萬)", "近高壓力(NH)", "主力加權成本", "主力合計買超", "主力合計佔比(%)"
    ]
    st.dataframe(df_display[[c for c in preferred_cols if c in df_display.columns]], use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 5: 首季名人堂
# ------------------------------------------------------------------------------
with tab_s1_hall:
    st.subheader("👑 第一場 (Season 1) 總冠軍名人堂檔案庫 (公證永久封存)")
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("首季總冠軍", "🟥 Gemini 戰情室", "11勝 6負 3平")
    c_m2.metric("首季終局淨值", "NT$ 1,743,595", "+74.36%")
    c_m3.metric("首季總獲利差距", "NT$ 331,914 領先", "亞軍 GPT: $1,411,681")
    st.caption("第一季 20 回合各輪對決詳細紀錄已完整歸檔，第二場賽事自 2026/10/05 開賽，雙方 100 萬重新起跑！")

# ------------------------------------------------------------------------------
# TAB 6: 📈 融資增減 (10/02 官方排行榜)
# ------------------------------------------------------------------------------
with tab_margin:
    st.subheader(f"📊 12 檔母池 {MARGIN_DISPLAY_DATE} 官方融資增減熱力排行榜 (按增減張數降序)")
    st.caption("資料來源：臺灣證券交易所官方核定。🔴 紅色代表融資增加（散戶接刀/追高慘套），🟢 綠色代表融資減少（斷頭停損/外資洗盤）。")

    summary_margin_list = []
    for item in DEFAULT_WATCHLIST_S2R1:
        c_code = item["代號"]
        c_name = item["名稱"]
        c_price = item["昨收"]
        df_10d = fetch_stock_margin_10d(c_code)
        
        last_chg = item.get("融資增減(張)", 0)
        last_bal = int(df_10d.iloc[-1]["balance"]) if not df_10d.empty else 10000
        cum_10d_chg = int(df_10d["change"].sum()) if not df_10d.empty else last_chg
        
        if last_chg > 1000:
            status_desc = "🔴 融資暴增 (散戶高檔接刀慘套 / 妖股鎖碼)"
        elif last_chg > 400:
            status_desc = "🟠 融資堆積 (浮額沉重，面臨踩踏)"
        elif last_chg > 0:
            status_desc = "🟡 融資微增 (籌碼趨向渙散)"
        elif last_chg < -1000:
            status_desc = "🟢 融資崩逃 (散戶斷頭大出逃 / 籌碼沉澱)"
        else:
            status_desc = "⚪ 融資微減 (散戶離場觀望)"

        summary_margin_list.append({
            "代號": c_code,
            "股票名稱": c_name,
            "收盤價": c_price,
            f"{MARGIN_DISPLAY_DATE}融資增減(張)": last_chg,
            "最新融資餘額(張)": last_bal,
            "近10日累計增減(張)": cum_10d_chg,
            "籌碼浮額狀態判定": status_desc
        })

    margin_col_name = f"{MARGIN_DISPLAY_DATE}融資增減(張)"
    df_all_m = pd.DataFrame(summary_margin_list).sort_values(by=margin_col_name, ascending=False).reset_index(drop=True)
    df_all_m.index = range(1, len(df_all_m) + 1)

    def style_margin_changes(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return "color: #FF4444; font-weight: bold;"
            elif val < 0:
                return "color: #00CC00; font-weight: bold;"
        return ""

    def apply_color_styler(styler, func, subset):
        if hasattr(styler, "map"):
            return styler.map(func, subset=subset)
        return styler.applymap(func, subset=subset)

    styled_df_all_m = apply_color_styler(df_all_m.style, style_margin_changes, subset=[margin_col_name, "近10日累計增減(張)"]).format({
        "收盤價": "{:.1f}",
        margin_col_name: "{:+,d}",
        "最新融資餘額(張)": "{:,d}",
        "近10日累計增減(張)": "{:+,d}"
    })
    
    st.dataframe(styled_df_all_m, use_container_width=True, height=490)

    st.markdown("---")
    st.subheader("⚡ 母池個股快速切換 (一鍵單擊快速檢視 10 日走勢)")
    pills_options = [f"{r['代號']} {r['股票名稱']} ({r[margin_col_name]:+,d})" for _, r in df_all_m.iterrows()]
    
    if "selected_margin_ticker" not in st.session_state:
        st.session_state["selected_margin_ticker"] = df_all_m.iloc[0]["代號"]

    default_pill_idx = 0
    for idx, opt in enumerate(pills_options):
        if opt.startswith(str(st.session_state["selected_margin_ticker"])):
            default_pill_idx = idx
            break

    sel_radio = st.radio(
        "選擇個股：",
        options=pills_options,
        index=default_pill_idx,
        horizontal=True,
        key="margin_horizontal_selector",
        label_visibility="collapsed"
    )
    cur_margin_code = sel_radio.split(" ")[0]
    st.session_state["selected_margin_ticker"] = cur_margin_code
    cur_stock_name = STOCK_NAME_DICT.get(cur_margin_code, cur_margin_code)
    
    df_margin_single = fetch_stock_margin_10d(cur_margin_code)
    m_col1, m_col2 = st.columns([2.5, 1.5])
    
    with m_col1:
        st.markdown(f"#### 📈 【{cur_margin_code} {cur_stock_name}】近 10 日融資餘額與單日增減走勢")
        fig_margin = make_subplots(specs=[[{"secondary_y": True}]])
        bar_colors = ['#FF4444' if c >= 0 else '#00CC00' for c in df_margin_single["change"]]
        
        fig_margin.add_trace(
            go.Bar(
                x=df_margin_single["date"], 
                y=df_margin_single["change"],
                name="單日融資增減(張)",
                marker_color=bar_colors,
                opacity=0.75
            ),
            secondary_y=False
        )
        
        fig_margin.add_trace(
            go.Scatter(
                x=df_margin_single["date"], 
                y=df_margin_single["balance"],
                name="融資餘額(張)",
                line=dict(color="#FFD700", width=3),
                mode="lines+markers"
            ),
            secondary_y=True
        )
        
        fig_margin.update_layout(
            template="plotly_dark", plot_bgcolor="#111", paper_bgcolor="#111",
            height=380, margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )
        fig_margin.update_yaxes(title_text="單日增減 (張)", secondary_y=False, gridcolor="#222")
        fig_margin.update_yaxes(title_text="融資餘額 (張)", secondary_y=True, gridcolor="#222")
        fig_margin.update_xaxes(gridcolor="#222")
        st.plotly_chart(fig_margin, use_container_width=True)

    with m_col2:
        st.markdown(f"#### 📋 逐日融資增減明細 (最新日期置頂)")
        df_margin_display = df_margin_single.iloc[::-1].copy().reset_index(drop=True)
        df_margin_display.columns = ["日期", "融資買進", "融資賣出", "單日增減(張)", "融資餘額(張)"]
        df_margin_display.index = range(1, len(df_margin_display) + 1)
        
        styled_single = apply_color_styler(df_margin_display.style, style_margin_changes, subset=["單日增減(張)"]).format({
            "融資買進": "{:,d}",
            "融資賣出": "{:,d}",
            "單日增減(張)": "{:+,d}",
            "融資餘額(張)": "{:,d}"
        })
        st.dataframe(styled_single, use_container_width=True, height=360)

# ------------------------------------------------------------------------------
# TAB 7: 🏢 主力分點 (10/02 盤後真實買賣超各前五大)
# ------------------------------------------------------------------------------
with tab_broker:
    st.subheader(f"🏢 12 檔母池主力關鍵分點分析 ({DATA_BASE_DATE} 盤後真實撮合)")
    st.caption("完整收錄 12 檔標的之買超前五大與賣超前五大主力券商名冊。")

    broker_pill_options = [f"{r['股票代號']} {r['股票名稱']}" for _, r in df_display.iterrows()]
    if "selected_broker_ticker" not in st.session_state:
        st.session_state["selected_broker_ticker"] = str(df_display.iloc[0]["股票代號"])

    default_b_idx = 0
    for idx, opt in enumerate(broker_pill_options):
        if opt.startswith(str(st.session_state["selected_broker_ticker"])):
            default_b_idx = idx
            break

    sel_broker_radio = st.radio(
        "選擇標的：", options=broker_pill_options, index=default_b_idx,
        horizontal=True, key="broker_horizontal_selector", label_visibility="collapsed"
    )
    cur_b_code = sel_broker_radio.split(" ")[0]
    st.session_state["selected_broker_ticker"] = cur_b_code
    cur_b_row = df_display[df_display["股票代號"] == cur_b_code].iloc[0]

    bc_top1, bc_top2, bc_top3, bc_top4 = st.columns(4)
    bc_top1.metric("標的與收盤價", f"{cur_b_row['股票名稱']} ({cur_b_code})", f"{cur_b_row['現價']} 元")
    bc_top2.metric("主力加權均價", f"{cur_b_row['主力加權成本']} 元")
    bc_top3.metric("主力合計買超", f"{cur_b_row['主力合計買超']:,} 張", f"佔比 {cur_b_row['主力合計佔比(%)']}%")
    bc_top4.metric("核心防守壓力 (NH)", f"{cur_b_row['近高壓力(NH)']} 元")

    st.markdown("---")
    b_detail_list = cur_b_row.get("各分點清單", [])
    if b_detail_list:
        df_all_raw_b = pd.DataFrame(b_detail_list)
        df_buy_list = df_all_raw_b[df_all_raw_b["買超張數"] > 0].sort_values(by="買超張數", ascending=False).head(5).copy().reset_index(drop=True)
        df_sell_list = df_all_raw_b[df_all_raw_b["買超張數"] < 0].sort_values(by="買超張數", ascending=True).head(5).copy().reset_index(drop=True)
        
        st.markdown(f"#### 🔴 【{cur_b_row['股票名稱']}】買超前五大主力分點")
        if not df_buy_list.empty:
            df_buy_list.index = range(1, len(df_buy_list) + 1)
            st.dataframe(df_buy_list, use_container_width=True)
        st.markdown(f"#### 🟢 【{cur_b_row['股票名稱']}】賣超前五大主力分點")
        if not df_sell_list.empty:
            df_sell_list.index = range(1, len(df_sell_list) + 1)
            st.dataframe(df_sell_list, use_container_width=True)

# ==============================================================================
# 11. 系統頁尾
# ==============================================================================
st.markdown("---")
st.caption(f"雙 AI 量化短空雷達系統 v21.1 (S2-R1 開幕戰完整版)｜{S2_R1_DATE} 週一開盤生效｜執法公約：5分K實體跌破 + 不利撮合滑價 + 2萬金盾停損硬上限 + 方案A鎖利 + 13:25強平")
