# -*- coding: utf-8 -*-
"""
三 AI 量化短空雷達 (S2-R1 三巨頭鼎立裁判長正式版) - app.py (v22.1)
==============================================================================
版本更新重點：
1. 資金規則全面修訂：依裁判長最新裁定，廢除單檔 20 萬上限，改採「分級固定口數 + 
   帳戶未平倉總保證金 ≤ 100 萬 + 依順位扣抵佇列」制。
2. 分級口數落實：華邦電(2344)、晶技(3042)、華通(2313) 上限 2 口；其餘 9 檔上限 1 口。
3. 官方封存名冊更新：
   - 🟥 Gemini：信昌電(1口/-1萬)、華邦電(2口/-2萬)、台虹(1口/-1萬)、晶技(2口/-2萬)、全新(1口/-2萬)。
   - 🟦 ChatGPT：華邦電(2口)、台虹(1口)、晶技(2口)、全新(1口)、國巨(1口) (依新規調整口數與停損)。
   - 🟪 Claude：華邦電(1口)、台虹(1口)、玉晶光(1口)、華通(1口) (四檔精選，其餘觸發禁空濾網)。
4. 單筆最大停損：維持單筆最大虧損強制硬上限 ≤ NT$ 20,000 金盾。
5. 撮合模擬器同步支援三方最新點位與口數股數換算。
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
    page_title="三 AI 量化短空雷達 (S2-R1 三方鼎立版)", 
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
# 2. 第二場公約常數與三方帳戶狀態 (2026/10/05 開賽重置)
# ==============================================================================
S2_R1_DATE = "2026/10/05"
DATA_BASE_DATE = "2026/10/02"
MARGIN_DISPLAY_DATE = "10/02"

CAPITAL_GEMINI = 1000000
CAPITAL_CHATGPT = 1000000
CAPITAL_CLAUDE = 1000000
MAX_ACCOUNT_MARGIN = 1000000  # 任一時點未平倉保證金總額上限 100 萬

MAX_STOP_LOSS_NTD = 20000  # 2 萬金盾硬停損

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
# 3. 2026-10-02 盤後 12 檔母池三維大數據庫
# ==============================================================================
DEFAULT_WATCHLIST_S2R1 = [
    {
        "代號": "6173", "名稱": "信昌電", "昨收": 303.00, "昨日鎖碼量": 24376, "融資增減(張)": -1100, "券資比": 4.0, "權證認售(萬)": 138, "權證認購(萬)": 0,
        "最高價": 322.50, "最低價": 299.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 2078, "均價": 313.97, "佔比": 8.52},
            {"分點": "富邦", "買超": 592, "均價": 311.05, "佔比": 2.43},
            {"分點": "富邦-彰化", "買超": 245, "均價": 312.91, "佔比": 1.01},
            {"分點": "華南永昌-竹北", "買超": 96, "均價": 308.37, "佔比": 0.39},
            {"分點": "美商高盛", "買超": 83, "均價": 313.61, "佔比": 0.34},
            {"分點": "群益金鼎", "買超": -781, "均價": 309.20, "佔比": -3.20},
            {"分點": "凱基", "買超": -341, "均價": 314.06, "佔比": -1.40},
            {"分點": "國泰", "買超": -182, "均價": 314.45, "佔比": -0.75},
            {"分點": "摩根大通", "買超": -177, "均價": 304.00, "佔比": -0.73},
            {"分點": "統一", "買超": -165, "均價": 311.62, "佔比": -0.68}
        ]
    },
    {
        "代號": "2344", "名稱": "華邦電", "昨收": 179.00, "昨日鎖碼量": 74491, "融資增減(張)": 2478, "券資比": 2.5, "權證認售(萬)": -27, "權證認購(萬)": 0,
        "最高價": 184.00, "最低價": 177.50,
        "主力分點": [
            {"分點": "元大", "買超": 3007, "均價": 179.75, "佔比": 4.04},
            {"分點": "台灣摩根士丹利", "買超": 1403, "均價": 179.81, "佔比": 1.88},
            {"分點": "摩根大通", "買超": 1211, "均價": 179.89, "佔比": 1.63},
            {"分點": "凱基-文心", "買超": 628, "均價": 178.83, "佔比": 0.84},
            {"分點": "華南永昌-大甲", "買超": 584, "均價": 179.38, "佔比": 0.78},
            {"分點": "凱基-站前", "買超": -10092, "均價": 178.73, "佔比": -13.55},
            {"分點": "富邦", "買超": -3825, "均價": 179.05, "佔比": -5.13},
            {"分點": "美林", "買超": -1230, "均價": 179.17, "佔比": -1.65},
            {"分點": "花旗環球", "買超": -1017, "均價": 179.53, "佔比": -1.37},
            {"分點": "港商野村", "買超": -935, "均價": 179.04, "佔比": -1.26}
        ]
    },
    {
        "代號": "8039", "名稱": "台虹", "昨收": 296.00, "昨日鎖碼量": 19171, "融資增減(張)": 2220, "券資比": 4.8, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 296.00, "最低價": 280.50,
        "主力分點": [
            {"分點": "新光", "買超": 424, "均價": 291.83, "佔比": 2.21},
            {"分點": "凱基-信義", "買超": 329, "均價": 294.80, "佔比": 1.72},
            {"分點": "台新", "買超": 217, "均價": 289.07, "佔比": 1.13},
            {"分點": "元大", "買超": 213, "均價": 287.51, "佔比": 1.11},
            {"分點": "永豐金-敦北", "買超": 199, "均價": 294.72, "佔比": 1.04},
            {"分點": "國票-敦北法人", "買超": -566, "均價": 283.78, "佔比": -2.95},
            {"分點": "摩根大通", "買超": -429, "均價": 293.09, "佔比": -2.24},
            {"分點": "統一", "買超": -409, "均價": 283.98, "佔比": -2.13},
            {"分點": "凱基-城中", "買超": -367, "均價": 284.63, "佔比": -1.91},
            {"分點": "凱基-台北", "買超": -354, "均價": 286.84, "佔比": -1.85}
        ]
    },
    {
        "代號": "3042", "名稱": "晶技", "昨收": 230.50, "昨日鎖碼量": 43452, "融資增減(張)": 1121, "券資比": 3.8, "權證認售(萬)": 0, "權證認購(萬)": -2065,
        "最高價": 232.50, "最低價": 217.50,
        "主力分點": [
            {"分點": "凱基", "買超": 1603, "均價": 228.71, "佔比": 3.69},
            {"分點": "群益金鼎", "買超": 801, "均價": 227.44, "佔比": 1.84},
            {"分點": "新加坡商瑞銀", "買超": 791, "均價": 226.83, "佔比": 1.82},
            {"分點": "富邦", "買超": 629, "均價": 227.67, "佔比": 1.45},
            {"分點": "康和", "買超": 512, "均價": 227.71, "佔比": 1.18},
            {"分點": "凱基-台北", "買超": -672, "均價": 224.91, "佔比": -1.55},
            {"分點": "元大", "買超": -509, "均價": 225.26, "佔比": -1.17},
            {"分點": "摩根大通", "買超": -318, "均價": 223.61, "佔比": -0.73},
            {"分點": "美林", "買超": -240, "均價": 226.76, "佔比": -0.55},
            {"分點": "法銀巴黎", "買超": -219, "均價": 225.10, "佔比": -0.50}
        ]
    },
    {
        "代號": "2455", "名稱": "全新", "昨收": 580.00, "昨日鎖碼量": 4299, "融資增減(張)": -274, "券資比": 4.5, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 580.00, "最低價": 551.00,
        "主力分點": [
            {"分點": "美商高盛", "買超": 666, "均價": 569.23, "佔比": 15.49},
            {"分點": "台灣摩根士丹利", "買超": 488, "均價": 567.71, "佔比": 11.35},
            {"分點": "元大", "買超": 429, "均價": 566.59, "佔比": 9.98},
            {"分點": "凱基-城中", "買超": 203, "均價": 571.82, "佔比": 4.72},
            {"分點": "摩根大通", "買超": 200, "均價": 566.38, "佔比": 4.65},
            {"分點": "群益金鼎", "買超": -909, "均價": 563.11, "佔比": -21.14},
            {"分點": "群益金鼎-大安", "買超": -136, "均價": 571.56, "佔比": -3.16},
            {"分點": "國泰-敦南", "買超": -72, "均價": 571.10, "佔比": -1.67},
            {"分點": "永豐金-匯立", "買超": -70, "均價": 564.79, "佔比": -1.63},
            {"分點": "元大-中山北路", "買超": -62, "均價": 580.00, "佔比": -1.44}
        ]
    },
    {
        "代號": "2313", "名稱": "華通", "昨收": 226.00, "昨日鎖碼量": 8635, "融資增減(張)": -190, "券資比": 3.0, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 228.00, "最低價": 224.00,
        "主力分點": [
            {"分點": "元大", "買超": 480, "均價": 226.61, "佔比": 5.56},
            {"分點": "凱基-台北", "買超": 449, "均價": 226.33, "佔比": 5.20},
            {"分點": "摩根大通", "買超": 346, "均價": 226.44, "佔比": 4.01},
            {"分點": "美商高盛", "買超": 265, "均價": 226.12, "佔比": 3.07},
            {"分點": "台灣摩根士丹利", "買超": 245, "均價": 226.98, "佔比": 2.84},
            {"分點": "宏遠", "買超": -528, "均價": 225.43, "佔比": -6.11},
            {"分點": "港商野村", "買超": -128, "均價": 225.98, "佔比": -1.48},
            {"分點": "富邦-南員林", "買超": -65, "均價": 228.00, "佔比": -0.75},
            {"分點": "元大-汐止", "買超": -57, "均價": 226.96, "佔比": -0.66},
            {"分點": "富邦", "買超": -55, "均價": 226.47, "佔比": -0.64}
        ]
    },
    {
        "代號": "2327", "名稱": "國巨*", "昨收": 626.00, "昨日鎖碼量": 106667, "融資增減(張)": 579, "券資比": 3.5, "權證認售(萬)": 112, "權證認購(萬)": 2981,
        "最高價": 647.00, "最低價": 598.00,
        "主力分點": [
            {"分點": "美林", "買超": 2184, "均價": 624.35, "佔比": 2.05},
            {"分點": "花旗環球", "買超": 2099, "均價": 636.74, "佔比": 1.97},
            {"分點": "凱基-站前", "買超": 2012, "均價": 633.07, "佔比": 1.89},
            {"分點": "凱基", "買超": 1463, "均價": 629.42, "佔比": 1.37},
            {"分點": "國泰", "買超": 800, "均價": 629.08, "佔比": 0.75},
            {"分點": "摩根大通", "買超": -3946, "均價": 628.11, "佔比": -3.70},
            {"分點": "元大", "買超": -3315, "均價": 625.87, "佔比": -3.11},
            {"分點": "富邦-新店", "買超": -2468, "均價": 613.18, "佔比": -2.31},
            {"分點": "凱基-台北", "買超": -1558, "均價": 624.09, "佔比": -1.46},
            {"分點": "新加坡商瑞銀", "買超": -953, "均價": 630.37, "佔比": -0.89}
        ]
    },
    {
        "代號": "2492", "名稱": "華新科", "昨收": 361.50, "昨日鎖碼量": 55788, "融資增減(張)": -1196, "券資比": 3.0, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 361.50, "最低價": 329.00,
        "主力分點": [
            {"分點": "美商高盛", "買超": 3819, "均價": 347.73, "佔比": 6.85},
            {"分點": "凱基-台北", "買超": 3079, "均價": 352.21, "佔比": 5.52},
            {"分點": "台新-台北", "買超": 2527, "均價": 361.50, "佔比": 4.53},
            {"分點": "花旗環球", "買超": 1971, "均價": 360.22, "佔比": 3.53},
            {"分點": "凱基-站前", "買超": 1904, "均價": 361.45, "佔比": 3.41},
            {"分點": "元大", "買超": -3623, "均價": 345.76, "佔比": -6.49},
            {"分點": "富邦", "買超": -2512, "均價": 339.87, "佔比": -4.50},
            {"分點": "凱基-信義", "買超": -1142, "均價": 346.42, "佔比": -2.05},
            {"分點": "永豐金", "買超": -526, "均價": 345.10, "佔比": -0.94},
            {"分點": "國泰-敦南", "買超": -384, "均價": 353.99, "佔比": -0.69}
        ]
    },
    {
        "代號": "3037", "名稱": "欣興", "昨收": 1305.00, "昨日鎖碼量": 18635, "融資增減(張)": 699, "券資比": 4.5, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 1305.00, "最低價": 1215.00,
        "主力分點": [
            {"分點": "美林", "買超": 2145, "均價": 1267.48, "佔比": 11.51},
            {"分點": "美商高盛", "買超": 1879, "均價": 1262.82, "佔比": 10.08},
            {"分點": "兆豐", "買超": 709, "均價": 1247.49, "佔比": 3.80},
            {"分點": "台灣摩根士丹利", "買超": 630, "均價": 1255.41, "佔比": 3.38},
            {"分點": "花旗環球", "買超": 347, "均價": 1252.07, "佔比": 1.86},
            {"分點": "國泰-敦南", "買超": -218, "均價": 1261.78, "佔比": -1.17},
            {"分點": "永豐金", "買超": -204, "均價": 1252.24, "佔比": -1.09},
            {"分點": "富邦", "買超": -189, "均價": 1256.17, "佔比": -1.01},
            {"分點": "港商野村", "買超": -188, "均價": 1251.95, "佔比": -1.01},
            {"分點": "統一-竹南", "買超": -184, "均價": 1247.37, "佔比": -0.99}
        ]
    },
    {
        "代號": "3189", "名稱": "景碩", "昨收": 1050.00, "昨日鎖碼量": 18823, "融資增減(張)": -1566, "券資比": 3.9, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 1070.00, "最低價": 1005.00,
        "主力分點": [
            {"分點": "永豐金", "買超": 1696, "均價": 1040.54, "佔比": 9.01},
            {"分點": "台灣摩根士丹利", "買超": 810, "均價": 1035.33, "佔比": 4.30},
            {"分點": "元大-松江", "買超": 320, "均價": 1058.95, "佔比": 1.70},
            {"分點": "統一", "買超": 318, "均價": 1047.35, "佔比": 1.69},
            {"分點": "富邦", "買超": 279, "均價": 1043.60, "佔比": 1.48},
            {"分點": "元大", "買超": -871, "均價": 1038.28, "佔比": -4.63},
            {"分點": "美商高盛", "買超": -319, "均價": 1048.28, "佔比": -1.69},
            {"分點": "凱基-台南", "買超": -227, "均價": 1029.95, "佔比": -1.21},
            {"分點": "永豐金-忠孝", "買超": -201, "均價": 1025.50, "佔比": -1.07},
            {"分點": "合庫", "買超": -186, "均價": 1030.68, "佔比": -0.99}
        ]
    },
    {
        "代號": "2408", "名稱": "南亞科", "昨收": 526.00, "昨日鎖碼量": 36677, "融資增減(張)": -342, "券資比": 3.2, "權證認售(萬)": 71, "權證認購(萬)": -2724,
        "最高價": 534.00, "最低價": 521.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 3220, "均價": 528.50, "佔比": 8.78},
            {"分點": "美商高盛", "買超": 1862, "均價": 529.22, "佔比": 5.08},
            {"分點": "凱基", "買超": 1153, "均價": 528.42, "佔比": 3.14},
            {"分點": "統一", "買超": 1063, "均價": 528.28, "佔比": 2.90},
            {"分點": "國泰", "買超": 985, "均價": 527.27, "佔比": 2.69},
            {"分點": "凱基-站前", "買超": -1045, "均價": 525.95, "佔比": -2.85},
            {"分點": "國泰-敦南", "買超": -455, "均價": 528.14, "佔比": -1.24},
            {"分點": "兆豐-城中", "買超": -242, "均價": 529.70, "佔比": -0.66},
            {"分點": "永豐金", "買超": -185, "均價": 528.86, "佔比": -0.50},
            {"分點": "凱基-信義", "買超": -185, "均價": 528.99, "佔比": -0.50}
        ]
    },
    {
        "代號": "3406", "名稱": "玉晶光", "昨收": 961.00, "昨日鎖碼量": 4816, "融資增減(張)": 208, "券資比": 4.1, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 974.00, "最低價": 929.00,
        "主力分點": [
            {"分點": "統一", "買超": 360, "均價": 956.26, "佔比": 7.48},
            {"分點": "台新", "買超": 59, "均價": 957.87, "佔比": 1.23},
            {"分點": "港商野村", "買超": 51, "均價": 955.19, "佔比": 1.06},
            {"分點": "中國信託", "買超": 46, "均價": 964.84, "佔比": 0.96},
            {"分點": "台灣摩根士丹利", "買超": 36, "均價": 954.04, "佔比": 0.75},
            {"分點": "凱基-台北", "買超": -237, "均價": 949.84, "佔比": -4.92},
            {"分點": "元大", "買超": -176, "均價": 950.04, "佔比": -3.65},
            {"分點": "花旗環球", "買超": -95, "均價": 952.25, "佔比": -1.97},
            {"分點": "摩根大通", "買超": -35, "均價": 959.87, "佔比": -0.73},
            {"分點": "國泰-新莊", "買超": -27, "均價": 952.84, "佔比": -0.56}
        ]
    }
]

# ==============================================================================
# 4. 第二場 Round 1 三方官方最新定案封單陣列 (依裁判長新制完全校準)
# ==============================================================================
# 口數規則：2344, 3042, 2313 最多 2 口，其餘 9 檔最多 1 口
# 1口 = 2,000股, 2口 = 4,000股
ORDERS_GEMINI_S2R1 = [
    {"rank": "🥇 1", "ticker": "6173", "name": "信昌電(期)", "tool": "個股期", "size": "1口", "trigger": 298.5, "stop": 303.5, "t1": 291.0, "shares": 2000, "max_loss": 10000, "reason": "認售連三日全市場買超第1名(+138萬)，衝322.5留長上影，融資大退-1100張潰逃！(依新規調為1口，風險-1萬精準防禦)"},
    {"rank": "🥈 2", "ticker": "2344", "name": "華邦電(期)", "tool": "個股期", "size": "2口", "trigger": 176.5, "stop": 181.5, "t1": 170.0, "shares": 4000, "max_loss": 20000, "reason": "凱基站前天量倒貨-10092張，散戶融資大接刀+2478張，高檔套牢沉重！"},
    {"rank": "🥉 3", "ticker": "8039", "name": "台虹(期)", "tool": "個股期", "size": "1口", "trigger": 291.0, "stop": 296.0, "t1": 282.0, "shares": 2000, "max_loss": 10000, "reason": "尾盤急拉引爆融資單日暴增+2220張，外資主力趁拉抬全線提款出逃！(依新規調為1口，風險-1萬精準防禦)"},
    {"rank": "4", "ticker": "3042", "name": "晶技(期)", "tool": "個股期", "size": "2口", "trigger": 227.0, "stop": 232.0, "t1": 219.0, "shares": 4000, "max_loss": 20000, "reason": "認購大賣-2065萬居市場第3，自營避險買盤將在盤中轉為回吐賣壓！"},
    {"rank": "5", "ticker": "2455", "name": "全新(期)", "tool": "個股期", "size": "1口", "trigger": 568.0, "stop": 578.0, "t1": 554.0, "shares": 2000, "max_loss": 20000, "reason": "群益金鼎單日暴砍-909張(佔比21%)，處置無承接買盤，外資買盤歇息即破線！"}
]

ORDERS_CHATGPT_S2R1 = [
    {"rank": "🥇 1", "ticker": "2344", "name": "華邦電(期)", "tool": "個股期", "size": "2口", "trigger": 178.0, "stop": 183.0, "t1": 168.0, "shares": 4000, "max_loss": 20000, "reason": "站前萬張賣壓壓頂，融資+2478張散戶接刀，5分K實體跌破178追多殺多。"},
    {"rank": "🥈 2", "ticker": "8039", "name": "台虹(期)", "tool": "個股期", "size": "1口", "trigger": 280.5, "stop": 290.5, "t1": 270.5, "shares": 2000, "max_loss": 20000, "reason": "融資暴增2220張多殺多未爆彈，下修為1口並拉寬停損至290.5卡死2萬金盾。"},
    {"rank": "🥉 3", "ticker": "3042", "name": "晶技(期)", "tool": "個股期", "size": "2口", "trigger": 217.5, "stop": 222.5, "t1": 207.5, "shares": 4000, "max_loss": 20000, "reason": "認購權證賣超2065萬避險回吐，實體破217.5追擊短線假突破回測。"},
    {"rank": "4", "ticker": "2455", "name": "全新(期)", "tool": "個股期", "size": "1口", "trigger": 551.0, "stop": 561.0, "t1": 541.0, "shares": 2000, "max_loss": 20000, "reason": "下修為1口，停損放寬至561，摜破551確認處置流動性枯竭崩跌。"},
    {"rank": "5", "ticker": "2327", "name": "國巨(期)", "tool": "個股期", "size": "1口", "trigger": 598.0, "stop": 608.0, "t1": 588.0, "shares": 2000, "max_loss": 20000, "reason": "高檔爆量分歧換手，下修為1口合規出戰，停損設608卡滿2萬金盾。"}
]

ORDERS_CLAUDE_S2R1 = [
    {"rank": "🥇 1", "ticker": "2344", "name": "華邦電(期)", "tool": "個股期", "size": "1口", "trigger": 179.0, "stop": 188.5, "t1": 160.0, "shares": 2000, "max_loss": 19000, "reason": "量化評分 80.5，未觸及不空條件，停損9.5點高容錯防守。"},
    {"rank": "🥈 2", "ticker": "8039", "name": "台虹(期)", "tool": "個股期", "size": "1口", "trigger": 299.0, "stop": 308.5, "t1": 280.0, "shares": 2000, "max_loss": 19000, "reason": "量化評分 80.0，融資暴增踩踏未爆彈，寬幅防守金盾合規。"},
    {"rank": "🥉 3", "ticker": "3406", "name": "玉晶光(期)", "tool": "個股期", "size": "1口", "trigger": 955.0, "stop": 964.0, "t1": 937.0, "shares": 2000, "max_loss": 18000, "reason": "量化評分 71.0，千金高價股奇兵，防守9點金盾合規。"},
    {"rank": "4", "ticker": "2313", "name": "華通(期)", "tool": "個股期", "size": "1口", "trigger": 224.5, "stop": 234.0, "t1": 205.5, "shares": 2000, "max_loss": 19000, "reason": "量化評分 62.5，其餘8檔因近20日強勢、外資鎖碼等不空硬濾網淘汰。"}
]

# ==============================================================================
# 5. 技術分析與動態 K 線指標模組
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
# 6. 量化撮合與方案 A 階梯結算引擎
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
            "pnl_points": pts, "pnl_ntd": effective_loss, "note": f"盤中突破停損價 {stop_p}，依紀律立即停損出場。"
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
# 7. 融資大數據模組
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
# 9. 側邊欄控制台 (三 AI 並列與最新風控規則)
# ==============================================================================
st.sidebar.title("⚔️ S2 三方鼎立控制台")
st.sidebar.markdown(f"**決戰輪次**：`Season 2 Round 1` ({S2_R1_DATE})")
st.sidebar.markdown(f"**母池籌碼基準**：`{DATA_BASE_DATE}` 三維完整大數據")

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 第二季起跑淨值儀表板")
st.sidebar.markdown(f"""
<div class="metric-card-gemini">
    <div style="font-size: 12px; color: #BBB;">🟥 Gemini 戰情室 (S1 總冠軍)</div>
    <div style="font-size: 20px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_GEMINI:,}</div>
    <div style="font-size: 11px; color: #FFD700;">第 2 季平手起跑</div>
</div>
<div class="metric-card-gpt">
    <div style="font-size: 12px; color: #BBB;">🟦 ChatGPT 戰情室 (S1 亞軍)</div>
    <div style="font-size: 20px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CHATGPT:,}</div>
    <div style="font-size: 11px; color: #FFD700;">第 2 季平手起跑</div>
</div>
<div class="metric-card-claude">
    <div style="font-size: 12px; color: #BBB;">🟪 Claude 戰情室 (全新參戰挑戰者)</div>
    <div style="font-size: 20px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CLAUDE:,}</div>
    <div style="font-size: 11px; color: #E1BEE7;">第 2 季平手起跑</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.info(f"""
🚩 **起跑差距**：三方平手 (NT$ 0)

📋 **S2 最新資金規則 (裁判長裁定)**：
• **起始本金**：各陣營 NT$ 1,000,000
• **分級口數上限**：
  - 2344 華邦電、3042 晶技、2313 華通：**最多 2 口**
  - 其餘 9 檔股票池：**最多 1 口**
• **單檔保證金**：不設上限
• **總保證金占用**：任一時點 **≤ NT$ {MAX_ACCOUNT_MARGIN:,}**
• **佇列順位**：同時觸發依 TOP 1~5 順序建倉，滿額鎖單
• **風控金盾**：單筆最大停損 **≤ NT$ {MAX_STOP_LOSS_NTD:,}**
• **鎖利模式**：方案 A 觸及 T1 立即全平保底
""")

# ==============================================================================
# 10. 主頁面六大核心分頁
# ==============================================================================
st.title("⚔️️ 三 AI 量化短空競賽｜第二場（Season 2）Round 1 旗艦戰情室")
st.caption(f"官方公證生效日：{S2_R1_DATE} 週一開盤｜基準數據：{DATA_BASE_DATE} 臺灣證交所融資券/主力分點/自營商權證金流")

tab_workspace, tab_broker, tab_margin, tab_orders, tab_radar, tab_s1_hall = st.tabs([
    "🖥️ 專業操盤工作台 (K線與分點)",
    "🏢 主力分點 (10/02 全景矩陣總表)",
    "📈 融資增減 (10/02 官方增減排行)",
    "⚔️ S2-R1 三方官方決戰名冊", 
    "📊 12檔母池籌碼雷達全景表",
    "👑 Season 1 榮譽總冠軍名人堂"
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
# TAB 2: 🏢 主力分點全景矩陣總表
# ------------------------------------------------------------------------------
with tab_broker:
    st.subheader(f"🏢 12 檔母池主力關鍵分點全景矩陣總表 ({DATA_BASE_DATE} 盤後真實撮合)")
    st.caption("⚡ 免逐檔切換！單一總表直接展開前五大買超/賣超主力與總量，滑鼠輕鬆滾動一覽無遺。")

    matrix_rows = []
    for item in DEFAULT_WATCHLIST_S2R1:
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

        if c_code == "2344":
            diag = "🚨 站前狂倒萬張，融資大接刀套牢"
        elif c_code == "6173":
            diag = "🎯 留長上影線，融資大退，連三日認售第1"
        elif c_code == "8039":
            diag = "🚨 尾盤急拉引爆融資暴增，外資趁高全線提款"
        elif c_code == "2455":
            diag = "⚡ 處置土洋極限對決，群益金鼎狂倒21%"
        elif c_code == "3042":
            diag = "🟡 認購賣超2065萬回吐，短線過熱"
        elif c_code in ["2327", "2492", "3037"]:
            diag = "🛑 外資天量狂掃/強鎖漲停主升浪"
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
            "籌碼多空結構診斷": st.column_config.TextColumn("籌碼多空結構診斷", width=260),
        }
    )

# ------------------------------------------------------------------------------
# TAB 3: 📈 融資增減
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
# TAB 4: S2-R1 三方正式決戰名冊 (含下嵌結算仲裁模擬台)
# ------------------------------------------------------------------------------
with tab_orders:
    st.subheader("⚔️ S2-R1 三大 AI 官方決戰名冊陣列 (三方鼎立旗艦版)")
    st.caption("公證核定：起始本金各 NT$ 1,000,000；華邦電/晶技/華通最多 2 口，其餘最多 1 口；總保證金占用上限 100 萬；單筆停損 ≤ NT$ 20,000；命中 T1 方案 A 全平保底。")
    
    col_g, col_c, col_cl = st.columns(3)
    
    with col_g:
        st.markdown("#### 🟥 Gemini 戰情室 S2-R1")
        st.caption("起始本金：NT$ 1,000,000 ｜ 依新規分級口數校準")
        df_gem_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "口數": x['size'], "最大風險": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_GEMINI_S2R1
        ])
        st.dataframe(df_gem_ui, use_container_width=True, hide_index=True)
        with st.expander("🔍 查看 Gemini 策略與籌碼依據", expanded=False):
            for x in ORDERS_GEMINI_S2R1:
                st.markdown(f"**{x['rank']} {x['name']} ({x['size']})**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']:.1f}`**")
                st.caption(f"└ {x['reason']}")
                
    with col_c:
        st.markdown("#### 🟦 ChatGPT 戰情室 S2-R1")
        st.caption("起始本金：NT$ 1,000,000 ｜ 依新規修正為 1 口合規單")
        df_gpt_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "口數": x['size'], "最大風險": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_CHATGPT_S2R1
        ])
        st.dataframe(df_gpt_ui, use_container_width=True, hide_index=True)
        with st.expander("🔍 查看 ChatGPT 策略與籌碼依據", expanded=False):
            for x in ORDERS_CHATGPT_S2R1:
                st.markdown(f"**{x['rank']} {x['name']} ({x['size']})**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']:.1f}`**")
                st.caption(f"└ {x['reason']}")

    with col_cl:
        st.markdown("#### 🟪 Claude 戰情室 S2-R1 (新參戰)")
        st.caption("起始本金：NT$ 1,000,000 ｜ 4 檔精選 (8檔觸發不空濾網)")
        df_claude_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "口數": x['size'], "最大風險": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_CLAUDE_S2R1
        ])
        st.dataframe(df_claude_ui, use_container_width=True, hide_index=True)
        with st.expander("🔍 查看 Claude 策略與籌碼依據", expanded=False):
            for x in ORDERS_CLAUDE_S2R1:
                st.markdown(f"**{x['rank']} {x['name']} ({x['size']})**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']:.1f}`**")
                st.caption(f"└ {x['reason']}")

    st.markdown("---")
    st.subheader("🛑 S2-R1 三方官方禁空名單（NO SHORT LIST）對照")
    cn1, cn2, cn3 = st.columns(3)
    cn1.error("🚫 **Gemini 禁空**：\n• 2327 國巨* (認購爆買+2981萬軋空)\n• 2492 華新科 (強攻漲停鎖主升浪)\n• 3037 欣興 (美林高盛暴買4000張)")
    cn2.error("🚫 **ChatGPT 禁空**：\n• 2492 華新科 (強嘎空結構)\n• 3189 景碩 (法人買超融資退)\n• 3037 欣興、6173 信昌電\n• 2408 南亞科、3406 玉晶光")
    cn3.error("🚫 **Claude 4大不空條件淘汰8檔**：\n• 20日漲幅≥5%不空：國巨、晶技、信昌電、全新、景碩、欣興、華新科\n• 外資鎖碼/逼近漲停不空：南亞科、欣興、華新科\n• 融資大減洗淨不空：景碩")

    st.markdown("---")
    
    # --------------------------------------------------------------------------
    # 🧮 內嵌：裁判長即時撮合與結算仲裁模擬台 (支援三方切換)
    # --------------------------------------------------------------------------
    with st.expander("⚖️ 裁判室專用：5分K實體跌破撮合與方案 A 結算模擬器 (點擊展開操作)", expanded=True):
        st.caption("依據官方公約：取不利撮合價進場，盤中穿破 T1 即刻鎖利全平，未達條件者於 13:25 強制結算。")
        
        sim_c1, sim_c2 = st.columns(2)
        with sim_c1:
            st.markdown("**步驟 1：選擇審查陣營與封單**")
            selected_side = st.radio("參賽陣營：", ["🟥 Gemini 戰情室", "🟦 ChatGPT 戰情室", "🟪 Claude 戰情室"], horizontal=True, key="embedded_sim_side")
            if "Gemini" in selected_side:
                order_set = ORDERS_GEMINI_S2R1
            elif "ChatGPT" in selected_side:
                order_set = ORDERS_CHATGPT_S2R1
            else:
                order_set = ORDERS_CLAUDE_S2R1
            
            target_order = st.selectbox(
                "選擇審查封單：", order_set,
                format_func=lambda x: f"{x['rank']} {x['name']} ({x['size']} | 門檻 < {x['trigger']:.1f}, 停損: {x['stop']:.1f}, T1: {x['t1']:.1f})",
                key="embedded_sim_order"
            )
            
            st.markdown("**步驟 2：輸入盤面 5 分 K 實體與走勢價位**")
            k_open_in = st.number_input("觸發 5 分 K 開盤價：", value=float(target_order["trigger"]) + 1.0, step=0.5, key="sim_k_o")
            k_close_in = st.number_input("觸發 5 分 K 收盤價：", value=float(target_order["trigger"]) - 0.5, step=0.5, key="sim_k_c")
            next_open_in = st.number_input("次一根 5 分 K 開盤價：", value=float(target_order["trigger"]) - 1.0, step=0.5, key="sim_next_o")
            k_high_in = st.number_input("盤中最高價 (檢驗停損)：", value=float(target_order["stop"]) - 1.0, step=0.5, key="sim_k_h")
            k_low_in = st.number_input("盤中最低價 (檢驗方案 A T1)：", value=float(target_order["t1"]) - 1.0, step=0.5, key="sim_k_l")
            exit_close_in = st.number_input("13:25 尾盤強制平倉價 (備用)：", value=float(target_order["trigger"]) - 2.0, step=0.5, key="sim_k_exit")
            
        with sim_c2:
            st.markdown("**步驟 3：官方仲裁自動計算結果**")
            res = execute_quant_settlement(
                order=target_order,
                k_open=k_open_in, k_close=k_close_in, k_low=k_low_in, k_high=k_high_in,
                next_k_open=next_open_in, exit_k_close=exit_close_in
            )
            
            st.info(f"**判定狀態**：{res['status']}")
            if res["entry_price"] is not None:
                st.write(f"- **核定部位口數**：`{target_order['size']} ({target_order['shares']:,} 股)`")
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
# TAB 6: 👑 首季總冠軍名人堂 (置底歸檔)
# ------------------------------------------------------------------------------
with tab_s1_hall:
    st.subheader("👑 第一場 (Season 1) 總冠軍名人堂檔案庫 (公證永久封存)")
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("首季總冠軍", "🟥 Gemini 戰情室", "11勝 6負 3平")
    c_m2.metric("首季終局淨值", "NT$ 1,743,595", "+74.36%")
    c_m3.metric("首季總獲利差距", "NT$ 331,914 領先", "亞軍 GPT: $1,411,681")
    st.caption("第一季 20 回合各輪對決詳細紀錄已完整歸檔，第二場賽事自 2026/10/05 開賽，三方各 100 萬重新起跑！")

# ==============================================================================
# 11. 系統頁尾
# ==============================================================================
st.markdown("---")
st.caption(f"三 AI 量化短空雷達系統 v22.1 (S2-R1 三方鼎立裁判長版)｜{S2_R1_DATE} 週一開盤生效｜執法公約：分級固定口數 + 帳戶總保證金 100 萬上限 + 5分K黑棒跌破 + 不利滑價撮合 + 2萬金盾停損 + 方案A全平 + 13:25強平")
