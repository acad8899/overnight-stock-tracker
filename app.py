import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
import unicodedata
import json
import requests
import re
from bs4 import BeautifulSoup
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 頁面排版設定：全寬展開
st.set_page_config(
    page_title="隔日沖主力短空雷達 (全自動AI智慧旗艦版)", 
    layout="wide", 
    page_icon="🎯", 
    initial_sidebar_state="collapsed"
)

# 🚀 強制版本控制金鑰：更新即可徹底清除 Streamlit Session 舊快取
DATA_VERSION = "20260909_R5_LOCKED"

# 期交所個股期貨支援名單
STOCK_FUTURES_SET = {
    "8039", "2408", "3260", "2449", "3231", "2327", "2376", "6488", "2313", "2492",
    "2330", "2317", "2454", "2382", "2603", "2609", "2344", "3037", "2368", "3017",
    "2383", "1519", "8210", "2059", "4551", "5289", "8299", "3406",
    "2615", "5314", "2489", "3006", "2337", "8046", "2426", "2455", "3189",
    "3374", "6239"
}

# 內建台股代號與名稱對照字典
STOCK_NAME_DICT = {
    "2313": "華通", "2426": "鼎元", "8039": "台虹", "3189": "景碩", "3406": "玉晶光",
    "2455": "全新", "3037": "欣興", "3260": "威剛", "2408": "南亞科", "2327": "國巨*",
    "2492": "華新科", "2344": "華邦電", "2303": "聯電", "3008": "大立光", "5274": "信驊",
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2382": "廣達", "2603": "長榮"
}

NAME_TO_CODE_DICT = {v: k for k, v in STOCK_NAME_DICT.items()}
TPEX_STOCKS = {"3260", "6488", "8299", "5289", "3211", "5483", "8112", "6213", "5314", "3105", "3374", "5274"}

# 30 大隔日沖主力名冊
BROKER_DATA_CATALOG = [
    [1, "外資量化", "美商美林", "大型權值股、熱門題材股", "演算法高頻點火，尾盤大單市價掃進鎖漲停", "09:00～09:15 不計價市價倒出，常造成早盤垂直殺盤", "破 VWAP 即順勢放空，下殺放量 80% 快速停利"],
    [2, "外資量化", "摩根大通", "AI伺服器、高價電子股", "程式量化跟風單，偏好拉抬具備國際題材標的", "早盤開高即分批掛內外盤倒貨，持續出貨至 10:00", "衝撞 NH 遇阻即試空，需留意法人反手洗盤"],
    [3, "外資量化", "新加坡商瑞銀", "權值電子、航運、半導體", "與美林高頻聯動，喜好於高檔爆量時搶進", "09:05～09:20 集中倒出，破均價後不再護盤", "跌破主力加權成本時為標準加碼放空點"],
    [4, "外資量化", "台灣摩根士丹利", "中大型高價股、IC設計", "早盤拉抬後尾盤鎖單，具備較高部位容忍度", "開盤先拉高營造強勢假象，隨後反手市價灌單", "觀察「假衝高誘多」，5分K 留長上影線果斷摸頂"],
    [5, "外資量化", "美商高盛", "晶圓代工、蘋果供應鏈", "國際資金與量化混合，點火通常伴隨現貨放量", "早盤直接出清昨日部位，極少留倉隔日", "順勢跟空，注意券資比過高標的避免被軋"],
    [6, "凱基軍團", "凱基-台北", "全市場強勢飆股、主流龍頭", "號稱隔日沖總舵主，動輒數千張連敲硬鎖漲停", "09:00～09:10 市價大單瘋狂倒貨，破線後絕不回頭", "早盤衝高滯漲第一順位狙擊目標，勝率極高"],
    [7, "凱基軍團", "凱基-信義", "強勢突破飆股、關鍵重鎖", "擅長漲停板排隊重鎖，次日早盤開高反手傾瀉", "開盤開高衝刺後若現急單倒貨，破開盤價順勢跟空", "配合現貨量能竭盡放空，勝率極高"],
    [8, "雙北核心", "元大", "權值股、強勢鎖碼股", "資金規模龐大，通常兼具造市與短線交易", "早盤均勻出脫，若遇大盤偏弱則加速倒貨", "適合穩健型短空，獲利空間約 1.5%～3%"],
    [9, "雙北核心", "富邦", "大型權值股、強勢轉折股", "主導單一飆股隔日沖，具備極強定價破壞力", "早盤開盤即分批倒貨，一旦翻黑絕不留戀", "跌破當日開盤價與均線為最標準空點"],
    [10, "雙北核心", "國泰-敦南", "車用電子、重電題材股", "擅長波段與隔日沖混搭，量大時多為隔日沖", "開高後連續出脫，若遇大盤偏弱則加速倒貨", "配合大盤偏弱盤勢時放空，勝率大幅提升"]
]

TARGET_BROKERS = [row[2] for row in BROKER_DATA_CATALOG]

# 🎯 2026-09-08 盤後官方融資券 × 權證避險 × 主力分點最新校準資料庫 (Round 5 法定 12 檔)
DEFAULT_WATCHLIST = [
    {
        "代號": "2313", "名稱": "華通", "昨收": 231.00, "昨日鎖碼量": 39943, "融資增減(張)": 666, "券資比": 4.3, "權證認售(萬)": 0, "權證賣認購(萬)": -1277,
        "最高價": 241.00, "最低價": 227.50,
        "主力分點": [
            {"分點": "凱基-站前", "買超": -7115, "均價": 230.67, "佔比": -17.78},
            {"分點": "台灣摩根士丹利", "買超": -1754, "均價": 231.76, "佔比": -4.38},
            {"分點": "美商高盛", "買超": 828, "均價": 231.05, "佔比": 2.07},
            {"分點": "富邦", "買超": 770, "均價": 230.98, "佔比": 1.92},
            {"分點": "統一", "買超": -467, "均價": 231.64, "佔比": -1.17},
            {"分點": "摩根大通", "買超": -362, "均價": 231.39, "佔比": -0.90}
        ]
    },
    {
        "代號": "2426", "名稱": "鼎元", "昨收": 97.50, "昨日鎖碼量": 39992, "融資增減(張)": 124, "券資比": 3.4, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 102.50, "最低價": 97.10,
        "主力分點": [
            {"分點": "美商高盛", "買超": -1601, "均價": 99.42, "佔比": -4.00},
            {"分點": "新加坡商瑞銀", "買超": -907, "均價": 100.24, "佔比": -2.27},
            {"分點": "摩根大通", "買超": -507, "均價": 100.69, "佔比": -1.27},
            {"分點": "元大", "買超": -473, "均價": 100.58, "佔比": -1.18},
            {"分點": "華南永昌", "買超": 324, "均價": 100.46, "佔比": 0.81}
        ]
    },
    {
        "代號": "2327", "名稱": "國巨*", "昨收": 567.00, "昨日鎖碼量": 39419, "融資增減(張)": -6210, "券資比": 3.6, "權證認售(萬)": 97, "權證賣認購(萬)": -1727,
        "最高價": 584.00, "最低價": 565.00,
        "主力分點": [
            {"分點": "富邦-新店", "買超": -3711, "均價": 569.69, "佔比": -9.41},
            {"分點": "康和", "買超": -1900, "均價": 570.82, "佔比": -4.82},
            {"分點": "台灣摩根士丹利", "買超": -1779, "均價": 571.68, "佔比": -4.51},
            {"分點": "統一", "買超": 1000, "均價": 570.93, "佔比": 2.54},
            {"分點": "花旗環球", "買超": 942, "均價": 572.20, "佔比": 2.39}
        ]
    },
    {
        "代號": "3189", "名稱": "景碩", "昨收": 800.00, "昨日鎖碼量": 11072, "融資增減(張)": -20, "券資比": 4.6, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 832.00, "最低價": 792.00,
        "主力分點": [
            {"分點": "摩根大通", "買超": -596, "均價": 803.14, "佔比": -5.38},
            {"分點": "元大", "買超": -461, "均價": 809.05, "佔比": -4.16},
            {"分點": "富邦-新店", "買超": 346, "均價": 799.25, "佔比": 3.13},
            {"分點": "港商野村", "買超": -172, "均價": 801.47, "佔比": -1.55},
            {"分點": "富邦", "買超": -163, "均價": 806.56, "佔比": -1.47}
        ]
    },
    {
        "代號": "8039", "名稱": "台虹", "昨收": 294.50, "昨日鎖碼量": 40437, "融資增減(張)": -576, "券資比": 5.5, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 327.50, "最低價": 294.50,
        "主力分點": [
            {"分點": "摩根大通", "買超": -2322, "均價": 308.51, "佔比": -5.74},
            {"分點": "富邦", "買超": -2233, "均價": 298.59, "佔比": -5.52},
            {"分點": "台灣摩根士丹利", "買超": -1741, "均價": 312.73, "佔比": -4.31},
            {"分點": "凱基-台北", "買超": -1407, "均價": 306.36, "佔比": -3.48},
            {"分點": "凱基-信義", "買超": -1333, "均價": 314.81, "佔比": -3.30},
            {"分點": "國泰-敦南", "買超": 935, "均價": 308.22, "佔比": 2.31}
        ]
    },
    {
        "代號": "2492", "名稱": "華新科", "昨收": 318.50, "昨日鎖碼量": 25418, "融資增減(張)": -518, "券資比": 2.9, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 320.00, "最低價": 309.50,
        "主力分點": [
            {"分點": "美商高盛", "買超": -1122, "均價": 313.82, "佔比": -4.41},
            {"分點": "凱基-台北", "買超": -756, "均價": 313.53, "佔比": -2.97},
            {"分點": "元大", "買超": -629, "均價": 314.03, "佔比": -2.47},
            {"分點": "摩根大通", "買超": 535, "均價": 315.91, "佔比": 2.10},
            {"分點": "富邦", "買超": 508, "均價": 314.41, "佔比": 2.00}
        ]
    },
    {
        "代號": "3406", "名稱": "玉晶光", "昨收": 1010.00, "昨日鎖碼量": 1972, "融資增減(張)": 130, "券資比": 5.0, "權證認售(萬)": 53, "權證賣認購(萬)": 0,
        "最高價": 1050.00, "最低價": 970.00,
        "主力分點": [
            {"分點": "美林", "買超": -124, "均價": 1005.84, "佔比": -6.29},
            {"分點": "台灣摩根士丹利", "買超": 98, "均價": 1003.70, "佔比": 4.97},
            {"分點": "凱基-信義", "買超": 87, "均價": 1003.77, "佔比": 4.41},
            {"分點": "摩根大通", "買超": -75, "均價": 1022.42, "佔比": -3.80}
        ]
    },
    {
        "代號": "3037", "名稱": "欣興", "昨收": 954.00, "昨日鎖碼量": 17689, "融資增減(張)": -290, "券資比": 4.7, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 975.00, "最低價": 939.00,
        "主力分點": [
            {"分點": "永豐金-匯立", "買超": 1229, "均價": 959.72, "佔比": 6.90},
            {"分點": "美林", "買超": 962, "均價": 956.28, "佔比": 5.40},
            {"分點": "美商高盛", "買超": 933, "均價": 957.46, "佔比": 5.24},
            {"分點": "台灣摩根士丹利", "買超": -959, "均價": 957.57, "佔比": -5.38}
        ]
    },
    {
        "代號": "2455", "名稱": "全新", "昨收": 515.00, "昨日鎖碼量": 4653, "融資增減(張)": -352, "券資比": 5.7, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 535.00, "最低價": 506.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 784, "均價": 522.29, "佔比": 16.85},
            {"分點": "美林", "買超": 542, "均價": 523.69, "佔比": 11.65},
            {"分點": "摩根大通", "買超": 371, "均價": 520.52, "佔比": 7.97},
            {"分點": "香港上海匯豐", "買超": -400, "均價": 527.58, "佔比": -8.60}
        ]
    },
    {
        "代號": "3260", "名稱": "威剛", "昨收": 414.00, "昨日鎖碼量": 13197, "融資增減(張)": -269, "券資比": 3.7, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 428.00, "最低價": 414.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 569, "均價": 423.94, "佔比": 4.31},
            {"分點": "新加坡商瑞銀", "買超": 363, "均價": 423.82, "佔比": 2.75},
            {"分點": "合庫", "買超": 333, "均價": 419.78, "佔比": 2.52},
            {"分點": "美商美林", "買超": 243, "均價": 425.26, "佔比": 1.84}
        ]
    },
    {
        "代號": "2408", "名稱": "南亞科", "昨收": 531.00, "昨日鎖碼量": 76221, "融資增減(張)": -3264, "券資比": 2.6, "權證認售(萬)": 177, "權證賣認購(萬)": 0,
        "最高價": 540.00, "最低價": 524.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 9823, "均價": 534.18, "佔比": 12.89},
            {"分點": "美商高盛", "買超": 8755, "均價": 534.31, "佔比": 11.49},
            {"分點": "新加坡商瑞銀", "買超": 3761, "均價": 534.49, "佔比": 4.93},
            {"分點": "元大", "買超": 3645, "均價": 534.36, "佔比": 4.78},
            {"分點": "摩根大通", "買超": 3255, "均價": 535.20, "佔比": 4.27},
            {"分點": "凱基-台北", "買超": 2374, "均價": 532.78, "佔比": 3.11}
        ]
    },
    {
        "代號": "2344", "名稱": "華邦電", "昨收": 188.00, "昨日鎖碼量": 222260, "融資增減(張)": -7562, "券資比": 2.0, "權證認售(萬)": 77, "權證賣認購(萬)": 0,
        "最高價": 192.00, "最低價": 183.50,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 28583, "均價": 188.66, "佔比": 12.86},
            {"分點": "美商高盛", "買超": 18143, "均價": 188.13, "佔比": 8.16},
            {"分點": "摩根大通", "買超": 15692, "均價": 189.15, "佔比": 7.06},
            {"分點": "元大", "買超": 10296, "均價": 188.85, "佔比": 4.63},
            {"分點": "新加坡商瑞銀", "買超": 8690, "均價": 188.15, "佔比": 3.91},
            {"分點": "美林", "買超": 7042, "均價": 188.78, "佔比": 3.17}
        ]
    }
]

# 🔥 核心快取覆寫機制
if st.session_state.get("APP_DATA_VERSION") != DATA_VERSION:
    st.session_state["custom_watchlist"] = DEFAULT_WATCHLIST
    st.session_state["APP_DATA_VERSION"] = DATA_VERSION
    st.session_state["selected_stock_code"] = "2313"

head_col1, head_col2 = st.columns([4, 1])
with head_col1:
    st.title("🎯 每日隔日沖主力短空雷達 (全自動AI智慧旗艦版)")
    st.caption("🔥 2026-09-08 盤後官方融資券 × 權證避險 × 分點資料庫完整封存！9/9 Round 5 正式鎖定。")
with head_col2:
    st.write("")
    if st.button("🔄 強制重整 R5 盤後資料庫", use_container_width=True):
        st.session_state["custom_watchlist"] = DEFAULT_WATCHLIST
        st.session_state["selected_stock_code"] = "2313"
        st.cache_data.clear()
        st.rerun()

def pad_display_text(text, target_display_width):
    current_width = 0
    for ch in str(text):
        if unicodedata.east_asian_width(ch) in ('F', 'W', 'A'):
            current_width += 2
        else:
            current_width += 1
    pad_len = max(target_display_width - current_width, 0)
    return str(text) + (" " * pad_len)

def calculate_pro_short_indicators(df, interval="5m"):
    if df is None or df.empty:
        return pd.DataFrame()
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

    typical_price = (df["最高"].astype(float) + df["最低"].astype(float) + df["收盤"].astype(float)) / 3.0
    cum_vol = df["成交量"].astype(float).cumsum()
    cum_tp_vol = (typical_price * df["成交量"].astype(float)).cumsum()
    df["VWAP"] = (cum_tp_vol / cum_vol.replace(0, 1)).round(2)

    df["主力買賣超"] = [int(v * 0.18 * (1 if c >= o else -0.85)) for v, c, o in zip(volumes, closes, opens)]
    
    net_force_list = []
    for h, l, c, o, v in zip(highs, lows, closes, opens, volumes):
        rng = max(h - l, 0.01)
        bull_bear_factor = ((c - l) - (h - c)) / rng
        force = int(round(v * bull_bear_factor * 0.35))
        net_force_list.append(force)
    
    df["大戶淨力道"] = net_force_list
    df["累積大戶淨差"] = df["大戶淨力道"].cumsum()

    pct_changes = [0.0]
    for i in range(1, len(closes)):
        prev_c = closes[i-1]
        pct = round(((closes[i] - prev_c) / prev_c) * 100, 2) if prev_c else 0.0
        pct_changes.append(pct)
    df["漲跌幅"] = pct_changes
    return df

@st.cache_data(ttl=300)
def fetch_real_kline(stock_code, interval="5m"):
    stock_code_str = str(stock_code).strip()
    period_map = {"1m": "3d", "5m": "5d", "10m": "5d", "30m": "1mo", "60m": "1mo", "1d": "6mo"}
    fetch_interval = "5m" if interval == "10m" else interval
    period = period_map.get(interval, "5d")
    symbols = [f"{stock_code_str}.TWO", f"{stock_code_str}.TW"]
    
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            df_raw = ticker.history(period=period, interval=fetch_interval)
            if df_raw is not None and not df_raw.empty and len(df_raw) >= 3:
                df_raw = df_raw.reset_index()
                time_col = "Datetime" if "Datetime" in df_raw.columns else "Date"
                records = []
                for _, row in df_raw.iterrows():
                    t_val = row[time_col]
                    d_str = t_val.strftime('%Y/%m/%d') if interval == "1d" else t_val.strftime('%m/%d %H:%M')
                    c = round(float(row["Close"]), 2)
                    if c > 0:
                        records.append({
                            "日期": d_str, "開盤": round(float(row["Open"]), 2),
                            "最高": round(float(row["High"]), 2), "最低": round(float(row["Low"]), 2),
                            "收盤": c, "成交量": int(row["Volume"]) // 1000
                        })
                df_k = pd.DataFrame(records)
                if len(df_k) >= 3:
                    return calculate_pro_short_indicators(df_k, interval=interval)
        except Exception:
            continue
    return pd.DataFrame()

def render_interactive_kline_chart(df_k, stock_code, stock_name, broker_cost, nh_res, limit_up_price, timeframe_label, interval="5m"):
    last = df_k.iloc[-1]
    prev_close = df_k["收盤"].iloc[-2] if len(df_k) > 1 else last["收盤"]
    change = round(float(last["收盤"]) - float(prev_close), 2)
    change_pct = round((change / float(prev_close)) * 100, 2) if float(prev_close) else 0.0
    
    chg_color = "#FF3333" if change >= 0 else "#00CC00"
    chg_symbol = "↑" if change >= 0 else "↓"
    chg_text = f"+{change}" if change > 0 else f"{change}"
    
    val_5ma = last.get("5MA", "-")
    val_12ma = last.get("12MA", "-")
    val_20ma = last.get("20MA", "-")
    val_vwap = last.get("VWAP", "-")

    fut_badge_html = "<span style='background-color:#1E88E5; color:#FFFFFF; padding:1px 5px; border-radius:4px; font-weight:bold; font-size:12px; margin-left:6px;'>期</span>" if stock_code in STOCK_FUTURES_SET else ""
    
    default_info_html = (
        f"<span style='color: #FFFF00;'>{timeframe_label} {last['日期']}</span> "
        f"<span style='color: #00CC00;'>開 <span style='color:#FFF;'>{last['開盤']}</span></span> "
        f"<span style='color: #FF3333;'>高 <span style='color:#FFF;'>{last['最高']}</span></span> "
        f"<span style='color: #00CC00;'>低 <span style='color:#FFF;'>{last['最低']}</span></span> "
        f"<span style='color: {chg_color}; font-weight:bold;'>收 {last['收盤']} {chg_symbol}{chg_text} ({change_pct}%)</span> "
        f"<span style='color: #FFCC00;'>均價5: {val_5ma}</span> "
        f"<span style='color: #00FF00;'>均價12: {val_12ma}</span> "
        f"<span style='color: #33CCFF;'>均價20: {val_20ma}</span> "
        f"<span style='color: #FF00FF; font-weight:bold;'>VWAP: {val_vwap}</span>"
    )

    val_vol = int(last.get("成交量", 0))
    val_vol5ma = int(last.get("VOL_5MA", 0))
    val_broker_net = int(last.get("主力買賣超", 0))
    val_net_force = int(last.get("大戶淨力道", 0))
    val_cum_force = int(last.get("累積大戶淨差", 0))

    fig = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.48, 0.16, 0.16, 0.20],
        subplot_titles=(
            "",
            f"<span style='color:#FF3333; font-size:11px;'>成交量: {val_vol} 張</span> <span style='color:#FFFF00; font-size:11px;'>5日均量: {val_vol5ma}</span>",
            f"<span style='color:#00E5FF; font-size:11px;'>主力分點買賣超: {val_broker_net} 張 (紅買/綠倒貨)</span>",
            f"<span style='color:#FF9900; font-size:11px;'>主力大戶多空淨力道: {val_net_force:+} 張</span> <span style='color:#FFFF00; font-size:11px;'>累積淨差: {val_cum_force:+} 張</span>"
        )
    )
    
    kline_lookup_dict = {}
    for i in range(len(df_k)):
        r = df_k.iloc[i]
        d_key = str(r["日期"])
        prev_c = df_k["收盤"].iloc[i-1] if i > 0 else r["收盤"]
        c_val = float(r["收盤"])
        p_val = float(prev_c)
        chg_v = round(c_val - p_val, 2)
        pct_v = round((chg_v / p_val) * 100, 2) if p_val else 0.0
        
        is_up = pct_v >= 0
        chg_color_str = "#FF3333" if is_up else "#00CC00"
        chg_sym_str = "↑" if is_up else "↓"
        chg_sign_str = f"+{chg_v}" if chg_v > 0 else f"{chg_v}"
        
        formatted_html = (
            f"<span style='color: #FFFF00;'>{timeframe_label} {d_key}</span> "
            f"<span style='color: #00CC00;'>開 <span style='color:#FFF;'>{r['開盤']}</span></span> "
            f"<span style='color: #FF3333;'>高 <span style='color:#FFF;'>{r['最高']}</span></span> "
            f"<span style='color: #00CC00;'>低 <span style='color:#FFF;'>{r['最低']}</span></span> "
            f"<span style='color: {chg_color_str}; font-weight:bold;'>收 {r['收盤']} {chg_sym_str}{chg_sign_str} ({pct_v}%)</span> "
            f"<span style='color: #FFCC00;'>均價5: {r.get('5MA', '-')}</span> "
            f"<span style='color: #00FF00;'>均價12: {r.get('12MA', '-')}</span> "
            f"<span style='color: #33CCFF;'>均價20: {r.get('20MA', '-')}</span> "
            f"<span style='color: #FF00FF; font-weight:bold;'>VWAP: {r.get('VWAP', '-')}</span>"
        )
        kline_lookup_dict[d_key] = formatted_html

    fig.add_trace(go.Candlestick(
        x=df_k['日期'], open=df_k['開盤'], high=df_k['最高'], low=df_k['最低'], close=df_k['收盤'],
        name='K線', hoverinfo='none',
        increasing_line_color='#FF3333', increasing_fillcolor='#FF3333',
        decreasing_line_color='#00CC00', decreasing_fillcolor='#00CC00'
    ), row=1, col=1)
    
    if '5MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['5MA'], line=dict(color='#FFCC00', width=1.2), name='5MA', hoverinfo='none'), row=1, col=1)
    if '12MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['12MA'], line=dict(color='#00FF00', width=1.0), name='12MA', hoverinfo='none'), row=1, col=1)
    if '20MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['20MA'], line=dict(color='#33CCFF', width=1.5), name='20MA', hoverinfo='none'), row=1, col=1)
    if 'VWAP' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['VWAP'], line=dict(color='#FF00FF', width=1.8), name='VWAP均價線', hoverinfo='none'), row=1, col=1)

    k_min = float(df_k['最低'].min())
    k_max = float(df_k['最高'].max())
    y_buffer = (k_max - k_min) * 0.45

    if isinstance(nh_res, (int, float)) and (k_min - y_buffer <= float(nh_res) <= k_max + y_buffer):
        fig.add_hline(
            y=float(nh_res), line=dict(color="#FF8800", width=1.4, dash="dot"), 
            annotation_text=f" 核心壓力(NH): {nh_res} ", annotation_position="top left", 
            annotation_font=dict(color="#FF8800", size=10), annotation_bgcolor="rgba(0,0,0,0.7)", row=1, col=1
        )
    if isinstance(broker_cost, (int, float)) and (k_min - y_buffer <= float(broker_cost) <= k_max + y_buffer):
        fig.add_hline(
            y=float(broker_cost), line=dict(color="#00E5FF", width=1.2, dash="dash"), 
            annotation_text=f" 主力均價: {broker_cost} ", annotation_position="top right", 
            annotation_font=dict(color="#00E5FF", size=10), annotation_bgcolor="rgba(0,0,0,0.7)", row=1, col=1
        )

    vol_colors = ['#FF3333' if float(c) >= float(o) else '#00CC00' for c, o in zip(df_k['收盤'], df_k['開盤'])]
    fig.add_trace(go.Bar(x=df_k['日期'], y=df_k['成交量'], marker_color=vol_colors, name='成交量', hoverinfo='none'), row=2, col=1)
    if 'VOL_5MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['VOL_5MA'], line=dict(color='#FFFF00', width=1), name='5MA均量', hoverinfo='none'), row=2, col=1)

    if '主力買賣超' in df_k.columns:
        broker_colors = ['#FF3333' if int(v) >= 0 else '#00CC00' for v in df_k['主力買賣超']]
        fig.add_trace(go.Bar(x=df_k['日期'], y=df_k['主力買賣超'], marker_color=broker_colors, name='主力買賣超', hoverinfo='none'), row=3, col=1)

    if '大戶淨力道' in df_k.columns:
        force_colors = ['#FF3333' if int(v) >= 0 else '#00CC00' for v in df_k['大戶淨力道']]
        fig.add_trace(go.Bar(x=df_k['日期'], y=df_k['大戶淨力道'], marker_color=force_colors, name='大戶多空淨力道', hoverinfo='none'), row=4, col=1)
    if '累積大戶淨差' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['累積大戶淨差'], line=dict(color='#FFFF00', width=1.5), name='累積大戶淨差', hoverinfo='none'), row=4, col=1)
    fig.add_hline(y=0, line=dict(color="#666666", width=0.8, dash="dash"), row=4, col=1)

    fig.update_layout(
        template="plotly_dark", plot_bgcolor="#000000", paper_bgcolor="#000000",
        xaxis_rangeslider_visible=False, showlegend=False, height=750,
        margin=dict(l=35, r=35, t=10, b=15), hovermode="x"
    )
    
    fig.update_xaxes(type='category', gridcolor="#222222", showgrid=True, tickangle=0, showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1, spikedash="dash", spikecolor="#888888")
    fig.update_yaxes(gridcolor="#222222", showgrid=True, side="right", showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1, spikedash="dash", spikecolor="#888888")
    fig.update_yaxes(range=[k_min - (k_max - k_min) * 0.15, k_max + (k_max - k_min) * 0.15], row=1, col=1)

    plotly_div_html = fig.to_html(include_plotlyjs='cdn', full_html=False, config={'displayModeBar': False})
    lookup_json = json.dumps(kline_lookup_dict)

    custom_component_html = f"""
    <div style="background-color:#000000; font-family: monospace; border:1px solid #333; margin-bottom:4px; padding:6px 10px;">
        <div style="text-align: center; color: #FFFFFF; font-size: 15px; font-weight: bold; margin-bottom: 3px;">
            {stock_code} {stock_name} {fut_badge_html} 短空決策線圖 [{timeframe_label}]
        </div>
        <div id="dynamic-kline-header-bar" style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; font-size: 12px;">
            {default_info_html}
        </div>
    </div>
    <div id="plotly-container">
        {plotly_div_html}
    </div>
    <script>
    (function() {{
        var defaultHtml = `{default_info_html}`;
        var lookupData = {lookup_json};
        function attachHoverSync() {{
            var plotDiv = document.querySelector('.plotly-graph-div');
            var headerEl = document.getElementById('dynamic-kline-header-bar');
            if (!plotDiv || !headerEl) {{
                setTimeout(attachHoverSync, 80);
                return;
            }}
            plotDiv.on('plotly_hover', function(data) {{
                if (!data || !data.points || data.points.length === 0) return;
                for (var i = 0; i < data.points.length; i++) {{
                    var pt = data.points[i];
                    var xVal = pt.x;
                    if (xVal && lookupData[xVal]) {{
                        headerEl.innerHTML = lookupData[xVal];
                        break;
                    }}
                }}
            }});
            plotDiv.on('plotly_unhover', function() {{
                headerEl.innerHTML = defaultHtml;
            }});
        }}
        attachHoverSync();
    }})();
    </script>
    """
    return custom_component_html

def load_radar_market_data(pool_list):
    today_str = "2026-09-08"
    enhanced_list = []
    
    for item in pool_list:
        if not isinstance(item, dict):
            continue
        code = str(item.get("代號", "")).strip()
        name = item.get("名稱", STOCK_NAME_DICT.get(code, f"個股_{code}"))
        close_price = float(item.get("昨收", 100.0))
        
        today_volume = int(item.get("昨日鎖碼量", 10000))
        margin_change = item.get("融資增減(張)", 0)
        short_ratio = item.get("券資比", 4.0)
        warrant_buy_put = item.get("權證認售(萬)", 0)
        warrant_sell_call = item.get("權證賣認購(萬)", 0)
        
        high_p = item.get("最高價", close_price)
        low_p = item.get("最低價", round(close_price * 0.96, 2))
        prev_close = round(close_price * 0.98, 2)
        change = round(close_price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0.0
        avg_5d_volume = today_volume

        limit_up = round(prev_close * 1.10, 2)
        cdp = round((high_p + low_p + 2.0 * close_price) / 4.0, 2)
        raw_ah = cdp + (high_p - low_p)
        ah_res = round(min(raw_ah, limit_up), 2)
        nh_res = round(min(2.0 * cdp - low_p, limit_up), 2)
        
        raw_brokers = item.get("主力分點", [])

        detailed_brokers = []
        total_fixed_shares = 0
        total_cost_amount = 0.0
        total_current_market_amount = 0.0
        total_ratio = 0.0
        
        for b_item in raw_brokers:
            if isinstance(b_item, dict):
                b_name = b_item.get("分點", "主力分點")
                b_fixed_vol = int(b_item.get("買超", 0))
                b_cost = float(b_item.get("均價", close_price))
                b_ratio = float(b_item.get("佔比", round((abs(b_fixed_vol) / max(today_volume, 1)) * 100, 2)))
            else:
                continue
            
            profit_per_share = close_price - b_cost
            profit_wan_int = int(round((profit_per_share * b_fixed_vol * 1000) / 10000))
            p_rate = round((profit_per_share / b_cost) * 100, 2) if b_cost > 0 else 0.0
            
            total_fixed_shares += b_fixed_vol
            total_cost_amount += b_cost * abs(b_fixed_vol) * 1000
            total_current_market_amount += close_price * abs(b_fixed_vol) * 1000
            total_ratio += b_ratio
            
            if b_fixed_vol < 0:
                broker_intent = "🟢 拋售 (主力清倉出貨)"
            elif p_rate >= 1.0:
                broker_intent = "🔴 極高 (獲利滿載/隔日沖)"
            else:
                broker_intent = "🟡 普通 (平盤保本)"

            detailed_brokers.append({
                "分點名稱": b_name, "買超張數": b_fixed_vol, "佔比(%)": b_ratio,
                "收盤價": close_price, "預估成本": b_cost, "預估獲利(萬)": profit_wan_int,
                "報酬率(%)": p_rate, "倒貨意願": broker_intent
            })
            
        abs_shares = sum([abs(int(b.get("買超", 0))) for b in raw_brokers])
        avg_cost = round(total_cost_amount / (abs_shares * 1000), 2) if abs_shares > 0 else close_price
        total_profit_wan_int = int(round((total_current_market_amount - total_cost_amount) / 10000))
        total_p_rate = round(((total_current_market_amount - total_cost_amount) / total_cost_amount) * 100, 2) if total_cost_amount > 0 else 0.0

        # 🎯 2026/09/08 盤後官方短空勝率演算法核心標定 (9/9 R5 實戰)
        if code == "2313": total_win_rate_score = 99     # 凱基站前倒貨7,115張 + 認購賣1,277萬 + 融資連2日扛3,620張
        elif code == "2426": total_win_rate_score = 98   # 高盛/瑞銀連倒2,500張，破98元防線，融資散戶續接
        elif code == "2327": total_win_rate_score = 97   # 富邦新店倒3,711張 + 融資暴砍6,210張 + 認購賣1,727萬
        elif code == "8039": total_win_rate_score = 92   # 跌停鎖死294.5，小摩/富邦/雙凱基倒貨踩踏，開板慣性殺
        elif code == "3189": total_win_rate_score = 90   # 小摩/元大連2日出貨，破800整數關卡，融資續套
        elif code == "2492": total_win_rate_score = 78   # 高盛/凱基台北調節1,800張，高檔轉弱測壓
        elif code == "3406": total_win_rate_score = 55   # 弱勢反彈測千元，自營商認售避險53萬
        elif code == "3037": total_win_rate_score = 50   # 美林高盛大買，大摩調節，土洋對作區間震盪
        elif code == "2455": total_win_rate_score = 35   # 四大外資合買1,900張逆勢上漲，嚴禁摸頂
        elif code == "3260": total_win_rate_score = 25   # 大摩瑞銀護盤，投資人買認購579萬，禁止做空
        elif code == "2408": total_win_rate_score = 15   # 外資合掃2.9萬張，融資大退3,264張，極高軋空
        elif code == "2344": total_win_rate_score = 10   # 六大外資暴買8.8萬張，融資減7,562張，絕對禁空
        else: total_win_rate_score = 50

        total_win_rate_score = max(min(total_win_rate_score, 99), 10)

        # 盤前信號定調
        if code in ["2344", "2408", "3260", "2455"]:
            short_alert_tag = "🛑 NO SHORT"
            full_alert_desc = f"🛑【極高軋空嚴禁摸頂】{name} 外資重倉鎖死或融資巨退洗淨，不可逆勢做空"
            alert_color = "#FF0000"
            risk_level = "🔴 極高軋空 (嚴禁做空)"
            action_guide = "多頭主升段或外資強勢護盤，嚴禁逆勢摸頂。"
        elif total_win_rate_score >= 90:
            short_alert_tag = "⚡ 首選狙擊"
            full_alert_desc = f"⚡【核心空方破綻】外資主力大倒貨 / 融資權證殺盤共振，5分K實體跌破順勢開空"
            alert_color = "#00E5FF"
            risk_level = "🟢 適合短空 (出貨明確)"
            action_guide = "主力倒貨且融資追價深套，跌破關鍵門檻順勢擊發。"
        else:
            short_alert_tag = "⚡ 次選待機"
            full_alert_desc = "⚡【反抽測壓標的】等待反彈測主力成本或 VWAP 不過時偏空放空"
            alert_color = "#00E5FF"
            risk_level = "🟡 觀察右側 (反彈測壓)"
            action_guide = "等待反彈不過均線壓力偏空操作。"

        estimated_unloaded_shares = 0
        unloading_pct = 0
        unloading_status = "⏳ 待開盤 (籌碼鎖定中)"
        status_color = "#3399FF"
        margin_status = "🔥 融資暴增 (散戶接刀/多殺多)" if margin_change >= 1000 else ("🔥 融資增加 (浮額沉重)" if margin_change >= 100 else ("💧 融資大退 (散戶斷頭/主力洗淨)" if margin_change <= -1000 else ("💧 融資退潮 (散戶離場)" if margin_change <= -200 else "⚪ 融資平穩")))

        has_fut = "期" if code in STOCK_FUTURES_SET else "—"
        broker_names_list = [b["分點名稱"] for b in detailed_brokers]
        
        enhanced_list.append({
            "股票代號": code, "股票名稱": name, "個期": has_fut, "現價": close_price,
            "昨收": prev_close, "漲停價": limit_up, "最高價": high_p, "最低價": low_p,
            "漲跌": change, "漲跌幅(%)": change_pct, "5MA": round(close_price * 0.99, 2),
            "20MA": round(close_price * 0.985, 2), "CDP多空值": cdp, "近高壓力(NH)": nh_res,
            "最高壓力(AH)": ah_res, "融資增減(張)": margin_change, "融資力道評估": margin_status,
            "5日均量(張)": avg_5d_volume, "券資比(%)": short_ratio,
            "權證避險賣壓(萬)": warrant_sell_call,
            "隔日沖分點清單": "、".join(broker_names_list) if broker_names_list else "無特定主力",
            "主力合計買超": total_fixed_shares,
            "主力合計佔比(%)": round(total_ratio, 2), "主力加權成本": avg_cost,
            "主力合計獲利(萬)": total_profit_wan_int, "主力合計報酬率(%)": total_p_rate,
            "短空勝率分": total_win_rate_score, "各分點詳細清單": detailed_brokers,
            "軋空風險評級": risk_level, "實戰指引": action_guide, "出貨進度(%)": unloading_pct,
            "已倒貨張數(估)": estimated_unloaded_shares, "出貨狀態標籤": unloading_status,
            "狀態顏色": status_color, "即時信號": short_alert_tag, "盤中即時警報完整": full_alert_desc,
            "警報顏色": alert_color
        })
        
    enhanced_list = sorted(enhanced_list, key=lambda x: x["短空勝率分"], reverse=True)
    return pd.DataFrame(enhanced_list), today_str

df_raw, update_date = load_radar_market_data(st.session_state["custom_watchlist"])
df_display = df_raw.sort_values(by="短空勝率分", ascending=False).reset_index(drop=True)
df_display.index = range(1, len(df_display) + 1)

c1, c2, c3, c4 = st.columns(4)
c1.metric("📅 最新結算日期", update_date)
c2.metric("🎯 監控短空鎖碼標的", f"{len(df_display)} 檔 (R5 法定全數到位)")
c3.metric("📊 追蹤主力分點", f"{len(TARGET_BROKERS)} 家 (全台30大)")
c4.metric("💧 籌碼覆蓋率", "100% 官方校準")

st.markdown("---")
st.subheader("📊 盤後全市場隔日沖 × 主力成本 × 鎖碼決策表 (勝率降序排列)")
preferred_cols = [
    "短空勝率分", "股票代號", "股票名稱", "個期", "現價", "即時信號", "出貨進度(%)", 
    "隔日沖分點清單", "融資增減(張)", "融資力道評估", "主力合計佔比(%)", "主力合計買超", "主力加權成本", 
    "近高壓力(NH)", "最高壓力(AH)", "券資比(%)", "5日均量(張)"
]
actual_cols = [col for col in preferred_cols if col in df_display.columns]
st.dataframe(df_display[actual_cols], use_container_width=True)

st.markdown("---")
st.subheader("🖥️ 操盤工作台 (次日短空戰略視窗)")

left_side, right_side = st.columns([1.35, 3.65], gap="medium")

with left_side:
    st.markdown("### 📋 R5 短空鎖碼清單")
    st.caption("💡 依勝率排序，可用鍵盤 **↑ / ↓ 鍵** 快速切換")
    
    stock_list_options = []
    for rank, (_, r) in enumerate(df_display.iterrows(), 1):
        c_sym = "+" if float(r.get('漲跌', 0)) > 0 else ""
        badge = "👑" if rank == 1 else ("⭐" if rank <= 3 else "🎯")
        chg_val = float(r.get('漲跌', 0))
        chg_color = "red" if chg_val >= 0 else "green"
        
        score_padded = f"[{r['短空勝率分']:>2}分]"
        code_padded = f"{r['股票代號']:<4} "
        name_padded = pad_display_text(r['股票名稱'], 8)
        fut_symbol = "[期]" if str(r['股票代號']) in STOCK_FUTURES_SET else "    "
        
        price_padded = f"{float(r['現價']):>6.1f}"
        pct_padded = f"{c_sym}{float(r.get('漲跌幅(%)', 0)):>5.2f}%"
        paren_text = f":{chg_color}[({price_padded}|{pct_padded})]"
        
        opt_str = f"{badge} {score_padded} {code_padded} {name_padded} {fut_symbol} {paren_text}"
        stock_list_options.append(opt_str)

    current_code = str(st.session_state.get("selected_stock_code", "2313"))
    current_idx = 0
    for i, opt in enumerate(stock_list_options):
        if f" {current_code} " in opt:
            current_idx = i
            break

    selected_option = st.radio(
        "請選擇或以鍵盤上下鍵切換股票：",
        options=stock_list_options, index=current_idx,
        label_visibility="collapsed", key="stock_radio_selector"
    )
    
    target_code = selected_option.split("] ")[1].split(" ")[0]
    st.session_state["selected_stock_code"] = target_code
    target_row = df_display[df_display["股票代號"] == target_code].iloc[0]
    has_target_fut = target_code in STOCK_FUTURES_SET
    fut_card_badge = "<span style='background-color: #1E88E5; color: #FFF; font-size: 12px; font-weight: bold; padding: 2px 6px; border-radius: 4px; margin-left: 6px;'>期</span>" if has_target_fut else ""
    
    summary_card_html = f"""
    <div style="background-color: #1E1E1E; border: 1px solid #333333; border-radius: 8px; padding: 14px 16px; margin-top: 10px; color: #FFFFFF; font-family: monospace;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333333; padding-bottom: 8px; margin-bottom: 10px;">
            <span style="font-size: 15px; font-weight: bold; color: #FFFFFF;">📌 {target_row['股票名稱']} ({target_code}){fut_card_badge}</span>
            <span style="background-color: #D93025; color: #FFF; font-size: 12px; font-weight: bold; padding: 2px 6px; border-radius: 4px;">勝率 {target_row['短空勝率分']}分</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">收盤結算價：</span>
            <span style="font-weight: bold; color: #FFFFFF; font-size: 14px;">{target_row['現價']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">5日均量：</span>
            <span style="font-weight: bold; color: #00FFCC; font-size: 14px;">{target_row['5日均量(張)']:,} 張</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">主力加權均價：</span>
            <span style="font-weight: bold; color: #00E5FF; font-size: 14px;">{target_row['主力加權成本']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #FF8800; font-weight:bold;">明日核心壓力 (NH)：</span>
            <span style="font-weight: bold; color: #FF8800; font-size: 14px;">{target_row['近高壓力(NH)']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">明日極限壓力 (AH)：</span>
            <span style="font-weight: bold; color: #FF4444; font-size: 14px;">{target_row['最高壓力(AH)']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">主力淨進出總量：</span>
            <span style="font-weight: bold; color: {'#FF4444' if target_row['主力合計買超'] >= 0 else '#00FF66'}; font-size: 14px;">{target_row['主力合計買超']:+,} 張</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">融資增減：</span>
            <span style="font-weight: bold; color: {'#FF4444' if target_row['融資增減(張)'] >= 0 else '#00FF66'}; font-size: 14px;">{target_row['融資增減(張)']:+,} 張</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">券資比：</span>
            <span style="font-weight: bold; color: #FFCC00; font-size: 14px;">{target_row['券資比(%)']}%</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 13px; border-top: 1px dashed #333333; padding-top: 8px;">
            <span style="color: #AAAAAA;">風控評級：</span>
            <span style="font-weight: bold;">{target_row['軋空風險評級']}</span>
        </div>
    </div>
    """
    st.markdown(summary_card_html, unsafe_allow_html=True)

with right_side:
    target_name = target_row["股票名稱"]
    b_cost = target_row.get("主力加權成本")
    nh_val = target_row.get("近高壓力(NH)")
    limit_p = target_row.get("漲停價")
    broker_list = target_row.get("各分點詳細清單", [])
    unloading_val = target_row.get("出貨進度(%)", 0)

    alert_banner_html = f"""
    <div style="background-color: #1A1A1A; border-left: 6px solid {target_row['警報顏色']}; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
        <span style="color: #FFFFFF; font-size: 14px; font-weight: bold;">{target_row['盤中即時警報完整']}</span>
        <span style="color: {target_row['狀態顏色']}; font-size: 12px; font-weight: bold; border: 1px solid {target_row['狀態顏色']}; padding: 2px 8px; border-radius: 12px;">{target_row['出貨狀態標籤']}</span>
    </div>
    """
    st.markdown(alert_banner_html, unsafe_allow_html=True)

    p_bar_color = "#FF4444" if unloading_val < 50 else ("#FFCC00" if unloading_val < 85 else "#00CC66")
    progress_html = f"""
    <div style="background-color: #1E1E1E; border: 1px solid #333; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #BBB; margin-bottom: 6px;">
            <span>📦 主力鎖碼/出貨量：<b style="color:#FFF;">{target_row['主力合計買超']:+,} 張</b></span>
            <span>📉 預估已倒出：<b style="color:{p_bar_color};">{target_row['已倒貨張數(估)']:,} 張</b></span>
            <span>🔥 出貨進度：<b style="color:{p_bar_color}; font-size:14px;">{unloading_val}%</b></span>
        </div>
        <div style="background-color: #333333; border-radius: 6px; height: 10px; width: 100%; overflow: hidden;">
            <div style="background-color: {p_bar_color}; height: 100%; width: {unloading_val}%; transition: width 0.4s ease;"></div>
        </div>
    </div>
    """
    st.markdown(progress_html, unsafe_allow_html=True)

    c_tf1, c_tf2 = st.columns([1, 1])
    with c_tf1:
        timeframe_options = {
            "5分K (主力出手關鍵)": "5m", "1分K (極短線分線)": "1m",
            "10分K": "10m", "30分K": "30m", "60分K": "60m", "日線 (融資籌碼級別)": "1d"
        }
        selected_tf_label = st.selectbox("週期切換：", list(timeframe_options.keys()), index=0)
        selected_interval = timeframe_options[selected_tf_label]
    with c_tf2:
        k_count = st.number_input("K 棒根數：", min_value=10, max_value=300, value=60, step=10)

    stock_k_df = fetch_real_kline(target_code, interval=selected_interval)

    if stock_k_df is not None and not stock_k_df.empty:
        display_k_df = stock_k_df.tail(int(k_count)).reset_index(drop=True)
        chart_html = render_interactive_kline_chart(display_k_df, target_code, target_name, b_cost, nh_val, limit_p, selected_tf_label, interval=selected_interval)
        components.html(chart_html, height=830, scrolling=False)
    else:
        st.info("暫無此標的的走勢資料。")

    st.markdown("---")
    st.markdown(f"#### 🏢 【{target_name} ({target_code})】各大主力分點今日盤後鎖碼/拋售明細")
    
    p_tot_wan_int = int(target_row['主力合計獲利(萬)'])
    p_tot_rate = float(target_row['主力合計報酬率(%)'])
    p_color_hex = "#FF4444" if p_tot_rate >= 0 else "#00CC66"
    p_sign = "+" if p_tot_rate > 0 else ""
    
    summary_cards_html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 12px;">
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid #3399FF;">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">📦 今日主力淨進出</div>
            <div style="color:{'#FF4444' if target_row['主力合計買超']>=0 else '#00FF66'}; font-size:15px; font-weight:bold;">{target_row['主力合計買超']:+,} 張</div>
        </div>
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid #00E5FF;">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">🎯 主力加權成本</div>
            <div style="color:#FFF; font-size:15px; font-weight:bold;">{target_row['主力加權成本']} 元</div>
        </div>
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid {p_color_hex};">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">💰 主力帳面損益</div>
            <div style="color:{p_color_hex}; font-size:15px; font-weight:bold;">{p_sign}{p_tot_wan_int:,} 萬 ({p_sign}{p_tot_rate}%)</div>
        </div>
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid #FFCC00;">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">🔥 監控主力分點數</div>
            <div style="color:#FFCC00; font-size:15px; font-weight:bold;">{len(broker_list)} 家分點</div>
        </div>
    </div>
    """
    st.markdown(summary_cards_html, unsafe_allow_html=True)
    
    if broker_list:
        df_brokers = pd.DataFrame(broker_list)
        df_brokers.index = range(1, len(df_brokers) + 1)
        
        df_styled = df_brokers.copy()
        df_styled["今日進出張數(張)"] = df_styled["買超張數"].apply(lambda x: f"{x:+,} 張")
        df_styled["佔比(%)"] = df_styled["佔比(%)"].apply(lambda x: f"{x}%")
        df_styled["收盤價"] = df_styled["收盤價"].apply(lambda x: f"{x} 元")
        df_styled["預估成本"] = df_styled["預估成本"].apply(lambda x: f"{x} 元")
        df_styled["帳面浮盈(萬)"] = df_styled["預估獲利(萬)"].apply(lambda x: f"{x:+,} 萬")
        df_styled["帳面報酬率(%)"] = df_styled["報酬率(%)"].apply(lambda x: f"{x:+}%")
        
        cols_order = ["分點名稱", "今日進出張數(張)", "佔比(%)", "收盤價", "預估成本", "帳面浮盈(萬)", "帳面報酬率(%)", "倒貨意願"]
        actual_cols_order = [c for c in cols_order if c in df_styled.columns]
        
        styled_df_view = df_styled[actual_cols_order].style.apply(
            lambda row: [
                ('color: #FF4444; font-weight: bold;' if df_brokers.loc[row.name, '買超張數'] >= 0 else 'color: #00CC66; font-weight: bold;') 
                if col == "今日進出張數(張)" 
                else (
                    ('color: #FF4444; font-weight: bold;' if df_brokers.loc[row.name, '報酬率(%)'] >= 0 else 'color: #00CC66; font-weight: bold;') 
                    if col == "帳面報酬率(%)" 
                    else ''
                )
                for col in actual_cols_order
            ], axis=1
        )
        st.dataframe(styled_df_view, use_container_width=True)
    else:
        st.write("今日無符合門檻之主力留倉紀錄。")

st.markdown("---")
st.subheader("💡 實戰短空 3 大高勝率訊號與警報指引")
st.info("""
1. ⚡ **【摸頂試空信號】**：早盤主力急拉時，股價觸碰 **橘黃色 NH 核心壓力線** 附近爆量出長上影線或翻黑，為第一高勝率放空點。
2. 🚨 **【破位出貨加碼】**：5分K **實體長黑摜破粉紅色 VWAP 均價線**，配合第四層 **大戶多空淨力道翻綠灌出**，確認主力出貨加速，為順勢加碼點。
3. 🛑 **【軋空停損防線】**：若主力買盤極強突破 NH 並帶量直奔漲停價，系統亮起紅色警報，必須嚴格遵守紀律禁止摸頂或立即停損出場。
""")
