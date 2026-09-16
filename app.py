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
    page_title="雙 AI 量化短空雷達 (Round 11 旗艦裁判長版)", 
    layout="wide", 
    page_icon="🎯", 
    initial_sidebar_state="expanded"
)

# 注入戰情室與量化卡片專用樣式
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
# 2. 官方公約常數與雙方帳戶狀態 (2026/09/16 結算後正式凍結生效)
# ==============================================================================
R11_DATE = "2026/09/17"
DATA_BASE_DATE = "2026/09/16"

# 帳戶資本與風控額度
CAPITAL_GEMINI = 1620595
CAPITAL_CHATGPT = 1289681
LIMIT_GEMINI = int(CAPITAL_GEMINI * 0.20)    # NT$ 324,119
LIMIT_CHATGPT = int(CAPITAL_CHATGPT * 0.20)  # NT$ 257,936
NET_SPREAD = CAPITAL_GEMINI - CAPITAL_CHATGPT # NT$ 330,914

# 期交所個股期貨支援名單 (支援 2000 股規格撮合)
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

# 30 大隔日沖主力名冊
BROKER_DATA_CATALOG = [
    [1, "外資量化", "美商美林", "大型權值股、熱門題材股", "演算法高頻點火，尾盤大單市價掃進鎖漲停", "09:00～09:15 不計價市價倒出，常造成早盤垂直殺盤", "破 VWAP 即順勢放空，下殺放量 80% 快速停利"],
    [2, "外資量化", "摩根大通", "AI伺服器、高價電子股", "程式量化跟風單，偏好拉抬具備國際題材標的", "早盤開高即分批掛內外盤倒貨，持續出貨至 10:00", "衝撞 NH 遇阻即試空，需留意法人反手洗盤"],
    [3, "外資量化", "新加坡商瑞銀", "權值電子、航運、半導體", "與美林高頻聯動，喜好於高檔爆量時搶進", "09:05～09:20 集中倒出，破均價後不再護盤", "跌破主力加權成本時為標準加碼放空點"],
    [4, "外資量化", "台灣摩根士丹利", "中大型高價股、IC設計", "早盤拉抬後尾盤鎖單，具備較高部位容忍度", "開盤先拉高營造強勢假象，隨後反手市價灌單", "觀察「假衝高誘多」，5分K 留長上影線果斷摸頂"],
    [5, "外資量化", "美商高盛", "晶圓代工、蘋果供應鏈", "國際資金與量化混合，點火通常伴隨現貨放量", "早盤直接出清昨日部位，極少留倉隔日", "順勢跟空，注意券資比過高標的避免被軋"],
    [6, "凱基軍團", "凱基-台北", "全市場強勢飆股、主流龍頭", "號稱隔日沖總舵主，動輒數千張連敲硬鎖漲停", "09:00～09:10 市價大單瘋狂倒貨，破線後絕不回頭", "早盤衝高滯漲第一順位狙擊目標，勝率極高"],
    [7, "凱基軍團", "凱基-站前", "強勢突破股、集團股", "擅長關鍵點位重鎖，常與外資聯動進出", "早盤迅速宣洩持倉，跌破成本即不再護盤", "開盤見爆量黑K直接順勢短空"],
    [8, "雙北核心", "元大", "權值股、強勢鎖碼股", "資金規模龐大，通常兼具造市與短線交易", "早盤均勻出脫，若遇大盤偏弱則加速倒貨", "適合穩健型短空，獲利空間約 1.5%～3%"],
    [9, "雙北核心", "國票-敦北法人", "機構大戶、高價主流股", "大部位集中進出，拉抬時常伴隨極大成交額", "早盤出貨節奏較慢，分批大單掛賣壓制盤面", "觀察 VWAP 均價線下方的大單壓盤，偏空操作"],
    [10, "雙北核心", "國泰-敦南", "車用電子、重電題材股", "擅長波段與隔日沖混搭，量大時多為隔日沖", "開高後連續出脫，若遇大盤偏弱則加速倒貨", "配合大盤偏弱盤勢時放空，勝率大幅提升"]
]
TARGET_BROKERS = [row[2] for row in BROKER_DATA_CATALOG]

# ==============================================================================
# 3. 🎯 2026-09-16 盤後 12 檔母池大數據庫 (主力進出 × 融資 × 權證完整版)
# ==============================================================================
DEFAULT_WATCHLIST = [
    {
        "代號": "2455", "名稱": "全新", "昨收": 515.00, "昨日鎖碼量": 19718, "融資增減(張)": 627, "券資比": 5.8, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 534.00, "最低價": 506.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 301, "均價": 519.53, "佔比": 1.53},
            {"分點": "元大-崇德", "買超": 220, "均價": 518.07, "佔比": 1.12},
            {"分點": "國票-安和", "買超": 187, "均價": 522.05, "佔比": 0.95},
            {"分點": "美林", "買超": -584, "均價": 515.97, "佔比": -2.96},
            {"分點": "富邦", "買超": -443, "均價": 522.60, "佔比": -2.25}
        ]
    },
    {
        "代號": "8039", "名稱": "台虹", "昨收": 275.50, "昨日鎖碼量": 12424, "融資增減(張)": 390, "券資比": 4.6, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 278.00, "最低價": 271.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 488, "均價": 274.66, "佔比": 3.93},
            {"分點": "元大-信義安和", "買超": 250, "均價": 277.26, "佔比": 2.01},
            {"分點": "摩根大通", "買超": -1731, "均價": 274.42, "佔比": -13.93},
            {"分點": "永豐金", "買超": -319, "均價": 275.03, "佔比": -2.57}
        ]
    },
    {
        "代號": "6173", "名稱": "信昌電", "昨收": 315.00, "昨日鎖碼量": 28232, "融資增減(張)": 551, "券資比": 3.9, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 323.00, "最低價": 295.00,
        "主力分點": [
            {"分點": "統一", "買超": 890, "均價": 311.10, "佔比": 3.15},
            {"分點": "富邦-台北", "買超": 871, "均價": 313.17, "佔比": 3.09},
            {"分點": "凱基-台北", "買超": 470, "均價": 306.80, "佔比": 1.66},
            {"分點": "國泰-敦南", "買超": -266, "均價": 307.54, "佔比": -0.94}
        ]
    },
    {
        "代號": "3189", "名稱": "景碩", "昨收": 820.00, "昨日鎖碼量": 10957, "融資增減(張)": 720, "券資比": 4.1, "權證認售(萬)": 0, "權證賣認購(萬)": -460,
        "最高價": 832.00, "最低價": 792.00,
        "主力分點": [
            {"分點": "富邦-新店", "買超": 331, "均價": 823.52, "佔比": 3.02},
            {"分點": "統一", "買超": 318, "均價": 820.14, "佔比": 2.90},
            {"分點": "永豐金-匯立", "買超": -283, "均價": 813.46, "佔比": -2.58},
            {"分點": "台灣摩根士丹利", "買超": -254, "均價": 812.07, "佔比": -2.32}
        ]
    },
    {
        "代號": "2327", "名稱": "國巨*", "昨收": 536.00, "昨日鎖碼量": 27854, "融資增減(張)": 55, "券資比": 3.2, "權證認售(萬)": -164, "權證賣認購(萬)": 0,
        "最高價": 543.00, "最低價": 526.00,
        "主力分點": [
            {"分點": "永豐金", "買超": 292, "均價": 533.40, "佔比": 1.05},
            {"分點": "國泰-敦南", "買超": 283, "均價": 533.69, "佔比": 1.02},
            {"分點": "美林", "買超": -2640, "均價": 532.80, "佔比": -9.48},
            {"分點": "新加坡商瑞銀", "買超": -865, "均價": 534.33, "佔比": -3.11}
        ]
    },
    {
        "代號": "3037", "名稱": "欣興", "昨收": 961.00, "昨日鎖碼量": 11860, "融資增減(張)": 56, "券資比": 4.8, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 971.00, "最低價": 940.00,
        "主力分點": [
            {"分點": "富邦", "買超": 882, "均價": 963.55, "佔比": 7.44},
            {"分點": "美商高盛", "買超": -1560, "均價": 952.32, "佔比": -13.15},
            {"分點": "凱基", "買超": -730, "均價": 953.29, "佔比": -6.16}
        ]
    },
    {
        "代號": "2492", "名稱": "華新科", "昨收": 307.50, "昨日鎖碼量": 15103, "融資增減(張)": -391, "券資比": 3.0, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 307.50, "最低價": 295.50,
        "主力分點": [
            {"分點": "凱基-台北", "買超": 931, "均價": 302.56, "佔比": 6.16},
            {"分點": "台灣摩根士丹利", "買超": 641, "均價": 301.40, "佔比": 4.24},
            {"分點": "新加坡商瑞銀", "買超": -534, "均價": 302.82, "佔比": -3.54}
        ]
    },
    {
        "代號": "2313", "名稱": "華通", "昨收": 225.00, "昨日鎖碼量": 18970, "融資增減(張)": -22, "券資比": 3.9, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 225.00, "最低價": 216.00,
        "主力分點": [
            {"分點": "元大", "買超": 636, "均價": 221.89, "佔比": 3.35},
            {"分點": "摩根大通", "買超": -797, "均價": 221.13, "佔比": -4.20}
        ]
    },
    {
        "代號": "3260", "名稱": "威剛", "昨收": 399.50, "昨日鎖碼量": 3365, "融資增減(張)": -194, "券資比": 4.2, "權證認售(萬)": 0, "權證賣認購(萬)": 1580,
        "最高價": 399.50, "最低價": 389.00,
        "主力分點": [
            {"分點": "美好-富順", "買超": 294, "均價": 394.44, "佔比": 8.74},
            {"分點": "永豐金", "買超": 229, "均價": 397.49, "佔比": 6.81}
        ]
    },
    {
        "代號": "2344", "名稱": "華邦電", "昨收": 169.00, "昨日鎖碼量": 83218, "融資增減(張)": -2056, "券資比": 2.1, "權證認售(萬)": -207, "權證賣認購(萬)": 0,
        "最高價": 169.50, "最低價": 163.50,
        "主力分點": [
            {"分點": "美商高盛", "買超": 4925, "均價": 166.79, "佔比": 5.92},
            {"分點": "美林", "買超": 3953, "均價": 166.70, "佔比": 4.75}
        ]
    },
    {
        "代號": "2408", "名稱": "南亞科", "昨收": 492.50, "昨日鎖碼量": 36437, "融資增減(張)": -741, "券資比": 2.8, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 495.00, "最低價": 475.00,
        "主力分點": [
            {"分點": "元大", "買超": 1924, "均價": 484.67, "佔比": 5.28},
            {"分點": "美林", "買超": 1094, "均價": 483.74, "佔比": 3.00}
        ]
    },
    {
        "代號": "3406", "名稱": "玉晶光", "昨收": 1005.00, "昨日鎖碼量": 4089, "融資增減(張)": 153, "券資比": 5.1, "權證認售(萬)": 71, "權證賣認購(萬)": 0,
        "最高價": 1005.00, "最低價": 941.00,
        "主力分點": [
            {"分點": "富邦", "買超": 556, "均價": 1003.82, "佔比": 13.60},
            {"分點": "元大", "買超": 349, "均價": 991.48, "佔比": 8.54}
        ]
    }
]

# ==============================================================================
# 4. 雙方 Round 11 正式封單陣列 (官方存證凍結版)
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
# 5. 抓取引擎與指標計算模組
# ==============================================================================
def pad_display_text(text, target_display_width):
    current_width = 0
    for ch in str(text):
        if unicodedata.east_asian_width(ch) in ('F', 'W', 'A'):
            current_width += 2
        else:
            current_width += 1
    return str(text) + (" " * max(target_display_width - current_width, 0))

def fetch_from_histock(stock_code, close_price, total_vol):
    url = f"https://histock.tw/stock/branch.aspx?no={stock_code}"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://histock.tw/"}
    try:
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            table = soup.find("table", {"class": "grid-table"})
            if table:
                cleaned = []
                for row in table.find_all("tr")[1:6]:
                    cols = row.find_all("td")
                    if len(cols) >= 4:
                        name = cols[0].text.strip()
                        v_str = cols[1].text.strip().replace(",", "").replace("+", "")
                        p_str = cols[3].text.strip().replace(",", "")
                        if v_str.isdigit():
                            vol = int(v_str)
                            cost = float(p_str) if p_str.replace(".", "", 1).isdigit() else close_price
                            cleaned.append({"分點": name, "買超": vol, "均價": cost, "佔比": round((vol / max(total_vol, 1)) * 100, 2)})
                if cleaned: return cleaned
    except Exception: pass
    return None

@st.cache_data(ttl=600)
def auto_fetch_broker_data(stock_code, close_price, total_vol):
    code_str = str(stock_code).strip()
    res = fetch_from_histock(code_str, close_price, total_vol)
    if res: return res
    for item in DEFAULT_WATCHLIST:
        if item.get("代號") == code_str:
            return item.get("主力分點", [])
    return []

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
# 6. 四層式連動 K 線繪圖引擎 (完全繼承原始 HTML/JS 跨層懸浮同步)
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
# 7. 量化撮合與方案 A 階梯結算引擎
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
# 8. 母池數據預加載與多空勝率演算法
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
        
        # 9/16 官方量化勝率評分
        score_dict = {"2455": 96, "8039": 95, "6173": 92, "3189": 89, "2327": 86, "3037": 84, "2492": 72, "2313": 68, "3260": 50, "2344": 30, "2408": 30, "3406": 10}
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
# 9. 側邊欄與總體戰績儀表板
# ==============================================================================
st.sidebar.title("⚡ 短空雷達量化控制台")
st.sidebar.markdown(f"**決戰輪次**：`Round 11` ({R11_DATE})")
st.sidebar.markdown(f"**母池籌碼基準**：`{DATA_BASE_DATE}` 盤後大數據")

# 淨值即時榜
st.sidebar.markdown("---")
st.sidebar.subheader("🏆 賽事累計淨值儀表板")
st.sidebar.markdown(f"""
<div class="metric-card-gemini">
    <div style="font-size: 13px; color: #BBB;">🟥 Gemini 總淨值 (7勝1負2平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_GEMINI:,}</div>
    <div style="font-size: 12px; color: #81C784;">R10 全數空手避軋 (損益 $0)</div>
</div>
<div class="metric-card-gpt">
    <div style="font-size: 13px; color: #BBB;">🟦 ChatGPT 總淨值 (1勝7負2平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CHATGPT:,}</div>
    <div style="font-size: 12px; color: #81C784;">R10 全數空手避軋 (損益 $0)</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.info(f"🚩 **雙方差距**：Gemini 領先 **NT$ {NET_SPREAD:,}**")

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
# 10. 主頁面四大核心分頁
# ==============================================================================
st.title("🎯 雙 AI 量化當沖 PK 賽事｜Round 11 旗艦戰情室")
st.caption(f"數據庫基準：{DATA_BASE_DATE} 臺灣證券交易所/櫃買中心/30+主力分點/自營商權證三維大數據")

tab_workspace, tab_orders, tab_matcher, tab_radar = st.tabs([
    "🖥️ 專業操盤工作台 (K線與分點)",
    "⚔️ R11 雙方正式決戰封單", 
    "🧮 官方撮合與方案A結算模擬器",
    "📊 12檔母池籌碼雷達全景表"
])

# ------------------------------------------------------------------------------
# TAB 1: 專業操盤工作台 (繼承原始左右分欄、等寬選單、4層式K線)
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
# TAB 2: R11 雙方正式決戰封單 (防截斷規格)
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
        
        with st.expander("🔍 查看 Gemini 籌碼依據與量化細節", expanded=True):
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
        
        with st.expander("🔍 查看 ChatGPT 型態邏輯與作戰口令", expanded=True):
            for x in ORDERS_CHATGPT:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']}`**")
                st.caption(f"└ 作戰型態：{x['reason']}")

    st.markdown("---")
    st.subheader("🛑 Round 11 官方共識禁空名單（NO SHORT LIST）")
    cn1, cn2, cn3 = st.columns(3)
    cn1.error("🚫 **3406 玉晶光**\n\n強勢漲停鎖死在 1,005 元，多頭極端擁擠，維持絕對禁空。")
    cn2.error("🚫 **2344 華邦電**\n\n高盛美林暴買 1.2 萬張，融資狂減 -2,056 張洗淨籌碼，嚴禁追空。")
    cn3.error("🚫 **2408 南亞科**\n\n元大美林反手狂補，大漲 5.8%，融資退 -741 張，結構由空翻多。")

# ------------------------------------------------------------------------------
# TAB 3: 官方撮合與方案 A 結算模擬器
# ------------------------------------------------------------------------------
with tab_matcher:
    st.subheader("🧮 裁判室專用：5分K實體跌破撮合與方案 A 結算模擬器")
    st.caption("依據官方公約：取不利撮合價進場，盤中穿破 T1 即刻鎖利，未達條件者於 13:25 強制結算。")
    
    sim_c1, sim_c2 = st.columns(2)
    with sim_c1:
        st.markdown("**步驟 1：選擇審查陣營與封單**")
        selected_side = st.radio("參賽陣營：", ["🟥 Gemini 戰情室", "🟦 ChatGPT 戰情室"], horizontal=True)
        order_set = ORDERS_GEMINI if "Gemini" in selected_side else ORDERS_CHATGPT
        
        target_order = st.selectbox(
            "選擇審查封單：", order_set,
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

# ==============================================================================
# 11. 系統頁尾
# ==============================================================================
st.markdown("---")
st.caption(f"雙 AI 量化短空雷達系統 v11.0 旗艦版｜2026/09/16 數據庫凍結備查｜執法標準：5分K實體跌破 + 不利撮合滑價 + 方案A鎖利 + 13:25強平")
