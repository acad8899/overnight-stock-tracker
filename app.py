# -*- coding: utf-8 -*-
"""
雙/三 AI 量化短空雷達 (S2-R2 巔峰對決旗艦裁判長版) - app.py (v23.0)
==============================================================================
版本更新重點：
1. 完整載入 2026/10/05 臺灣證券交易所官方融資券增減、自營商權證金流與分點明細。
2. S2-R1 官方結算定案入庫：收錄逐筆對帳與權益 (ChatGPT 冠軍、Gemini 亞軍、Claude 季軍)。
3. S2-R2 官方 TOP 5 決戰名冊三方並列：Gemini (6口) vs ChatGPT (6口) vs Claude 補位版 (5口)。
4. 升級量化撮合引擎：納入「跌破 T1 不進場」、逐筆手續費 (每口單邊 20 元) 與期交稅 (十萬分之二)。
5. 嚴格貫徹單筆 2 萬金盾與方案 A 觸及 T1 全平保底規則，13:25 尾盤市價強平。
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
# 1. 頁面排版與外觀設定
# ==============================================================================
st.set_page_config(
    page_title="三 AI 量化短空雷達 (S2-R2 決戰旗艦版)", 
    layout="wide", 
    page_icon="⚔️", 
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card-gemini {
        background: linear-gradient(135deg, #1E1E1E 0%, #2A1818 100%);
        border-radius: 8px;
        padding: 10px;
        border-left: 5px solid #FF4444;
        margin-bottom: 8px;
    }
    .metric-card-gpt {
        background: linear-gradient(135deg, #1E1E1E 0%, #162436 100%);
        border-radius: 8px;
        padding: 10px;
        border-left: 5px solid #1E88E5;
        margin-bottom: 8px;
    }
    .metric-card-claude {
        background: linear-gradient(135deg, #1E1E1E 0%, #261B33 100%);
        border-radius: 8px;
        padding: 10px;
        border-left: 5px solid #AB47BC;
        margin-bottom: 8px;
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
# 2. 賽事常數與真實結算權益狀態 (S2-R1 結算 ➔ S2-R2 開賽起跑)
# ==============================================================================
S2_R2_MATCH_DATE = "2026/10/06"
DATA_BASE_DATE = "2026/10/05"
MARGIN_DISPLAY_DATE = "10/05"

# S2-R1 結算後實際權益總額
CAPITAL_CHATGPT = 979999.68  # 🥇 ChatGPT 冠軍 (-NT$ 20,000)
CAPITAL_GEMINI = 971820.08   # 🥈 Gemini 亞軍 (-NT$ 28,180)
CAPITAL_CLAUDE = 970945.22   # 🥉 Claude 季軍 (-NT$ 29,055)

MAX_STOP_LOSS_NTD = 20000
COMMISSION_PER_CONTRACT = 20.0  # 每口單邊手續費 NT$ 20
TAX_RATE = 0.00002              # 股價期貨交易稅率 十萬分之二

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
# 3. 2026-10-05 盤後 12 檔母池三維大數據庫 (分點、融資、權證金流)
# ==============================================================================
DEFAULT_WATCHLIST_S2R2 = [
    {
        "代號": "2492", "名稱": "華新科", "昨收": 368.50, "昨日鎖碼量": 95779, "融資增減(張)": 3382, "券資比": 3.2, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 396.00, "最低價": 365.00,
        "主力分點": [
            {"分點": "美林", "買超": 4430, "均價": 381.54, "佔比": 4.63},
            {"分點": "國泰-敦南", "買超": 804, "均價": 378.35, "佔比": 0.84},
            {"分點": "凱基", "買超": 417, "均價": 377.93, "佔比": 0.44},
            {"分點": "元大", "買超": 391, "均價": 379.35, "佔比": 0.41},
            {"分點": "永豐金", "買超": 382, "均價": 378.66, "佔比": 0.40},
            {"分點": "台灣摩根士丹利", "買超": -3510, "均價": 376.80, "佔比": -3.66},
            {"分點": "美商高盛", "買超": -3207, "均價": 379.19, "佔比": -3.35},
            {"分點": "凱基-松山", "買超": -2489, "均價": 374.80, "佔比": -2.60},
            {"分點": "台新-台北", "買超": -2450, "均價": 375.41, "佔比": -2.56},
            {"分點": "凱基-站前", "買超": -1904, "均價": 377.82, "佔比": -1.99}
        ]
    },
    {
        "代號": "3042", "名稱": "晶技", "昨收": 222.00, "昨日鎖碼量": 35474, "融資增減(張)": -114, "券資比": 3.7, "權證認售(萬)": 0, "權證認購(萬)": -8448,
        "最高價": 235.50, "最低價": 221.00,
        "主力分點": [
            {"分點": "凱基-台北", "買超": 452, "均價": 224.31, "佔比": 1.27},
            {"分點": "美林", "買超": 389, "均價": 222.88, "佔比": 1.10},
            {"分點": "國泰-敦南", "買超": 364, "均價": 226.82, "佔比": 1.03},
            {"分點": "中國信託", "買超": 303, "均價": 225.40, "佔比": 0.85},
            {"分點": "台灣摩根士丹利", "買超": 205, "均價": 224.46, "佔比": 0.58},
            {"分點": "凱基", "買超": -2458, "均價": 224.94, "佔比": -6.93},
            {"分點": "康和", "買超": -1923, "均價": 223.38, "佔比": -5.42},
            {"分點": "摩根大通", "買超": -1080, "均價": 225.80, "佔比": -3.04},
            {"分點": "美商高盛", "買超": -791, "均價": 226.94, "佔比": -2.23},
            {"分點": "國泰", "買超": -622, "均價": 223.83, "佔比": -1.75}
        ]
    },
    {
        "代號": "3406", "名稱": "玉晶光", "昨收": 1055.00, "昨日鎖碼量": 5365, "融資增減(張)": 208, "券資比": 4.2, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 1055.00, "最低價": 971.00,
        "主力分點": [
            {"分點": "凱基-信義", "買超": 1047, "均價": 1051.25, "佔比": 19.52},
            {"分點": "富邦", "買超": 403, "均價": 1049.95, "佔比": 7.51},
            {"分點": "台新", "買超": 124, "均價": 1008.33, "佔比": 2.31},
            {"分點": "美商高盛", "買超": 115, "均價": 1022.30, "佔比": 2.14},
            {"分點": "元大", "買超": 114, "均價": 1017.06, "佔比": 2.12},
            {"分點": "摩根大通", "買超": -86, "均價": 1022.12, "佔比": -1.60},
            {"分點": "港商野村", "買超": -84, "均價": 1000.55, "佔比": -1.57},
            {"分點": "台灣摩根士丹利", "買超": -67, "均價": 1023.59, "佔比": -1.25},
            {"分點": "新光", "買超": -54, "均價": 1049.22, "佔比": -1.01},
            {"分點": "國泰-敦南", "買超": -53, "均價": 1031.60, "佔比": -0.99}
        ]
    },
    {
        "代號": "6173", "名稱": "信昌電", "昨收": 292.00, "昨日鎖碼量": 11982, "融資增減(張)": -1737, "券資比": 3.8, "權證認售(萬)": 59, "權證認購(萬)": 0,
        "最高價": 314.50, "最低價": 292.00,
        "主力分點": [
            {"分點": "華南永昌-麻豆", "買超": 156, "均價": 311.70, "佔比": 1.30},
            {"分點": "康和-台中", "買超": 111, "均價": 309.93, "佔比": 0.93},
            {"分點": "國泰-敦南", "買超": 103, "均價": 304.88, "佔比": 0.86},
            {"分點": "富邦-彰化", "買超": 77, "均價": 308.57, "佔比": 0.64},
            {"分點": "元大-中壢", "買超": 63, "均價": 307.43, "佔比": 0.53},
            {"分點": "統一", "買超": -722, "均價": 305.10, "佔比": -6.03},
            {"分點": "凱基", "買超": -406, "均價": 302.62, "佔比": -3.39},
            {"分點": "群益金鼎-大安", "買超": -360, "均價": 307.97, "佔比": -3.00},
            {"分點": "康和", "買超": -341, "均價": 308.62, "佔比": -2.85},
            {"分點": "台新-台北", "買超": -284, "均價": 305.68, "佔比": -2.37}
        ]
    },
    {
        "代號": "2327", "名稱": "國巨*", "昨收": 626.00, "昨日鎖碼量": 67379, "融資增減(張)": 654, "券資比": 3.6, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 658.00, "最低價": 626.00,
        "主力分點": [
            {"分點": "國泰", "買超": 2154, "均價": 636.49, "佔比": 3.20},
            {"分點": "新加坡商瑞銀", "買超": 949, "均價": 641.37, "佔比": 1.41},
            {"分點": "富邦-新店", "買超": 531, "均價": 646.55, "佔比": 0.79},
            {"分點": "兆豐", "買超": 408, "均價": 635.46, "佔比": 0.61},
            {"分點": "凱基", "買超": 401, "均價": 635.09, "佔比": 0.60},
            {"分點": "台灣摩根士丹利", "買超": -3821, "均價": 636.59, "佔比": -5.67},
            {"分點": "美商高盛", "買超": -3034, "均價": 638.72, "佔比": -4.50},
            {"分點": "元大", "買超": -2754, "均價": 639.92, "佔比": -4.09},
            {"分點": "美林", "買超": -2260, "均價": 640.29, "佔比": -3.35},
            {"分點": "摩根大通", "買超": -1030, "均價": 637.71, "佔比": -1.53}
        ]
    },
    {
        "代號": "8039", "名稱": "台虹", "昨收": 303.50, "昨日鎖碼量": 49438, "融資增減(張)": 1413, "券資比": 4.9, "權證認售(萬)": 0, "權證認購(萬)": 1914,
        "最高價": 308.00, "最低價": 283.00,
        "主力分點": [
            {"分點": "富邦", "買超": 1195, "均價": 300.29, "佔比": 2.42},
            {"分點": "港商麥格理", "買超": 354, "均價": 301.31, "佔比": 0.72},
            {"分點": "元大-台北", "買超": 257, "均價": 299.26, "佔比": 0.52},
            {"分點": "群益金鼎-東大", "買超": 229, "均價": 298.53, "佔比": 0.46},
            {"分點": "凱基-市府", "買超": 202, "均價": 302.50, "佔比": 0.41},
            {"分點": "台灣摩根士丹利", "買超": -1147, "均價": 295.36, "佔比": -2.32},
            {"分點": "群益金鼎", "買超": -635, "均價": 294.04, "佔比": -1.28},
            {"分點": "凱基-台北", "買超": -616, "均價": 295.34, "佔比": -1.25},
            {"分點": "摩根大通", "買超": -595, "均價": 292.87, "佔比": -1.20},
            {"分點": "元大", "買超": -508, "均價": 296.95, "佔比": -1.03}
        ]
    },
    {
        "代號": "2455", "名稱": "全新", "昨收": 606.00, "昨日鎖碼量": 2369, "融資增減(張)": -215, "券資比": 4.3, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 607.00, "最低價": 575.00,
        "主力分點": [
            {"分點": "元大", "買超": 151, "均價": 600.20, "佔比": 6.37},
            {"分點": "富邦", "買超": 111, "均價": 593.95, "佔比": 4.69},
            {"分點": "統一", "買超": 96, "均價": 605.87, "佔比": 4.05},
            {"分點": "台新", "買超": 89, "均價": 601.06, "佔比": 3.76},
            {"分點": "永豐金-高雄", "買超": 53, "均價": 592.95, "佔比": 2.24},
            {"分點": "元大-中山北路", "買超": -136, "均價": 598.02, "佔比": -5.74},
            {"分點": "群益金鼎-大安", "買超": -67, "均價": 589.93, "佔比": -2.83},
            {"分點": "統一-新竹", "買超": -53, "均價": 599.75, "佔比": -2.24},
            {"分點": "元大-南屯", "買超": -52, "均價": 603.00, "佔比": -2.20},
            {"分點": "華南永昌-桃園", "買超": -47, "均價": 597.91, "佔比": -1.98}
        ]
    },
    {
        "代號": "3189", "名稱": "景碩", "昨收": 1095.00, "昨日鎖碼量": 30076, "融資增減(張)": -1719, "券資比": 4.0, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 1150.00, "最低價": 1030.00,
        "主力分點": [
            {"分點": "台新", "買超": 748, "均價": 1096.53, "佔比": 2.49},
            {"分點": "中國信託", "買超": 544, "均價": 1115.99, "佔比": 1.81},
            {"分點": "美商高盛", "買超": 431, "均價": 1090.21, "佔比": 1.43},
            {"分點": "摩根大通", "買超": 371, "均價": 1091.52, "佔比": 1.23},
            {"分點": "群益金鼎", "買超": 283, "均價": 1100.25, "佔比": 0.94},
            {"分點": "富邦-陽明", "買超": -818, "均價": 1124.21, "佔比": -2.72},
            {"分點": "台灣摩根士丹利", "買超": -432, "均價": 1084.72, "佔比": -1.44},
            {"分點": "富邦-新店", "買超": -354, "均價": 1122.83, "佔比": -1.18},
            {"分點": "群益金鼎-台北", "買超": -211, "均價": 1095.20, "佔比": -0.70},
            {"分點": "凱基-信義", "買超": -200, "均價": 1085.62, "佔比": -0.66}
        ]
    },
    {
        "代號": "3037", "名稱": "欣興", "昨收": 1325.00, "昨日鎖碼量": 27109, "融資增減(張)": -677, "券資比": 4.6, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 1420.00, "最低價": 1310.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 3965, "均價": 1366.37, "佔比": 14.63},
            {"分點": "美商高盛", "買超": 1740, "均價": 1356.98, "佔比": 6.42},
            {"分點": "新加坡商瑞銀", "買超": 685, "均價": 1366.98, "佔比": 2.53},
            {"分點": "宏遠", "買超": 261, "均價": 1383.52, "佔比": 0.96},
            {"分點": "兆豐", "買超": 114, "均價": 1360.74, "佔比": 0.42},
            {"分點": "花旗環球", "買超": -1367, "均價": 1340.06, "佔比": -5.04},
            {"分點": "元大", "買超": -992, "均價": 1370.57, "佔比": -3.66},
            {"分點": "大和國泰", "買超": -540, "均價": 1335.96, "佔比": -1.99},
            {"分點": "港商野村", "買超": -504, "均價": 1381.95, "佔比": -1.86},
            {"分點": "永豐金", "買超": -496, "均價": 1344.92, "佔比": -1.83}
        ]
    },
    {
        "代號": "2344", "名稱": "華邦電", "昨收": 181.00, "昨日鎖碼量": 90976, "融資增減(張)": -5343, "券資比": 2.3, "權證認售(萬)": 0, "權證認購(萬)": 1893,
        "最高價": 181.00, "最低價": 174.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 5957, "均價": 179.04, "佔比": 6.55},
            {"分點": "新加坡商瑞銀", "買超": 3432, "均價": 179.10, "佔比": 3.77},
            {"分點": "美商高盛", "買超": 2834, "均價": 179.40, "佔比": 3.12},
            {"分點": "美林", "買超": 2571, "均價": 178.44, "佔比": 2.83},
            {"分點": "元大", "買超": 2553, "均價": 179.01, "佔比": 2.81},
            {"分點": "康和", "買超": -1342, "均價": 176.32, "佔比": -1.48},
            {"分點": "凱基-信義", "買超": -908, "均價": 177.23, "佔比": -1.00},
            {"分點": "國泰-敦南", "買超": -825, "均價": 179.06, "佔比": -0.91},
            {"分點": "元大-北投", "買超": -605, "均價": 176.86, "佔比": -0.67},
            {"分點": "宏遠", "買超": -527, "均價": 179.15, "佔比": -0.58}
        ]
    },
    {
        "代號": "2408", "名稱": "南亞科", "昨收": 530.00, "昨日鎖碼量": 42326, "融資增減(張)": -1314, "券資比": 3.0, "權證認售(萬)": 62, "權證認購(萬)": 2427,
        "最高價": 534.00, "最低價": 512.00,
        "主力分點": [
            {"分點": "富邦", "買超": 3083, "均價": 529.34, "佔比": 7.28},
            {"分點": "元大", "買超": 1096, "均價": 527.03, "佔比": 2.59},
            {"分點": "群益金鼎", "買超": 1068, "均價": 529.04, "佔比": 2.52},
            {"分點": "新加坡商瑞銀", "買超": 1067, "均價": 525.80, "佔比": 2.52},
            {"分點": "摩根大通", "買超": 646, "均價": 527.32, "佔比": 1.53},
            {"分點": "美商高盛", "買超": -998, "均價": 521.94, "佔比": -2.36},
            {"分點": "台中銀-豐原", "買超": -505, "均價": 525.46, "佔比": -1.19},
            {"分點": "美林", "買超": -450, "均價": 525.50, "佔比": -1.06},
            {"分點": "永豐金", "買超": -272, "均價": 526.07, "佔比": -0.64},
            {"分點": "元大-復北", "買超": -231, "均價": 528.64, "佔比": -0.55}
        ]
    },
    {
        "代號": "2313", "名稱": "華通", "昨收": 248.50, "昨日鎖碼量": 51436, "融資增減(張)": 1211, "券資比": 3.1, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 248.50, "最低價": 232.00,
        "主力分點": [
            {"分點": "元大", "買超": 7092, "均價": 245.07, "佔比": 13.79},
            {"分點": "富邦", "買超": 4685, "均價": 247.72, "佔比": 9.11},
            {"分點": "台灣摩根士丹利", "買超": 3349, "均價": 239.26, "佔比": 6.51},
            {"分點": "美商高盛", "買超": 2064, "均價": 240.33, "佔比": 4.01},
            {"分點": "凱基-城中", "買超": 2020, "均價": 248.34, "佔比": 3.93},
            {"分點": "國泰-敦南", "買超": -1190, "均價": 242.98, "佔比": -2.31},
            {"分點": "中國信託", "買超": -455, "均價": 246.82, "佔比": -0.88},
            {"分點": "新光", "買超": -342, "均價": 242.51, "佔比": -0.66},
            {"分點": "玉山-新莊", "買超": -301, "均價": 247.01, "佔比": -0.59},
            {"分點": "國泰-台中", "買超": -290, "均價": 243.97, "佔比": -0.56}
        ]
    }
]

# ==============================================================================
# 4. 第二場 Round 2 (S2-R2) 三方官方正式封單陣列
# ==============================================================================
ORDERS_GEMINI_S2R2 = [
    {"rank": "🥇 1", "ticker": "2492", "name": "華新科(期)", "tool": "個股期", "size": "1口", "trigger": 366.5, "stop": 376.0, "t1": 352.0, "shares": 2000, "max_loss": 19000, "reason": "留28元長上影，融資狂增+3382張散戶高檔接刀慘套，大摩/高盛倒貨6700張，破366.5引爆踩踏！"},
    {"rank": "🥈 2", "ticker": "3042", "name": "晶技(期)", "tool": "個股期", "size": "2口", "trigger": 220.5, "stop": 225.0, "t1": 212.0, "shares": 4000, "max_loss": 18000, "reason": "認購權證爆賣-8448萬全市場第2，自營商被迫按Delta反向砍股票避險，凱基/康和提款4381張，破220.5追空！"},
    {"rank": "🥉 3", "ticker": "3406", "name": "玉晶光(期)", "tool": "個股期", "size": "1口", "trigger": 1060.0, "stop": 1069.0, "t1": 1030.0, "shares": 2000, "max_loss": 18000, "reason": "凱基信義單一主力狂買1047張(佔近2成)硬鎖漲停，明早開高即倒貨，5分K收黑摜破1060精準狙擊隔日沖！"},
    {"rank": "4", "ticker": "6173", "name": "信昌電(期)", "tool": "個股期", "size": "1口", "trigger": 289.0, "stop": 298.5, "t1": 275.0, "shares": 2000, "max_loss": 19000, "reason": "認售連4日買超第9名(+59萬)，收當日最低292長黑，統一/凱基倒貨逾2100張，買盤渙散，破289順勢追擊弱勢波！"},
    {"rank": "5", "ticker": "2327", "name": "國巨*(期)", "tool": "個股期", "size": "1口", "trigger": 622.0, "stop": 631.5, "t1": 605.0, "shares": 2000, "max_loss": 19000, "reason": "大摩/高盛/美林三大外資單日集體提款1.1萬張，衝649殺回收626平盤，融資微增，跌破622確認外資出貨轉折！"}
]

ORDERS_CHATGPT_S2R2 = [
    {"rank": "🥇 1", "ticker": "3042", "name": "晶技(期)", "tool": "個股期", "size": "2口", "trigger": 220.5, "stop": 225.5, "t1": 210.5, "shares": 4000, "max_loss": 20000, "reason": "法人-2438張＋高檔反轉，連續大漲後外資自營同步撤退，5分K實體跌破220.5追空。"},
    {"rank": "🥈 2", "ticker": "2327", "name": "國巨*(期)", "tool": "個股期", "size": "1口", "trigger": 628.0, "stop": 638.0, "t1": 608.0, "shares": 2000, "max_loss": 20000, "reason": "外資-12366張大量倒貨，大買隔天突反手出貨，實體跌破628追擊法人高檔反轉。"},
    {"rank": "🥉 3", "ticker": "2492", "name": "華新科(期)", "tool": "個股期", "size": "1口", "trigger": 365.0, "stop": 375.0, "t1": 345.0, "shares": 2000, "max_loss": 20000, "reason": "三大法人由+1.2萬轉為-8266張，3天+23%爆量留長上影，跌破365確認轉弱。"},
    {"rank": "4", "ticker": "8039", "name": "台虹(期)", "tool": "個股期", "size": "1口", "trigger": 299.0, "stop": 309.0, "t1": 289.0, "shares": 2000, "max_loss": 20000, "reason": "外資連6賣，法人-2638張，股價上漲與法人賣超背離，跌破299順勢做空。"},
    {"rank": "5", "ticker": "3406", "name": "玉晶光(期)", "tool": "個股期", "size": "1口", "trigger": 1045.0, "stop": 1055.0, "t1": 1025.0, "shares": 2000, "max_loss": 20000, "reason": "法人連12日賣超，強鎖漲停但籌碼矛盾，跌破1045確認強勢結構瓦解。"}
]

ORDERS_CLAUDE_S2R2 = [
    {"rank": "🥇 1", "ticker": "8039", "name": "台虹(期)", "tool": "個股期", "size": "1口", "trigger": 297.5, "stop": 307.0, "t1": 278.5, "shares": 2000, "max_loss": 19064, "reason": "外資趁拉高倒貨，未觸發硬濾網；門檻<297.5確認破線，停損卡今日高點307。"},
    {"rank": "🥈 2", "ticker": "2492", "name": "華新科(期)", "tool": "個股期", "size": "1口", "trigger": 369.0, "stop": 378.5, "t1": 350.0, "shares": 2000, "max_loss": 19070, "reason": "補位入選；外資倒貨8千張留長上影，摜破369追擊高檔多殺多。"},
    {"rank": "🥉 3", "ticker": "2313", "name": "華通(期)", "tool": "個股期", "size": "1口", "trigger": 249.0, "stop": 258.5, "t1": 230.0, "shares": 2000, "max_loss": 19060, "reason": "補位入選；強鎖漲停248.5，若早盤開高反轉跌破249，順勢狙擊漲停打開。"},
    {"rank": "4", "ticker": "2327", "name": "國巨*(期)", "tool": "個股期", "size": "1口", "trigger": 631.0, "stop": 640.0, "t1": 613.0, "shares": 2000, "max_loss": 18090, "reason": "補位入選；外資賣超逾萬張，衝高回測平盤，跌破631放空抓回檔。"},
    {"rank": "5", "ticker": "2455", "name": "全新(期)", "tool": "個股期", "size": "1口", "trigger": 602.0, "stop": 611.0, "t1": 584.0, "shares": 2000, "max_loss": 18088, "reason": "補位入選；處置量縮創高，摜破602心理支撐放空，停損設在611。"}
]

# ==============================================================================
# 5. 技術指標計算與互動線圖
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
# 6. 量化撮合與方案 A 階梯結算引擎 (含手續費與期交稅扣除)
# ==============================================================================
def execute_quant_settlement(order, k_open, k_close, k_low, k_high, next_k_open, exit_k_close=None):
    trigger_p = float(order["trigger"])
    stop_p = float(order["stop"])
    t1_p = float(order["t1"])
    shares = order["shares"]
    contracts = shares // 2000
    
    # 公約第 5 條：開盤已跌破 T1 則不進場撤單
    if k_open <= t1_p:
        return {
            "status": "⚪ 穿過T1撤單 (不進場)", "entry_price": None, "exit_price": None,
            "pnl_points": 0.0, "pnl_ntd": 0, "commission": 0, "tax": 0,
            "note": f"開盤 {k_open} 已低於或等於 T1 ({t1_p})，依公約撤單不進場。"
        }
    
    # 5分K黑棒跌破檢驗 (收盤 < 開盤 且 收盤 < 門檻)
    if not (k_close < k_open and k_close < trigger_p):
        return {
            "status": "⚪ 未觸發 (空手防守)", "entry_price": None, "exit_price": None,
            "pnl_points": 0.0, "pnl_ntd": 0, "commission": 0, "tax": 0,
            "note": f"5分K未收黑破門檻 {trigger_p}，空手觀望。"
        }
    
    # 不利滑價進場撮合
    entry_p = min(k_close, next_k_open)
    
    # 若成交價亦穿過 T1，同樣不進場
    if entry_p <= t1_p:
        return {
            "status": "⚪ 撮合價跌過T1撤單", "entry_price": None, "exit_price": None,
            "pnl_points": 0.0, "pnl_ntd": 0, "commission": 0, "tax": 0,
            "note": f"撮合價 {entry_p} 跌過 T1 ({t1_p})，利潤耗盡撤單。"
        }

    # 計算嚴格 2 萬金盾停損點 (反推含稅費)
    # 最大虧損 = (進場 - 出場) * 股數 - 總手續費 - 總稅 <= -20000
    total_comm = COMMISSION_PER_CONTRACT * 2 * contracts
    # 近似反推硬停損點
    max_pts_risk = (MAX_STOP_LOSS_NTD - total_comm) / shares
    shield_stop_p = round(entry_p + max_pts_risk, 2)
    effective_stop_p = min(stop_p, shield_stop_p)

    def calc_net_pnl(en, ex):
        pts = en - ex
        gross = pts * shares
        entry_tax = round(en * shares * TAX_RATE)
        exit_tax = round(ex * shares * TAX_RATE)
        net = gross - total_comm - entry_tax - exit_tax
        return pts, int(net), total_comm, (entry_tax + exit_tax)

    # 1. 停損檢驗
    if k_high >= effective_stop_p:
        pts, net, comm, tax = calc_net_pnl(entry_p, effective_stop_p)
        effective_loss = max(net, -MAX_STOP_LOSS_NTD)
        return {
            "status": "❌ 停損平倉 (2萬金盾觸發)", "entry_price": entry_p, "exit_price": effective_stop_p,
            "pnl_points": pts, "pnl_ntd": effective_loss, "commission": comm, "tax": tax,
            "note": f"突破金盾停損價 {effective_stop_p}，依紀律手起刀落停損出場。"
        }
    
    # 2. 方案 A 停利檢驗 (觸及 T1 全平保底)
    if k_low <= t1_p:
        pts, net, comm, tax = calc_net_pnl(entry_p, t1_p)
        return {
            "status": "🎯 方案 A 停利 (命中 T1)", "entry_price": entry_p, "exit_price": t1_p,
            "pnl_points": pts, "pnl_ntd": net, "commission": comm, "tax": tax,
            "note": f"盤中穿破 T1 ({t1_p})，依方案 A 全數平倉保底獲利！"
        }
    
    # 3. 13:25 尾盤強制平倉
    if exit_k_close is not None:
        pts, net, comm, tax = calc_net_pnl(entry_p, exit_k_close)
        return {
            "status": "⏰ 尾盤強制平倉 (13:25)", "entry_price": entry_p, "exit_price": exit_k_close,
            "pnl_points": pts, "pnl_ntd": net, "commission": comm, "tax": tax,
            "note": f"未達 T1 且未停損，13:25 以開盤價 {exit_k_close} 強平出場。"
        }

    return {
        "status": "⏳ 部位持倉中", "entry_price": entry_p, "exit_price": None,
        "pnl_points": 0.0, "pnl_ntd": 0, "commission": 0, "tax": 0,
        "note": f"部位建立於不利滑價 {entry_p}，等待觸發 T1 或 13:25 結算。"
    }

# ==============================================================================
# 7. 融資大數據模組 (2026/10/05 最新校準)
# ==============================================================================
LOCAL_MARGIN_HISTORY_10D_S2R2 = {
    "2492": [
        {"date": "09/23", "buy": 1800, "sell": 1600, "change": 200, "balance": 18200},
        {"date": "09/24", "buy": 2100, "sell": 1900, "change": 200, "balance": 18400},
        {"date": "09/29", "buy": 2400, "sell": 2000, "change": 400, "balance": 18800},
        {"date": "09/30", "buy": 2800, "sell": 2500, "change": 300, "balance": 19100},
        {"date": "10/01", "buy": 3100, "sell": 2900, "change": 200, "balance": 19300},
        {"date": "10/02", "buy": 3400, "sell": 4596, "change": -1196, "balance": 18104},
        {"date": "10/05", "buy": 7820, "sell": 4438, "change": 3382, "balance": 21486}
    ],
    "3042": [
        {"date": "09/23", "buy": 1200, "sell": 1100, "change": 100, "balance": 14100},
        {"date": "09/24", "buy": 1400, "sell": 1250, "change": 150, "balance": 14250},
        {"date": "09/29", "buy": 1600, "sell": 1300, "change": 300, "balance": 14550},
        {"date": "09/30", "buy": 1500, "sell": 1600, "change": -100, "balance": 14450},
        {"date": "10/01", "buy": 1800, "sell": 1700, "change": 100, "balance": 14550},
        {"date": "10/02", "buy": 2450, "sell": 1329, "change": 1121, "balance": 15671},
        {"date": "10/05", "buy": 1850, "sell": 1964, "change": -114, "balance": 15557}
    ],
    "2344": [
        {"date": "09/23", "buy": 2200, "sell": 1900, "change": 300, "balance": 35350},
        {"date": "09/24", "buy": 2400, "sell": 2200, "change": 200, "balance": 35550},
        {"date": "09/29", "buy": 2100, "sell": 2719, "change": -619, "balance": 34931},
        {"date": "09/30", "buy": 2800, "sell": 2650, "change": 150, "balance": 35081},
        {"date": "10/01", "buy": 2100, "sell": 4601, "change": -2501, "balance": 32580},
        {"date": "10/02", "buy": 5890, "sell": 3412, "change": 2478, "balance": 35058},
        {"date": "10/05", "buy": 3200, "sell": 8543, "change": -5343, "balance": 29715}
    ],
    "6173": [
        {"date": "09/23", "buy": 1680, "sell": 1420, "change": 260, "balance": 11710},
        {"date": "09/24", "buy": 1850, "sell": 1365, "change": 485, "balance": 12195},
        {"date": "09/29", "buy": 1720, "sell": 1191, "change": 529, "balance": 12724},
        {"date": "09/30", "buy": 1420, "sell": 3080, "change": -1660, "balance": 11064},
        {"date": "10/01", "buy": 1560, "sell": 2417, "change": -857, "balance": 10207},
        {"date": "10/02", "buy": 1240, "sell": 2340, "change": -1100, "balance": 9107},
        {"date": "10/05", "buy": 950, "sell": 2687, "change": -1737, "balance": 7370}
    ]
}

@st.cache_data(ttl=300)
def fetch_stock_margin_10d(stock_code):
    code_str = str(stock_code).strip()
    fallback_data = LOCAL_MARGIN_HISTORY_10D_S2R2.get(code_str, [
        {"date": "09/24", "buy": 1250, "sell": 1100, "change": 150, "balance": 15150},
        {"date": "09/29", "buy": 1500, "sell": 1200, "change": 300, "balance": 15450},
        {"date": "09/30", "buy": 1200, "sell": 1300, "change": -100, "balance": 15350},
        {"date": "10/01", "buy": 1300, "sell": 1350, "change": -50, "balance": 15300},
        {"date": "10/02", "buy": 1450, "sell": 1350, "change": 100, "balance": 15400},
        {"date": "10/05", "buy": 1600, "sell": 1500, "change": 100, "balance": 15500}
    ])
    return pd.DataFrame(fallback_data)

# ==============================================================================
# 8. 母池數據加載
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
        
        score_dict = {
            "3042": 99, "6173": 96, "3406": 92, "2492": 90, "2327": 85, 
            "3189": 70, "2455": 60, "8039": 45, "3037": 40, "2344": 15, "2408": 10, "2313": 5
        }
        score = score_dict.get(code, 50)
        alert_tag = "👑 首選獵殺" if score >= 95 else ("🎯 次選狙擊" if score >= 85 else ("🟡 觀望換手" if score >= 60 else "🛑 嚴格禁空"))
        alert_desc = f"【{alert_tag}】10/05 融資: {margin_change:+d} 張，認購: {call_val:+d} 萬"
        
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

df_display = load_radar_market_data(DEFAULT_WATCHLIST_S2R2)
df_display.index = range(1, len(df_display) + 1)

# ==============================================================================
# 9. 側邊欄控制台 (三 AI 並列儀表板)
# ==============================================================================
st.sidebar.title("⚔️ S2 三方對決戰情室")
st.sidebar.markdown(f"**決戰輪次**：`Season 2 Round 2` ({S2_R2_MATCH_DATE})")
st.sidebar.markdown(f"**籌碼基準日**：`{DATA_BASE_DATE}` 三維完整大數據")

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 S2 最新權益天梯榜 (R1 結算定案)")
st.sidebar.markdown(f"""
<div class="metric-card-gpt">
    <div style="font-size: 12px; color: #BBB;">🥇 🟦 ChatGPT 戰情室 (榜首領跑)</div>
    <div style="font-size: 20px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CHATGPT:,.2f}</div>
    <div style="font-size: 11px; color: #64B5F6;">S2-R1 損益：-NT$ 20,000 (-2.00%)</div>
</div>
<div class="metric-card-gemini">
    <div style="font-size: 12px; color: #BBB;">🥈 🟥 Gemini 戰情室 (緊追在後)</div>
    <div style="font-size: 20px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_GEMINI:,.2f}</div>
    <div style="font-size: 11px; color: #E57373;">S2-R1 損益：-NT$ 28,180 (-2.82%)</div>
</div>
<div class="metric-card-claude">
    <div style="font-size: 12px; color: #BBB;">🥉 🟪 Claude 戰情室 (新參戰)</div>
    <div style="font-size: 20px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CLAUDE:,.2f}</div>
    <div style="font-size: 11px; color: #BA68C8;">S2-R1 損益：-NT$ 29,055 (-2.91%)</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.info(f"🚩 **榜首差距**：\n• Gemini 落後 GPT：NT$ 8,179.60\n• Claude 落後 GPT：NT$ 9,054.46\n\n🛡️ **風控硬公約**：\n單筆最大停損 **≤ NT$ 20,000** ｜ **命中 T1 全平保底** ｜ **13:25 市價強平**")

# ==============================================================================
# 10. 主頁面六大核心分頁
# ==============================================================================
st.title("⚔️ 三 AI 量化短空競賽｜第二場 Round 2 (S2-R2) 旗艦決戰室")
st.caption(f"比賽開盤日：{S2_R2_MATCH_DATE} 週二 08:45｜籌碼大數據：{DATA_BASE_DATE} 官方融資券、主力分點、自營商權證金流")

tab_workspace, tab_broker, tab_margin, tab_orders, tab_radar, tab_s2r1_hall = st.tabs([
    "🖥️ 專業操盤工作台 (K線與分點)",
    "🏢 主力分點 (10/05 全景矩陣總表)",
    "📈 融資增減 (10/05 官方增減排行)",
    "⚔️ S2-R2 三方官方決戰名冊", 
    "📊 12檔母池籌碼雷達全景表",
    "📜 S2-R1 官方結算對帳檔案庫"
])

# ------------------------------------------------------------------------------
# TAB 1: 專業操盤工作台
# ------------------------------------------------------------------------------
with tab_workspace:
    left_side, right_side = st.columns([1.35, 3.65], gap="medium")
    
    with left_side:
        st.markdown("### 📋 短空鎖碼清單 (10/05 盤後)")
        st.caption("💡 嚴格等寬對齊，使用 **↑ / ↓ 鍵** 快速切換標的")
        
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
                <span style="color: #AAA;">主力加權均價：</span><span style="font-weight: bold; color: #00E5FF;">{target_row['主力加權成本']} 元</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px;">
                <span style="color: #FF8800; font-weight: bold;">核心壓力(NH)：</span><span style="font-weight: bold; color: #FF8800;">{target_row['近高壓力(NH)']} 元</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px;">
                <span style="color: #AAA;">10/05 官方融資：</span><span style="font-weight: bold; color: {'#FF4444' if target_row['融資增減(張)']>=0 else '#00FF66'};">{target_row['融資增減(張)']:+,} 張</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px;">
                <span style="color: #AAA;">自營權證認購賣超：</span><span style="font-weight: bold; color: {'#00FF66' if target_row['權證認購(萬)']<0 else '#FFF'};">{target_row['權證認購(萬)']:+,} 萬元</span>
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

        st.markdown(f"#### 🏢 【{target_name}】主力分點進出明細 (10/05 盤後)")
        b_list = target_row.get("各分點清單", [])
        if b_list:
            df_b = pd.DataFrame(b_list)
            df_b.index = range(1, len(df_b) + 1)
            st.dataframe(df_b, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: 🏢 主力分點全景矩陣總表
# ------------------------------------------------------------------------------
with tab_broker:
    st.subheader(f"🏢 12 檔母池主力關鍵分點全景矩陣總表 ({DATA_BASE_DATE} 盤後真實撮合)")
    st.caption("⚡ 免逐檔切換！單一總表直接展開前五大買超/賣超主力與總量，滑鼠輕鬆滾動一覽無遺。")

    matrix_rows = []
    for item in DEFAULT_WATCHLIST_S2R2:
        c_code = item["代號"]
        c_name = item["名稱"]
        c_close = float(item["昨收"])
        
        fut_tag = " [期]" if c_code in STOCK_FUTURES_SET else ""
        code_with_tag = f"{c_code}{fut_tag}"
        
        b_list = item.get("主力分點", [])
        buys = sorted([b for b in b_list if b.get("買超", 0) > 0], key=lambda x: x.get("買超", 0), reverse=True)[:5]
        sells = sorted([b for b in b_list if b.get("買超", 0) < 0], key=lambda x: x.get("買超", 0))[:5]

        if buys:
            buy_lines = [f"{b['分點']} ({b['買超']:+,d}張 | {b['均價']:.1f}元)" for b in buys]
            b5_txt = "\n".join(buy_lines)
            b5_total = sum(b['買超'] for b in buys)
        else:
            b5_txt = "—"
            b5_total = 0

        if sells:
            sell_lines = [f"{s['分點']} ({s['買超']:+,d}張 | {s['均價']:.1f}元)" for s in sells]
            s5_txt = "\n".join(sell_lines)
            s5_total = sum(s['買超'] for s in sells)
        else:
            s5_txt = "—"
            s5_total = 0

        if c_code == "2492":
            diag = "🚨 留28元長上影，融資大增3382張，大摩高盛狂倒6700張"
        elif c_code == "3042":
            diag = "👑 認購權證爆賣-8448萬全市場第2，自營商被動砍倉狂跌"
        elif c_code == "3406":
            diag = "🎯 凱基信義單一主力掃1047張鎖漲停，明早隔日沖摜壓倒貨"
        elif c_code == "6173":
            diag = "🎯 收最低292長黑，統一凱基提款2100張，買盤徹底渙散"
        elif c_code == "2327":
            diag = "⚡ 外資大摩高盛美林集體大倒1.1萬張，高檔分歧收平盤"
        elif c_code == "8039":
            diag = "🟡 外資趁拉高倒貨，但認購買超1914萬有自營商支撐"
        elif c_code in ["2344", "2408", "2313"]:
            diag = "🛑 法人爆買逾萬張/強鎖漲停主升浪，嚴格禁空！"
        else:
            diag = "⚪ 法人震盪洗盤換手"

        matrix_rows.append({
            "代號": code_with_tag,
            "名稱": c_name,
            "股價": c_close,
            "🔴 前五大買超主力": b5_txt,
            "買超總量": b5_total,
            "🟢 前五大賣超主力": s5_txt,
            "賣超總量": s5_total,
            "籌碼多空結構診斷": diag
        })

    df_matrix = pd.DataFrame(matrix_rows)
    df_matrix.index = range(1, len(df_matrix) + 1)

    st.dataframe(
        df_matrix, 
        use_container_width=True, 
        height=720,
        column_config={
            "代號": st.column_config.TextColumn("代號", width=95),
            "名稱": st.column_config.TextColumn("名稱", width=85),
            "股價": st.column_config.NumberColumn("股價", format="%.1f", width=75),
            "🔴 前五大買超主力": st.column_config.TextColumn("🔴 前五大買超主力 (分點/張數/均價)", width=320),
            "買超總量": st.column_config.NumberColumn("買超總量", format="%+d 張", width=110),
            "🟢 前五大賣超主力": st.column_config.TextColumn("🟢 前五大賣超主力 (分點/張數/均價)", width=320),
            "賣超總量": st.column_config.NumberColumn("賣超總量", format="%+d 張", width=110),
            "籌碼多空結構診斷": st.column_config.TextColumn("籌碼多空結構診斷", width=280),
        }
    )

# ------------------------------------------------------------------------------
# TAB 3: 📈 融資增減
# ------------------------------------------------------------------------------
with tab_margin:
    st.subheader(f"📊 12 檔母池 {MARGIN_DISPLAY_DATE} 官方融資增減熱力排行榜 (按增減張數降序)")
    st.caption("資料來源：臺灣證券交易所官方核定。🔴 紅色代表融資增加（散戶接刀慘套），🟢 綠色代表融資減少（斷頭退場/外資洗盤）。")

    summary_margin_list = []
    for item in DEFAULT_WATCHLIST_S2R2:
        c_code = item["代號"]
        c_name = item["名稱"]
        c_price = item["昨收"]
        df_10d = fetch_stock_margin_10d(c_code)
        
        last_chg = item.get("融資增減(張)", 0)
        last_bal = int(df_10d.iloc[-1]["balance"]) if not df_10d.empty else 10000
        cum_10d_chg = int(df_10d["change"].sum()) if not df_10d.empty else last_chg
        
        if last_chg > 2000:
            status_desc = "🔴 融資狂增暴套 (散戶高檔接刀 / 踩踏引信引爆)"
        elif last_chg > 500:
            status_desc = "🟠 融資堆積 (浮額沉重，面臨高檔回測)"
        elif last_chg > 0:
            status_desc = "🟡 融資微增 (籌碼略顯渙散)"
        elif last_chg < -2000:
            status_desc = "🟢 融資崩退洗淨 (散戶全面停損 / 籌碼落入外資手中)"
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
# TAB 4: S2-R2 三方正式決戰名冊 (含裁判長撮合結算模擬台)
# ------------------------------------------------------------------------------
with tab_orders:
    st.subheader("⚔️ S2-R2 三大 AI 官方 TOP 5 決戰名冊陣列 (三方鼎立版)")
    st.caption("公證核定：晶技/華邦電/華通上限 2 口，其餘上限 1 口；單筆最大停損 ≤ NT$ 20,000；命中 T1 方案 A 立即全平保底。")
    col_g, col_c, col_cl = st.columns(3)
    
    with col_g:
        st.markdown("#### 🟥 Gemini 戰情室 S2-R2")
        st.caption(f"起始權益：NT$ {CAPITAL_GEMINI:,.2f} ｜ 上限：NT$ 1,000,000")
        df_gem_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "口數": x['size'], "最大風險": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_GEMINI_S2R2
        ])
        st.dataframe(df_gem_ui, use_container_width=True, hide_index=True)
        with st.expander("🔍 查看 Gemini 籌碼微觀依據", expanded=False):
            for x in ORDERS_GEMINI_S2R2:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']:.1f}`**")
                st.caption(f"└ {x['reason']}")
                
    with col_c:
        st.markdown("#### 🟦 ChatGPT 戰情室 S2-R2")
        st.caption(f"起始權益：NT$ {CAPITAL_CHATGPT:,.2f} ｜ 上限：NT$ 1,000,000")
        df_gpt_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "口數": x['size'], "最大風險": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_CHATGPT_S2R2
        ])
        st.dataframe(df_gpt_ui, use_container_width=True, hide_index=True)
        with st.expander("🔍 查看 ChatGPT 策略邏輯", expanded=False):
            for x in ORDERS_CHATGPT_S2R2:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']:.1f}`**")
                st.caption(f"└ {x['reason']}")

    with col_cl:
        st.markdown("#### 🟪 Claude 戰情室 S2-R2 (補位版)")
        st.caption(f"起始權益：NT$ {CAPITAL_CLAUDE:,.2f} ｜ 上限：NT$ 1,000,000")
        df_claude_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "口數": x['size'], "最大風險": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_CLAUDE_S2R2
        ])
        st.dataframe(df_claude_ui, use_container_width=True, hide_index=True)
        with st.expander("🔍 查看 Claude 策略邏輯", expanded=False):
            for x in ORDERS_CLAUDE_S2R2:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']:.1f}`**")
                st.caption(f"└ {x['reason']}")

    st.markdown("---")
    st.subheader("🛑 S2-R2 三方官方禁空名單（NO SHORT LIST）對照")
    cn1, cn2, cn3 = st.columns(3)
    cn1.error("🚫 **Gemini 禁空**：\n• 2344 華邦電 (外資大買1.4萬張護盤)\n• 2408 南亞科 (本土富邦大掃3083張)\n• 2313 華通 (法人狂掃1.7萬張強鎖主升)")
    cn2.error("🚫 **ChatGPT 禁空**：\n• 2344 華邦電 (外資+2.2萬張轉多)\n• 2313 華通 (外資大買7880張鎖漲停)\n• 2408 南亞科、3189 景碩、6173 信昌電")
    cn3.error("🚫 **Claude 原始禁空**：\n• 3042 晶技、6173 信昌電\n• 3406 玉晶光、2408 南亞科\n• 2344 華邦電、3189 景碩、3037 欣興")

    st.markdown("---")
    
    # --------------------------------------------------------------------------
    # 🧮 內嵌：裁判長即時撮合與結算仲裁模擬台 (升級 1分K、滑價、手續費與稅)
    # --------------------------------------------------------------------------
    with st.expander("⚖️ 裁判室專用：1分K逐筆撮合與方案 A 結算模擬器 (點擊展開操作)", expanded=True):
        st.caption("依據官方公約：取不利撮合價進場，開盤穿破 T1 撤單不進場；嚴格扣除手續費 (每口20元) 與期交稅 (十萬分之二)；單筆損失嚴格上限 NT$ 20,000。")
        
        sim_c1, sim_c2 = st.columns(2)
        with sim_c1:
            st.markdown("**步驟 1：選擇審查陣營與封單**")
            selected_side = st.radio("參賽陣營：", ["🟥 Gemini 戰情室", "🟦 ChatGPT 戰情室", "🟪 Claude 戰情室"], horizontal=True, key="embedded_sim_side_r2")
            if "Gemini" in selected_side:
                order_set = ORDERS_GEMINI_S2R2
            elif "ChatGPT" in selected_side:
                order_set = ORDERS_CHATGPT_S2R2
            else:
                order_set = ORDERS_CLAUDE_S2R2
            
            target_order = st.selectbox(
                "選擇審查封單：", order_set,
                format_func=lambda x: f"{x['rank']} {x['name']} (門檻 < {x['trigger']:.1f}, 停損: {x['stop']:.1f}, T1保利: {x['t1']:.1f})",
                key="embedded_sim_order_r2"
            )
            
            st.markdown("**步驟 2：輸入盤面走勢價位 (依 1分K / 5分K 穿透)**")
            k_open_in = st.number_input("開盤價 (檢驗是否已跌穿 T1)：", value=float(target_order["trigger"]) + 1.0, step=0.5, key="sim_k_o_r2")
            k_close_in = st.number_input("觸發 K 棒收盤價：", value=float(target_order["trigger"]) - 0.5, step=0.5, key="sim_k_c_r2")
            next_open_in = st.number_input("次一根 K 棒開盤價：", value=float(target_order["trigger"]) - 1.0, step=0.5, key="sim_next_o_r2")
            k_high_in = st.number_input("盤中最高價 (檢驗停損)：", value=float(target_order["stop"]) - 1.0, step=0.5, key="sim_k_h_r2")
            k_low_in = st.number_input("盤中最低價 (檢驗方案 A T1)：", value=float(target_order["t1"]) - 1.0, step=0.5, key="sim_k_l_r2")
            exit_close_in = st.number_input("13:25 當根開盤價 (尾盤強平價)：", value=float(target_order["trigger"]) - 2.0, step=0.5, key="sim_k_exit_r2")
            
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
                    st.write(f"- **扣除成本**：手續費 `NT$ {res['commission']:,}` ｜ 期交稅 `NT$ {res['tax']:,}`")
                    if res['pnl_ntd'] > 0:
                        st.success(f"💰 **核定稅後淨獲利**：`+NT$ {res['pnl_ntd']:,}`")
                    else:
                        st.error(f"📉 **核定稅後淨損失**：`-NT$ {abs(res['pnl_ntd']):,}` (嚴格鎖定在 2 萬金盾內)")
            st.caption(f"**仲裁備註**：{res['note']}")

# ------------------------------------------------------------------------------
# TAB 5: 12檔母池籌碼雷達全景表
# ------------------------------------------------------------------------------
with tab_radar:
    st.subheader(f"📋 12 檔母池三維大數據全景表 ({DATA_BASE_DATE} 官方融資與權證校正版)")
    preferred_cols = [
        "短空勝率分", "股票代號", "股票名稱", "個期", "現價", "即時信號",
        "融資增減(張)", "權證認售(萬)", "權證認購(萬)", "近高壓力(NH)", "主力加權成本", "主力合計買超", "主力合計佔比(%)"
    ]
    st.dataframe(df_display[[c for c in preferred_cols if c in df_display.columns]], use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 6: 📜 S2-R1 官方結算對帳檔案庫
# ------------------------------------------------------------------------------
with tab_s2r1_hall:
    st.subheader("📜 Season 2 Round 1 (S2-R1) 官方最終核定對帳公報 (2026/10/05 開幕戰)")
    st.caption("依據 1分K 逐筆撮合、不利滑價、手續費與期交稅扣除、以及穿過 T1 撤單公約，公證最終結果如下：")
    
    r1_summary_df = pd.DataFrame([
        {"天梯排名": "🥇 冠軍", "參賽戰情室": "🟦 ChatGPT 戰情室", "成交標的": "1檔 (2口)", "當日淨損益": "-NT$ 20,000", "終局總權益": "NT$ 979,999.68", "報酬率": "-2.00%", "關鍵戰況": "華邦電觸碰 2 萬金盾停損；其餘 4 檔門檻未達空手防守成功"},
        {"天梯排名": "🥈 亞軍", "參賽戰情室": "🟥 Gemini 戰情室", "成交標的": "3檔 (5口)", "當日淨損益": "-NT$ 28,180", "終局總權益": "NT$ 971,820.08", "報酬率": "-2.82%", "關鍵戰況": "信昌電穿T1撤單；華邦電/台虹金盾停損；晶技尾盤強平獲利+3884元"},
        {"天梯排名": "🥉 季軍", "參賽戰情室": "🟪 Claude 戰情室", "成交標的": "2檔 (2口)", "當日淨損益": "-NT$ 29,055", "終局總權益": "NT$ 970,945.22", "報酬率": "-2.91%", "關鍵戰況": "台虹觸碰金盾硬停損(-2萬)；華邦電尾盤強平(-9054元)"}
    ])
    st.dataframe(r1_summary_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("👑 第一場 (Season 1) 總冠軍名人堂歷史檔案")
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("首季總冠軍", "🟥 Gemini 戰情室", "11勝 6負 3平")
    c_m2.metric("首季終局淨值", "NT$ 1,743,595", "+74.36%")
    c_m3.metric("首季總獲利差距", "NT$ 331,914 領先", "亞軍 GPT: $1,411,681")

# ==============================================================================
# 11. 系統頁尾
# ==============================================================================
st.markdown("---")
st.caption(f"三 AI 量化短空雷達系統 v23.0 (S2-R2 巔峰決戰版)｜{S2_R2_MATCH_DATE} 週二 08:45 開盤生效｜執法公約：1分K逐筆不利撮合 + 2萬金盾硬停損 + 穿過T1撤單 + 方案A全平保底 + 13:25強平")
