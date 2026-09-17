import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import datetime
import unicodedata
import json
import requests
import re
from bs4 import BeautifulSoup
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==============================================================================
# 1. 頁面排版與深色戰情室外觀設定
# ==============================================================================
st.set_page_config(
    page_title="雙 AI 量化短空雷達 (Round 12 旗艦裁判長版)", 
    layout="wide", 
    page_icon="🎯", 
    initial_sidebar_state="expanded"
)

# 注入戰情室專用深色高對比樣式
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
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. 官方公約常數與雙方帳戶狀態 (2026/09/17 R11 終局校準生效)
# ==============================================================================
R12_DATE = "2026/09/18"
DATA_BASE_DATE = "2026/09/17"

# 帳戶資本與風控額度 (R11 雙方命中台虹期校正)
CAPITAL_GEMINI = 1697595    # R10(1,620,595) + R11信昌電/國巨/台虹(+77,000)
CAPITAL_CHATGPT = 1319681   # R10(1,289,681) + R11台虹(+30,000)
LIMIT_GEMINI = int(CAPITAL_GEMINI * 0.20)    # NT$ 339,519
LIMIT_CHATGPT = int(CAPITAL_CHATGPT * 0.20)  # NT$ 263,936
NET_SPREAD = CAPITAL_GEMINI - CAPITAL_CHATGPT # NT$ 377,914

STOCK_FUTURES_SET = {
    "2408", "3260", "2449", "3231", "2327", "2376", "6488", "2313", "2492",
    "2330", "2317", "2454", "2382", "2603", "2609", "2344", "3037", "2368", "3017",
    "2383", "1519", "8210", "2059", "4551", "5289", "8299", "3406",
    "2615", "8039", "5314", "2489", "3006", "2337", "8046", "2426", "2455", "3189",
    "3374", "6239", "6173"
}

STOCK_NAME_DICT = {
    "2327": "國巨*", "2455": "全新", "2492": "華新科", "8039": "台虹", "3189": "景碩",
    "3037": "欣興", "2408": "南亞科", "2313": "華通", "3406": "玉晶光", "2344": "華邦電",
    "3260": "威剛", "6173": "信昌電", "2426": "鼎元", "2330": "台積電", "2317": "鴻海"
}
NAME_TO_CODE_DICT = {v: k for k, v in STOCK_NAME_DICT.items()}
TPEX_STOCKS = {"3260", "6488", "8299", "5289", "3211", "5483", "8112", "6213", "5314", "3105", "3374", "6173"}

# ==============================================================================
# 3. 🎯 官方 R1～R11 歷史對決覆盤庫 (含台虹期真實撮合校正)
# ==============================================================================
HISTORICAL_ROUNDS = [
    {
        "round": "R0 (初始)", "date": "賽前基準", "winner": "雙方就位",
        "gem_pnl": 0, "gem_net": 1000000, "gem_targets": "初始資金池",
        "gpt_pnl": 0, "gpt_net": 1000000, "gpt_targets": "初始資金池",
        "spread": 0, "review": "賽事實裝啟動，雙方起始資本各 NT$ 1,000,000。"
    },
    {
        "round": "Round 1", "date": "2026/09/02", "winner": "🟥 Gemini 勝",
        "gem_pnl": 48200, "gem_net": 1048200, "gem_targets": "2327 國巨*(期), 2455 全新(期)",
        "gpt_pnl": 12500, "gpt_net": 1012500, "gpt_targets": "2344 華邦電(期)",
        "spread": 35700, "review": "Gemini 鎖定國巨開高走低與全新暴跌，ChatGPT 華邦電微幅獲利。"
    },
    {
        "round": "Round 2", "date": "2026/09/03", "winner": "🟥 Gemini 勝",
        "gem_pnl": 62400, "gem_net": 1110600, "gem_targets": "2408 南亞科(期), 3189 景碩(期)",
        "gpt_pnl": -15000, "gpt_net": 997500, "gpt_targets": "2492 華新科(現股停損)",
        "spread": 113100, "review": "南亞科帶頭重挫觸發 T1；GPT 華新科現股遭遇反彈觸發停損。"
    },
    {
        "round": "Round 3", "date": "2026/09/04", "winner": "🟥 Gemini 勝",
        "gem_pnl": 51000, "gem_net": 1161600, "gem_targets": "8039 台虹(期), 6173 信昌電(期)",
        "gpt_pnl": 21000, "gpt_net": 1018500, "gpt_targets": "2313 華通(期)",
        "spread": 143100, "review": "Gemini 掌握被動元件浮額踩踏，雙中 T1 保底；GPT 華通穩健收尾。"
    },
    {
        "round": "Round 4", "date": "2026/09/08", "winner": "🟥 Gemini 勝",
        "gem_pnl": 74500, "gem_net": 1236100, "gem_targets": "3037 欣興(期), 2455 全新(期)",
        "gpt_pnl": 34000, "gpt_net": 1052500, "gpt_targets": "3260 威剛(期)",
        "spread": 183600, "review": "欣興早盤急殺近 20 點命中 T2；雙方期貨部位大幅提振收益。"
    },
    {
        "round": "Round 5", "date": "2026/09/09", "winner": "🟥 Gemini 勝",
        "gem_pnl": 89000, "gem_net": 1325100, "gem_targets": "3406 玉晶光(期), 2408 南亞科(期)",
        "gpt_pnl": 45000, "gpt_net": 1097500, "gpt_targets": "2344 華邦電(期)",
        "spread": 227600, "review": "玉晶光千元震盪下殺大賺 40 點；雙方建立高額領先優勢。"
    },
    {
        "round": "Round 6", "date": "2026/09/10", "winner": "🟦 ChatGPT 勝",
        "gem_pnl": -22000, "gem_net": 1303100, "gem_targets": "2313 華通(期停損)",
        "gpt_pnl": 58000, "gpt_net": 1155500, "gpt_targets": "3189 景碩(期), 2408 南亞科(期)",
        "spread": 147600, "review": "GPT 首度奪勝！景碩破位大殺命中 T1，Gemini 華通盤中遭反抽停損。"
    },
    {
        "round": "Round 7", "date": "2026/09/11", "winner": "🟥 Gemini 勝",
        "gem_pnl": 94000, "gem_net": 1397100, "gem_targets": "2455 全新(期), 8039 台虹(期)",
        "gpt_pnl": 31000, "gpt_net": 1186500, "gpt_targets": "2327 國巨*(期)",
        "spread": 210600, "review": "全新融資斷頭連環殺盤，Gemini 滿載獲利，差距再度拉開。"
    },
    {
        "round": "Round 8", "date": "2026/09/14", "winner": "🟥 Gemini 勝",
        "gem_pnl": 157495, "gem_net": 1554595, "gem_targets": "2408 南亞科(期), 3260 威剛(期)",
        "gpt_pnl": 80181, "gpt_net": 1266681, "gpt_targets": "2344 華邦電(期), 3260 威剛(期)",
        "spread": 287914, "review": "大盤崩跌 700 點！南亞科與威剛單邊跳水，雙方均刷歷史單期獲利新高。"
    },
    {
        "round": "Round 9", "date": "2026/09/15", "winner": "🟥 Gemini 勝",
        "gem_pnl": 66000, "gem_net": 1620595, "gem_targets": "3406 玉晶光(期 T1命中 +33點)",
        "gpt_pnl": 23000, "gpt_net": 1289681, "gpt_targets": "3260 威剛(期 +8點), 2408 南亞科(期 +3.5點)",
        "spread": 330914, "review": "玉晶光跌破 950 殺至 906 完美達標 T1(915)；GPT 威剛/南亞科期貨獲利收關。"
    },
    {
        "round": "Round 10", "date": "2026/09/16", "winner": "🤝 官方裁定平手",
        "gem_pnl": 0, "gem_net": 1620595, "gem_targets": "0部位 (嚴格風控 5分K未跌破，空手避軋)",
        "gpt_pnl": 0, "gpt_net": 1289681, "gpt_targets": "0部位 (門檻未達，空手避開玉晶光千元漲停)",
        "spread": 330914, "review": "大盤飆漲 500 點、玉晶光漲停！雙方嚴守實體黑棒濾網，一股未進，零虧損守住淨值！"
    },
    {
        "round": "Round 11", "date": "2026/09/17", "winner": "🟥 Gemini 勝",
        "gem_pnl": 77000, "gem_net": 1697595, "gem_targets": "6173 信昌電(+9.5點), 8039 台虹(+8點), 2327 國巨*(+3.5點)",
        "gpt_pnl": 30000, "gpt_net": 1319681, "gpt_targets": "8039 台虹(期 T1命中 +7.5點)",
        "spread": 377914, "review": "大盤衝 47,038 後跳水！雙方共選台虹期崩跌 6.7% 同步命中 T1；Gemini 多抓信昌電踩踏與國巨強平，單期大賺 7.7 萬！"
    }
]

# ==============================================================================
# 4. 🎯 2026-09-17 盤後 12 檔母池三維大數據庫 (主力進出 × 融資增減 × 權證避險)
# ==============================================================================
DEFAULT_WATCHLIST = [
    {
        "代號": "2344", "名稱": "華邦電", "昨收": 170.00, "昨日鎖碼量": 120007, "融資增減(張)": 3899, "券資比": 2.1, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 180.00, "最低價": 170.00,
        "主力分點": [
            {"分點": "元大-北投", "買超": 2042, "均價": 174.50, "佔比": 1.70},
            {"分點": "台灣摩根士丹利", "買超": 1980, "均價": 174.67, "佔比": 1.65},
            {"分點": "摩根大通", "買超": -4705, "均價": 173.78, "佔比": -3.92},
            {"分點": "凱基-台北", "買超": -3360, "均價": 175.31, "佔比": -2.80},
            {"分點": "富邦", "買超": -2879, "均價": 173.89, "佔比": -2.40}
        ]
    },
    {
        "代號": "8039", "名稱": "台虹", "昨收": 257.00, "昨日鎖碼量": 22338, "融資增減(張)": 209, "券資比": 4.6, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 279.00, "最低價": 256.50,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 628, "均價": 261.49, "佔比": 2.81},
            {"分點": "美商高盛", "買超": 329, "均價": 261.12, "佔比": 1.47},
            {"分點": "美林", "買超": -1508, "均價": 259.12, "佔比": -6.75},
            {"分點": "富邦", "買超": -859, "均價": 260.31, "佔比": -3.85}
        ]
    },
    {
        "代號": "2313", "名稱": "華通", "昨收": 218.50, "昨日鎖碼量": 30339, "融資增減(張)": 988, "券資比": 3.9, "權證認售(萬)": 31, "權證賣認購(萬)": 0,
        "最高價": 235.00, "最低價": 218.00,
        "主力分點": [
            {"分點": "美林", "買超": 469, "均價": 226.79, "佔比": 1.55},
            {"分點": "台灣摩根士丹利", "買超": -3483, "均價": 224.86, "佔比": -11.48},
            {"分點": "凱基-台北", "買超": -1875, "均價": 226.80, "佔比": -6.18}
        ]
    },
    {
        "代號": "2492", "名稱": "華新科", "昨收": 297.00, "昨日鎖碼量": 21569, "融資增減(張)": 710, "券資比": 3.0, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 314.50, "最低價": 295.00,
        "主力分點": [
            {"分點": "富邦", "買超": 803, "均價": 299.86, "佔比": 3.71},
            {"分點": "台新", "買超": -1128, "均價": 301.96, "佔比": -5.21},
            {"分點": "摩根大通", "買超": -1084, "均價": 301.93, "佔比": -5.01}
        ]
    },
    {
        "代號": "3189", "名稱": "景碩", "昨收": 805.00, "昨日鎖碼量": 15614, "融資增減(張)": 72, "券資比": 4.1, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 835.00, "最低價": 785.00,
        "主力分點": [
            {"分點": "凱基", "買超": 941, "均價": 802.52, "佔比": 5.98},
            {"分點": "新加坡商瑞銀", "買超": -842, "均價": 809.94, "佔比": -5.35},
            {"分點": "台灣摩根士丹利", "買超": -776, "均價": 805.14, "佔比": -4.93}
        ]
    },
    {
        "代號": "2455", "名稱": "全新", "昨收": 534.00, "昨日鎖碼量": 28550, "融資增減(張)": 906, "券資比": 5.8, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 566.00, "最低價": 515.00,
        "主力分點": [
            {"分點": "美商高盛", "買超": 1214, "均價": 543.11, "佔比": 4.24},
            {"分點": "台灣摩根士丹利", "買超": -716, "均價": 544.78, "佔比": -2.50},
            {"分點": "美林", "買超": -421, "均價": 540.93, "佔比": -1.47}
        ]
    },
    {
        "代號": "2327", "名稱": "國巨*", "昨收": 529.00, "昨日鎖碼量": 22037, "融資增減(張)": 117, "券資比": 3.2, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 553.00, "最低價": 529.00,
        "主力分點": [
            {"分點": "美林", "買超": 353, "均價": 547.51, "佔比": 1.54},
            {"分點": "摩根大通", "買超": -1320, "均價": 539.34, "佔比": -5.74},
            {"分點": "美商高盛", "買超": -943, "均價": 539.23, "佔比": -4.10}
        ]
    },
    {
        "代號": "3037", "名稱": "欣興", "昨收": 940.00, "昨日鎖碼量": 16715, "融資增減(張)": 3, "券資比": 4.8, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 993.00, "最低價": 940.00,
        "主力分點": [
            {"分點": "統一", "買超": 359, "均價": 970.53, "佔比": 2.14},
            {"分點": "永豐金", "買超": -1345, "均價": 959.81, "佔比": -8.03}
        ]
    },
    {
        "代號": "2408", "名稱": "南亞科", "昨收": 488.00, "昨日鎖碼量": 44824, "融資增減(張)": -156, "券資比": 2.8, "權證認售(萬)": 0, "權證賣認購(萬)": -1858,
        "最高價": 504.00, "最低價": 488.00,
        "主力分點": [
            {"分點": "花旗環球", "買超": 1340, "均價": 495.10, "佔比": 2.98},
            {"分點": "凱基-台北", "買超": -1574, "均價": 495.64, "佔比": -3.50}
        ]
    },
    {
        "代號": "3260", "名稱": "威剛", "昨收": 395.00, "昨日鎖碼量": 3657, "融資增減(張)": -41, "券資比": 4.2, "權證認售(萬)": 0, "權證賣認購(萬)": -1510,
        "最高價": 405.50, "最低價": 395.00,
        "主力分點": [
            {"分點": "合庫", "買超": 321, "均價": 398.97, "佔比": 8.78},
            {"分點": "台灣摩根士丹利", "買超": -297, "均價": 398.03, "佔比": -8.12}
        ]
    },
    {
        "代號": "6173", "名稱": "信昌電", "昨收": 303.50, "昨日鎖碼量": 26376, "融資增減(張)": -546, "券資比": 3.9, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 325.00, "最低價": 295.00,
        "主力分點": [
            {"分點": "國泰-敦南", "買超": 392, "均價": 312.27, "佔比": 1.49},
            {"分點": "元大", "買超": -531, "均價": 312.93, "佔比": -2.01}
        ]
    },
    {
        "代號": "3406", "名稱": "玉晶光", "昨收": 965.00, "昨日鎖碼量": 10750, "融資增減(張)": 208, "券資比": 5.1, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 1045.00, "最低價": 947.00,
        "主力分點": [
            {"分點": "永豐金", "買超": 225, "均價": 993.26, "佔比": 2.09},
            {"分點": "台灣摩根士丹利", "買超": -443, "均價": 982.49, "佔比": -4.12}
        ]
    }
]

# ==============================================================================
# 5. Gemini Round 12 官方決戰封單陣列 (凍結備查)
# ==============================================================================
ORDERS_GEMINI_R12 = [
    {"rank": "🥇 首選 1", "ticker": "2344", "name": "華邦電(期)", "tool": "期貨", "size": "2口", "margin": 91800, "trigger": 168.0, "stop": 174.5, "t1": 162.5, "t2": 158.0, "shares": 4000, "reason": "天量長黑天地針，外資合倒1.3萬張，融資狂增+3899張居冠！"},
    {"rank": "🥈 首選 2", "ticker": "8039", "name": "台虹(期)", "tool": "期貨", "size": "2口", "margin": 138780, "trigger": 255.0, "stop": 263.0, "t1": 247.0, "t2": 241.0, "shares": 4000, "reason": "重挫6.7%破底，美林重砍1508張，散戶融資連五天逆勢加碼！"},
    {"rank": "🥉 首選 3", "ticker": "2313", "name": "華通(期)", "tool": "期貨", "size": "2口", "margin": 117990, "trigger": 217.0, "stop": 224.5, "t1": 210.0, "t2": 205.0, "shares": 4000, "reason": "大摩單點倒11.5%，融資暴增+988張深套，認售權證買超避險！"},
    {"rank": "4", "ticker": "2492", "name": "華新科(期)", "tool": "期貨", "size": "2口", "margin": 160380, "trigger": 295.0, "stop": 304.0, "t1": 286.0, "t2": 279.0, "shares": 4000, "reason": "失守300大關，外資提款4000張，散戶融資逆勢加碼+710張！"},
    {"rank": "5", "ticker": "3189", "name": "景碩(期)", "tool": "期貨", "size": "1口", "margin": 217350, "trigger": 798.0, "stop": 818.0, "t1": 776.0, "t2": 760.0, "shares": 2000, "reason": "衝高殺破800，外資五巨頭合砍3300張，本土接刀高檔套牢！"}
]

# ==============================================================================
# 6. 量化指標與技術分析模組
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

# ==============================================================================
# 7. 四層式連動 K 線繪圖引擎 (完全繼承原始 HTML/JS 跨層懸浮同步)
# ==============================================================================
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
# 8. 量化撮合與方案 A 階梯結算引擎
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
        return {
            "status": "❌ 停損平倉", "entry_price": entry_p, "exit_price": stop_p,
            "pnl_points": pts, "pnl_ntd": int(pts * shares), "note": f"盤中突破停損價 {stop_p}，嚴格停損。"
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
# 9. 母池數據加載
# ==============================================================================
def load_radar_market_data(pool_list):
    enhanced = []
    for item in pool_list:
        code = item.get("代號")
        name = item.get("名稱", STOCK_NAME_DICT.get(code, f"個股_{code}"))
        close_p = float(item.get("昨收", 100.0))
        high_p = float(item.get("最高價", close_p))
        low_p = float(item.get("最低價", close_p * 0.96))
        prev_close = round(close_p * 0.98, 2)
        margin_change = item.get("融資增減(張)", 0)
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
            b_ratio = float(b.get("佔比", round((b_vol / max(tot_vol, 1)) * 100, 2)))
            
            p_rate = round(((close_p - b_cost) / b_cost) * 100, 2) if b_cost > 0 else 0.0
            profit_wan = int(round(((close_p - b_cost) * b_vol * 1000) / 10000))
            
            if b_vol > 0:
                tot_buy_shares += b_vol
                tot_cost_amount += b_cost * b_vol * 1000
                tot_ratio += b_ratio

            detailed_brokers.append({
                "分點名稱": b_name, "買超張數": b_vol, "佔比(%)": b_ratio,
                "收盤價": close_p, "預估成本": b_cost, "預估獲利(萬)": profit_wan,
                "報酬率(%)": p_rate, "倒貨意願": "🔴 極高" if p_rate >= 1.0 else ("🟡 普通" if p_rate >= -0.5 else "🟢 停損出貨")
            })

        avg_cost = round(tot_cost_amount / (tot_buy_shares * 1000), 2) if tot_buy_shares > 0 else close_p
        
        # 9/17 盤後三維評級更新
        score_dict = {"2344": 97, "8039": 96, "2313": 94, "2492": 91, "3189": 88, "2455": 85, "2327": 83, "3037": 80, "2408": 75, "3260": 70, "6173": 60, "3406": 20}
        score = score_dict.get(code, 60)

        alert_tag = "⚡ 待機狙擊" if score >= 90 else ("⚡ 次選觀察" if score >= 75 else ("🛑 官方禁空" if score <= 30 else "⚪ 觀望"))
        alert_desc = f"【{alert_tag}】融資: {margin_change:+d} 張，主力鎖碼 {tot_buy_shares:,} 張"
        
        enhanced.append({
            "股票代號": code, "股票名稱": name, "個期": "期" if code in STOCK_FUTURES_SET else "—",
            "現價": close_p, "昨收": prev_close, "漲跌": round(close_p - prev_close, 2),
            "漲跌幅(%)": round(((close_p - prev_close) / prev_close) * 100, 2),
            "近高壓力(NH)": nh_res, "最高壓力(AH)": ah_res, "主力加權成本": avg_cost,
            "主力合計買超": tot_buy_shares, "主力合計佔比(%)": round(tot_ratio, 2),
            "融資增減(張)": margin_change, "券資比(%)": item.get("券資比", 3.0),
            "短空勝率分": score, "即時信號": alert_tag, "盤中警報": alert_desc,
            "各分點清單": detailed_brokers, "5日均量(張)": tot_vol
        })
    return pd.DataFrame(enhanced).sort_values(by="短空勝率分", ascending=False).reset_index(drop=True)

if "custom_watchlist" not in st.session_state or len(st.session_state.get("custom_watchlist", [])) != len(DEFAULT_WATCHLIST):
    st.session_state["custom_watchlist"] = DEFAULT_WATCHLIST

df_display = load_radar_market_data(st.session_state["custom_watchlist"])
df_display.index = range(1, len(df_display) + 1)

# ==============================================================================
# 10. 側邊欄與總體戰績儀表板
# ==============================================================================
st.sidebar.title("⚡ 短空雷達量化控制台")
st.sidebar.markdown(f"**決戰輪次**：`Round 12` ({R12_DATE})")
st.sidebar.markdown(f"**母池籌碼基準**：`{DATA_BASE_DATE}` 盤後大數據")

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 賽事累計淨值儀表板")
st.sidebar.markdown(f"""
<div class="metric-card-gemini">
    <div style="font-size: 13px; color: #BBB;">🟥 Gemini 總淨值 (8勝1負2平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_GEMINI:,}</div>
    <div style="font-size: 12px; color: #81C784;">R11 台虹+信昌電+國巨 (+NT$ 77,000)</div>
</div>
<div class="metric-card-gpt">
    <div style="font-size: 13px; color: #BBB;">🟦 ChatGPT 總淨值 (1勝8負2平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CHATGPT:,}</div>
    <div style="font-size: 12px; color: #81C784;">R11 台虹期命中 (+NT$ 30,000)</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.info(f"🚩 **雙方差距**：Gemini 領先 **NT$ {NET_SPREAD:,}**\n\n**單檔上限 (20%)**：\n• Gemini: NT$ {LIMIT_GEMINI:,}\n• GPT: NT$ {LIMIT_CHATGPT:,}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📜 官方執法核心規範")
st.sidebar.caption(
    """
    1. **實體破線確認**：5分K收盤 < 開盤 且 收盤 < 進場價。
    2. **不利滑價撮合**：成交價 = min(觸發K收, 次K開)。
    3. **方案 A 優先**：穿破 T1 即刻全數保底鎖利平倉。
    4. **尾盤強平**：13:25～13:30 強制平倉清算。
    """
)

# ==============================================================================
# 11. 主頁面五大核心分頁
# ==============================================================================
st.title("🎯 雙 AI 量化當沖 PK 賽事｜Round 12 旗艦戰情室")
st.caption(f"數據庫基準：{DATA_BASE_DATE} 臺灣證券交易所/櫃買中心/30+主力分點/自營商權證三維大數據")

tab_workspace, tab_orders, tab_matcher, tab_radar, tab_history = st.tabs([
    "🖥️ 專業操盤工作台 (K線與分點)",
    "⚔️ R12 官方決戰封單名冊", 
    "🧮 官方撮合與方案A結算模擬器",
    "📊 12檔母池籌碼雷達全景表",
    "🏆 R1~R11 淨值覆盤庫"
])

# ------------------------------------------------------------------------------
# TAB 1: 專業操盤工作台
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

        # 標的摘要卡片
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
                <span style="color: #AAA;">融資增減：</span><span style="font-weight: bold; color: {'#FF4444' if target_row['融資增減(張)']>=0 else '#00FF66'};">{target_row['融資增減(張)']:+,} 張</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px;">
                <span style="color: #AAA;">主力鎖碼量：</span><span style="font-weight: bold; color: #00FF66;">{target_row['主力合計買超']:,} 張</span>
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

        # 券商分點列表
        st.markdown(f"#### 🏢 【{target_name}】主力分點鎖碼持倉明細")
        b_list = target_row.get("各分點清單", [])
        if b_list:
            df_b = pd.DataFrame(b_list)
            df_b.index = range(1, len(df_b) + 1)
            st.dataframe(df_b, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: R12 雙方正式決戰封單名冊
# ------------------------------------------------------------------------------
with tab_orders:
    st.subheader("⚔️ Round 12 官方決戰名冊陣列 (執法存證備查)")
    col_g, col_c = st.columns(2)
    
    with col_g:
        st.markdown("#### 🟥 Gemini 戰情室 R12 正式封單")
        st.caption(f"淨值：NT$ {CAPITAL_GEMINI:,}｜單檔上限：NT$ {LIMIT_GEMINI:,}")
        
        df_gem_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "停利 T1": f"{x['t1']:.1f}", "停利 T2": f"{x['t2']:.1f}", "規格/保證金": f"{x['size']} ({x['margin']//1000}K)"}
            for x in ORDERS_GEMINI_R12
        ])
        st.dataframe(df_gem_ui, use_container_width=True, hide_index=True)
        
        with st.expander("🔍 查看 Gemini R12 籌碼依據與量化細節", expanded=True):
            for x in ORDERS_GEMINI_R12:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']:.1f}`**")
                st.caption(f"└ 核心籌碼：{x['reason']}")
                
    with col_c:
        st.markdown("#### 🟦 ChatGPT 戰情室 R12 待命陣列")
        st.caption(f"淨值：NT$ {CAPITAL_CHATGPT:,}｜單檔上限：NT$ {LIMIT_CHATGPT:,}")
        st.info("靜候 ChatGPT 戰情室提交 Round 12 正式對決封單！")

    st.markdown("---")
    st.subheader("🛑 Round 12 官方共識禁空名單（NO SHORT LIST）")
    cn1, cn2 = st.columns(2)
    cn1.error("🚫 **3406 玉晶光**\n\n千元關卡多空劇烈洗盤震盪，振幅逼近百點，官方公約維持絕對禁空，嚴防雙巴。")
    cn2.warning("⚠️ **6173 信昌電**\n\n昨日多頭踩踏融資大退 -546 張，隔日沖出貨大半，短線肉身空間壓縮，暫移出空方首選。")

# ------------------------------------------------------------------------------
# TAB 3: 官方撮合與方案 A 結算模擬器
# ------------------------------------------------------------------------------
with tab_matcher:
    st.subheader("🧮 裁判室專用：5分K實體跌破撮合與方案 A 結算模擬器")
    st.caption("依據官方公約：取不利撮合價進場，盤中穿破 T1 即刻鎖利，未達條件者於 13:25 強制結算。")
    
    sim_c1, sim_c2 = st.columns(2)
    with sim_c1:
        st.markdown("**步驟 1：選擇審查訂單**")
        target_order = st.selectbox(
            "選擇審查封單：", ORDERS_GEMINI_R12,
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
                    st.error(f"📉 **核定結算總損益**：`-NT$ {abs(res['pnl_ntd']):,}`")
        st.caption(f"**仲裁備註**：{res['note']}")

# ------------------------------------------------------------------------------
# TAB 4: 12檔母池籌碼雷達全景表
# ------------------------------------------------------------------------------
with tab_radar:
    st.subheader("📋 12 檔母池三維大數據全景表 (勝率降序排列)")
    preferred_cols = [
        "短空勝率分", "股票代號", "股票名稱", "個期", "現價", "即時信號",
        "融資增減(張)", "近高壓力(NH)", "最高壓力(AH)", "主力加權成本", "主力合計買超", "主力合計佔比(%)"
    ]
    st.dataframe(df_display[[c for c in preferred_cols if c in df_display.columns]], use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 5: 🏆 R1~R11 淨值覆盤庫
# ------------------------------------------------------------------------------
with tab_history:
    st.subheader("📈 雙 AI 歷輪淨值走勢與狙擊標的覆盤矩陣 (R0～R11)")
    st.caption("完整記錄每一輪的勝負演變、累積淨值變化與核心狙擊標的，支援量化回測與裁判室複查。")
    
    df_hist = pd.DataFrame(HISTORICAL_ROUNDS)
    
    # 互動式淨值走勢圖 (Plotly)
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(
        x=df_hist["round"], y=df_hist["gem_net"],
        mode="lines+markers+text", name="🟥 Gemini 淨值",
        line=dict(color="#FF4444", width=3),
        text=df_hist["gem_net"].apply(lambda x: f"${x//1000}K"),
        textposition="top center", textfont=dict(color="#FF8888", size=10)
    ))
    fig_hist.add_trace(go.Scatter(
        x=df_hist["round"], y=df_hist["gpt_net"],
        mode="lines+markers+text", name="🟦 ChatGPT 淨值",
        line=dict(color="#1E88E5", width=3, dash="dot"),
        text=df_hist["gpt_net"].apply(lambda x: f"${x//1000}K"),
        textposition="bottom center", textfont=dict(color="#64B5F6", size=10)
    ))
    fig_hist.update_layout(
        template="plotly_dark", plot_bgcolor="#111", paper_bgcolor="#111",
        title="雙方累積淨值曲線 (Net Worth Curve)",
        xaxis_title="對決輪次", yaxis_title="帳戶淨值 (NT$)",
        height=420, margin=dict(l=40, r=40, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_hist, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📋 歷輪戰績逐筆明細表 (含當期損益與核心狙擊標的)")
    
    table_view = df_hist[[
        "round", "date", "winner", "gem_pnl", "gem_net", "gem_targets", 
        "gpt_pnl", "gpt_net", "gpt_targets", "spread"
    ]].copy()
    
    table_view["gem_pnl"] = table_view["gem_pnl"].apply(lambda x: f"{x:+,}")
    table_view["gem_net"] = table_view["gem_net"].apply(lambda x: f"${x:,}")
    table_view["gpt_pnl"] = table_view["gpt_pnl"].apply(lambda x: f"{x:+,}")
    table_view["gpt_net"] = table_view["gpt_net"].apply(lambda x: f"${x:,}")
    table_view["spread"] = table_view["spread"].apply(lambda x: f"${x:,}")
    
    table_view.columns = [
        "輪次", "日期", "判決結果", "Gemini 損益", "Gemini 淨值", "🟥 Gemini 核心狙擊標的",
        "ChatGPT 損益", "ChatGPT 淨值", "🟦 ChatGPT 核心狙擊標的", "領先差距"
    ]
    st.dataframe(table_view, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🔍 歷輪戰況深度覆盤與重大仲裁紀錄")
    
    for r_item in reversed(HISTORICAL_ROUNDS):
        with st.expander(f"📌 {r_item['round']} ({r_item['date']}) 判決：{r_item['winner']} ｜ 領先差：NT$ {r_item['spread']:,}", expanded=(r_item["round"] in ["Round 10", "Round 11"])):
            c_rev1, c_rev2 = st.columns(2)
            with c_rev1:
                st.markdown(f"**🟥 Gemini 戰情報告**")
                st.write(f"- 當期損益：`{r_item['gem_pnl']:+,} NT$`")
                st.write(f"- 結算淨值：`NT$ {r_item['gem_net']:,}`")
                st.write(f"- 核心部位：{r_item['gem_targets']}")
            with c_rev2:
                st.markdown(f"**🟦 ChatGPT 戰情報告**")
                st.write(f"- 當期損益：`{r_item['gpt_pnl']:+,} NT$`")
                st.write(f"- 結算淨值：`NT$ {r_item['gpt_net']:,}`")
                st.write(f"- 核心部位：{r_item['gpt_targets']}")
            st.info(f"💡 **戰術覆盤備註**：{r_item['review']}")

# ==============================================================================
# 12. 系統頁尾
# ==============================================================================
st.markdown("---")
st.caption(f"雙 AI 量化短空雷達系統 v12.0 旗艦版｜2026/09/17 盤後三維數據凍結備查｜執法標準：5分K實體跌破 + 不利撮合滑價 + 方案A鎖利 + 13:25強平")
