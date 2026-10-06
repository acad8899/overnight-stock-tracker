# -*- coding: utf-8 -*-
"""
雙/三 AI 量化短空雷達 (S2-R3 三巨頭頂尖對決旗艦裁判長版) - app.py (v24.0)
==============================================================================
版本更新重點 (2026/10/06 盤後最新版)：
1. 歷史公證戰績全入庫：
   - 納入 S2-R2 最終公證結算 (GPT +24,608 / Claude +8,758 / Gemini -10,115)。
   - 同步收錄最高裁判長個人實戰戰績 (10筆7勝2負1平，+36,351元，總資產 1,036,351)。
2. 10/06 最新母池大數據庫：
   - 全面更新 12 檔主力分點進出明細 (元大、大摩、花旗、凱基信義等)。
   - 官方融資增減全入庫 (華新科+1339、全新+395、景碩+386、信昌電-746、晶技-2748)。
   - 獨門權證認售/認購主力收購金流建檔 (信昌電認售+1641萬登榜首、國巨認購+1.5億)。
3. S2-R3 三方官方正式 TOP 5 封單陣列：
   - ChatGPT 戰情室：國巨 / 台虹 / 景碩 / 信昌電 / 華邦電 (排除華新科)。
   - Claude 戰情室：華新科 / 景碩 / 玉晶光 / 信昌電 / 台虹。
   - Gemini 戰情室：信昌電 / 全新 / 華新科 / 玉晶光 / 台虹。
4. 內嵌官方 5分K 實體黑棒判定與方案 A 撮合模擬器，支援 S2-R3 最新參數。
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
    page_title="三 AI 量化短空雷達 (S2-R3 官方決戰版)", 
    layout="wide", 
    page_icon="⚔️", 
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card-referee {
        background: linear-gradient(135deg, #1E1E1E 0%, #332B10 100%);
        border-radius: 8px;
        padding: 10px;
        border-left: 5px solid #FFD700;
        margin-bottom: 8px;
    }
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
# 2. 第二場公約常數與最新結算狀態 (2026/10/06 盤後核定)
# ==============================================================================
S2_R3_DATE = "2026/10/07"
DATA_BASE_DATE = "2026/10/06"
MARGIN_DISPLAY_DATE = "10/06"

# 官方公證累積最新淨值 (基底金 NT$ 1,000,000)
EQUITY_REFEREE = 1036351.00  # 裁判長 S2-R2: 10筆7勝2負1平 (+36,351元)
EQUITY_CHATGPT = 1004607.68  # GPT S2-R1: 979,999.68 -> S2-R2 (+24,608.00)
EQUITY_CLAUDE  = 979703.22   # Claude S2-R1: 970,945.22 -> S2-R2 (+8,758.00)
EQUITY_GEMINI  = 961705.08   # Gemini S2-R1: 971,820.08 -> S2-R2 (-10,115.00)

LIMIT_PER_STOCK = 200000     # 單檔部位上限 NT$ 200,000
MAX_STOP_LOSS_NTD = 20000    # 單筆 2 萬金盾最大停損

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
# 3. 2026-10-06 盤後 12 檔母池三維大數據庫 (主力分點/融資/權證收購表)
# ==============================================================================
DEFAULT_WATCHLIST_S2R3 = [
    {
        "代號": "6173", "名稱": "信昌電", "昨收": 284.00, "昨日鎖碼量": 5715, "融資增減(張)": -746, "券資比": 4.1, "權證認售(萬)": 1641, "權證認購(萬)": 0,
        "最高價": 298.50, "最低價": 284.00,
        "主力分點": [
            {"分點": "凱基-松山", "買超": 91, "均價": 288.89, "佔比": 1.59},
            {"分點": "永豐金-豐原", "買超": 72, "均價": 287.19, "佔比": 1.26},
            {"分點": "法銀巴黎", "買超": 65, "均價": 285.22, "佔比": 1.14},
            {"分點": "富邦-彰化", "買超": 58, "均價": 290.95, "佔比": 1.01},
            {"分點": "新加坡商瑞銀", "買超": 42, "均價": 291.06, "佔比": 0.73},
            {"分點": "富邦", "買超": -197, "均價": 294.72, "佔比": -3.45},
            {"分點": "國票-敦北法人", "買超": -102, "均價": 286.41, "佔比": -1.78},
            {"分點": "凱基", "買超": -100, "均價": 292.47, "佔比": -1.75},
            {"分點": "美商高盛", "買超": -90, "均價": 293.34, "佔比": -1.57},
            {"分點": "聯邦-忠孝", "買超": -64, "均價": 289.00, "佔比": -1.12}
        ]
    },
    {
        "代號": "2455", "名稱": "全新", "昨收": 567.00, "昨日鎖碼量": 16089, "融資增減(張)": 395, "券資比": 4.6, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 613.00, "最低價": 560.00,
        "主力分點": [
            {"分點": "新加坡商瑞銀", "買超": 317, "均價": 580.43, "佔比": 1.97},
            {"分點": "台新", "買超": 303, "均價": 585.73, "佔比": 1.88},
            {"分點": "國泰-敦南", "買超": 217, "均價": 584.26, "佔比": 1.35},
            {"分點": "奔亞證券", "買超": 151, "均價": 585.97, "佔比": 0.94},
            {"分點": "港商野村", "買超": 132, "均價": 580.66, "佔比": 0.82},
            {"分點": "台灣摩根士丹利", "買超": -669, "均價": 583.13, "佔比": -4.16},
            {"分點": "摩根大通", "買超": -522, "均價": 577.70, "佔比": -3.24},
            {"分點": "美商高盛", "買超": -464, "均價": 588.10, "佔比": -2.88},
            {"分點": "凱基-台北", "買超": -353, "均價": 586.69, "佔比": -2.19},
            {"分點": "第一金", "買超": -341, "均價": 582.33, "佔比": -2.12}
        ]
    },
    {
        "代號": "2492", "名稱": "華新科", "昨收": 389.50, "昨日鎖碼量": 56423, "融資增減(張)": 1339, "券資比": 3.8, "權證認售(萬)": 0, "權證認購(萬)": 6596,
        "最高價": 395.00, "最低價": 362.50,
        "主力分點": [
            {"分點": "花旗環球", "買超": 1446, "均價": 374.90, "佔比": 2.56},
            {"分點": "美林", "買超": 1112, "均價": 380.81, "佔比": 1.97},
            {"分點": "摩根大通", "買超": 898, "均價": 378.15, "佔比": 1.59},
            {"分點": "元大", "買超": 781, "均價": 377.95, "佔比": 1.38},
            {"分點": "富邦", "買超": 736, "均價": 384.52, "佔比": 1.30},
            {"分點": "凱基-台北", "買超": -1014, "均價": 377.59, "佔比": -1.80},
            {"分點": "美商高盛", "買超": -845, "均價": 376.96, "佔比": -1.50},
            {"分點": "台灣摩根士丹利", "買超": -422, "均價": 377.32, "佔比": -0.75},
            {"分點": "國泰-敦南", "買超": -332, "均價": 378.33, "佔比": -0.59},
            {"分點": "凱基-城中", "買超": -309, "均價": 391.00, "佔比": -0.55}
        ]
    },
    {
        "代號": "3042", "名稱": "晶技", "昨收": 204.50, "昨日鎖碼量": 25656, "融搞增減(張)": -2748, "券資比": 3.6, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 218.50, "最低價": 203.50,
        "主力分點": [
            {"分點": "凱基-台北", "買超": 226, "均價": 206.92, "佔比": 0.88},
            {"分點": "永豐金-南京", "買超": 220, "均價": 207.19, "佔比": 0.86},
            {"分點": "國票-天祥", "買超": 207, "均價": 205.22, "佔比": 0.81},
            {"分點": "國泰-敦南", "買超": 138, "均價": 208.51, "佔比": 0.54},
            {"分點": "新光", "買超": 127, "均價": 207.73, "佔比": 0.50},
            {"分點": "華南永昌", "買超": -1623, "均價": 207.92, "佔比": -6.33},
            {"分點": "統一", "買超": -561, "均價": 207.45, "佔比": -2.19},
            {"分點": "凱基-斗六", "買超": -299, "均價": 208.62, "佔比": -1.17},
            {"分點": "凱基", "買超": -296, "均價": 207.03, "佔比": -1.15},
            {"分點": "美商高盛", "買超": -292, "均價": 209.60, "佔比": -1.14}
        ]
    },
    {
        "代號": "3406", "名稱": "玉晶光", "昨收": 1045.00, "昨日鎖碼量": 8029, "融資增減(張)": 262, "券資比": 4.2, "權證認售(萬)": 368, "權證認購(萬)": 0,
        "最高價": 1095.00, "最低價": 1020.00,
        "主力分點": [
            {"分點": "新加坡商瑞銀", "買超": 186, "均價": 1047.75, "佔比": 2.32},
            {"分點": "中國信託", "買超": 130, "均價": 1058.90, "佔比": 1.62},
            {"分點": "華南永昌", "買超": 95, "均價": 1046.83, "佔比": 1.18},
            {"分點": "元大", "買超": 92, "均價": 1053.67, "佔比": 1.15},
            {"分點": "港商麥格理", "買超": 80, "均價": 1047.69, "佔比": 1.00},
            {"分點": "凱基-信義", "買超": -851, "均價": 1055.99, "佔比": -10.60},
            {"分點": "富邦", "買超": -266, "均價": 1058.08, "佔比": -3.31},
            {"分點": "花旗環球", "買超": -143, "均價": 1049.09, "佔比": -1.78},
            {"分點": "凱基-台北", "買超": -94, "均價": 1057.34, "佔比": -1.17},
            {"分點": "永豐金-匯立", "買超": -60, "均價": 1045.00, "佔比": -0.75}
        ]
    },
    {
        "代號": "8039", "名稱": "台虹", "昨收": 295.50, "昨日鎖碼量": 21600, "融資增減(張)": 190, "券資比": 4.7, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 305.50, "最低價": 291.50,
        "主力分點": [
            {"分點": "國泰-敦南", "買超": 241, "均價": 298.96, "佔比": 1.12},
            {"分點": "元大-彰化", "買超": 152, "均價": 299.11, "佔比": 0.70},
            {"分點": "群益金鼎-東大", "買超": 145, "均價": 301.98, "佔比": 0.67},
            {"分點": "凱基-市府", "買超": 95, "均價": 302.95, "佔比": 0.44},
            {"分點": "統一-三重", "買超": 82, "均價": 299.31, "佔比": 0.38},
            {"分點": "台灣摩根士丹利", "買超": -622, "均價": 299.33, "佔比": -2.88},
            {"分點": "元大", "買超": -528, "均價": 299.22, "佔比": -2.44},
            {"分點": "群益金鼎", "買超": -517, "均價": 298.00, "佔比": -2.39},
            {"分點": "美商高盛", "買超": -462, "均價": 299.43, "佔比": -2.14},
            {"分點": "元大-台北", "買超": -258, "均價": 295.83, "佔比": -1.19}
        ]
    },
    {
        "代號": "2327", "名稱": "國巨*", "昨收": 625.00, "昨日鎖碼量": 29671, "融資增減(張)": -87, "券資比": 3.7, "權證認售(萬)": 0, "權證認購(萬)": 15365,
        "最高價": 635.00, "最低價": 615.00,
        "主力分點": [
            {"分點": "富邦", "買超": 356, "均價": 623.97, "佔比": 1.20},
            {"分點": "凱基", "買超": 221, "均價": 623.26, "佔比": 0.74},
            {"分點": "國泰-敦南", "買超": 212, "均價": 623.66, "佔比": 0.71},
            {"分點": "花旗環球", "買超": 208, "均價": 623.88, "佔比": 0.70},
            {"分點": "摩根大通", "買超": 183, "均價": 623.38, "佔比": 0.62},
            {"分點": "元大", "買超": -1185, "均價": 623.71, "佔比": -3.99},
            {"分點": "兆豐", "買超": -711, "均價": 618.39, "佔比": -2.40},
            {"分點": "美林", "買超": -492, "均價": 624.51, "佔比": -1.66},
            {"分點": "凱基-桃園", "買超": -291, "均價": 622.94, "佔比": -0.98},
            {"分點": "永豐金", "買超": -274, "均價": 620.92, "佔比": -0.92}
        ]
    },
    {
        "代號": "3189", "名稱": "景碩", "昨收": 1070.00, "昨日鎖碼量": 10026, "融資增減(張)": 386, "券資比": 4.0, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 1105.00, "最低價": 1055.00,
        "主力分點": [
            {"分點": "富邦-新店", "買超": 519, "均價": 1078.69, "佔比": 5.18},
            {"分點": "台灣摩根士丹利", "買超": 368, "均價": 1075.38, "佔比": 3.67},
            {"分點": "摩根大通", "買超": 202, "均價": 1072.55, "佔比": 2.01},
            {"分點": "美林", "買超": 190, "均價": 1075.84, "佔比": 1.90},
            {"分點": "凱基-台北", "買超": 64, "均價": 1074.20, "佔比": 0.64},
            {"分點": "美商高盛", "買超": -463, "均價": 1073.68, "佔比": -4.62},
            {"分點": "元大", "買超": -389, "均價": 1076.37, "佔比": -3.88},
            {"分點": "群益金鼎-高盛", "買超": -215, "均價": 1079.55, "佔比": -2.14},
            {"分點": "永豐金-匯立", "買超": -190, "均價": 1070.61, "佔比": -1.90},
            {"分點": "港商野村", "買超": -182, "均價": 1070.68, "佔比": -1.82}
        ]
    },
    {
        "代號": "2344", "名稱": "華邦電", "昨收": 177.50, "昨日鎖碼量": 58643, "融資增減(張)": -452, "券資比": 2.6, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 183.00, "最低價": 177.50,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 6886, "均價": 179.67, "佔比": 11.74},
            {"分點": "美商高盛", "買超": 1170, "均價": 179.07, "佔比": 2.00},
            {"分點": "新加坡商瑞銀", "買超": 1160, "均價": 179.66, "佔比": 1.98},
            {"分點": "元大-館前", "買超": 979, "均價": 180.34, "佔比": 1.67},
            {"分點": "國泰", "買超": 391, "均價": 178.32, "佔比": 0.67},
            {"分點": "台新", "買超": -10580, "均價": 179.17, "佔比": -18.04},
            {"分點": "元大", "買超": -1527, "均價": 180.27, "佔比": -2.60},
            {"分點": "永豐金-匯立", "買超": -1055, "均價": 177.50, "佔比": -1.80},
            {"分點": "中國信託", "買超": -598, "均價": 178.58, "佔比": -1.02},
            {"分點": "富邦", "買超": -433, "均價": 180.96, "佔比": -0.74}
        ]
    },
    {
        "代號": "3037", "名稱": "欣興", "昨收": 1310.00, "昨日鎖碼量": 12776, "融資增減(張)": -76, "券資比": 4.3, "權證認售(萬)": 0, "權證認購(萬)": -6981,
        "最高價": 1340.00, "最低價": 1285.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 1506, "均價": 1311.63, "佔比": 11.79},
            {"分點": "新加坡商瑞銀", "買超": 1186, "均價": 1303.30, "佔比": 9.28},
            {"分點": "美商高盛", "買超": 371, "均價": 1304.80, "佔比": 2.90},
            {"分點": "美林", "買超": 270, "均價": 1305.81, "佔比": 2.11},
            {"分點": "摩根大通", "買超": 185, "均價": 1308.90, "佔比": 1.45},
            {"分點": "統一", "買超": -1098, "均價": 1299.42, "佔比": -8.59},
            {"分點": "永豐金-匯立", "買超": -632, "均價": 1318.01, "佔比": -4.95},
            {"分點": "富邦", "買超": -602, "均價": 1300.28, "佔比": -4.71},
            {"分點": "元大", "買超": -316, "均價": 1310.62, "佔比": -2.47},
            {"分點": "凱基-台北", "買超": -250, "均價": 1314.61, "佔比": -1.96}
        ]
    },
    {
        "代號": "2408", "名稱": "南亞科", "昨收": 525.00, "昨日鎖碼量": 30800, "融資增減(張)": -1259, "券資比": 3.1, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 535.00, "最低價": 524.00,
        "主力分點": [
            {"分點": "富邦", "買超": 3597, "均價": 529.78, "佔比": 11.68},
            {"分點": "統一", "買超": 380, "均價": 529.60, "佔比": 1.23},
            {"分點": "台灣摩根士丹利", "買超": 312, "均價": 530.57, "佔比": 1.01},
            {"分點": "美商高盛", "買超": 264, "均價": 530.75, "佔比": 0.86},
            {"分點": "玉山-城中", "買超": 254, "均價": 530.11, "佔比": 0.82},
            {"分點": "永豐金", "買超": -252, "均價": 530.41, "佔比": -0.82},
            {"分點": "大和國泰", "買超": -180, "均價": 528.03, "佔比": -0.58},
            {"分點": "凱基-台北", "買超": -173, "均價": 530.30, "佔比": -0.56},
            {"分點": "美林", "買超": -153, "均價": 527.89, "佔比": -0.50},
            {"分點": "台新", "買超": -134, "均價": 530.02, "佔比": -0.44}
        ]
    },
    {
        "代號": "2313", "名稱": "華通", "昨收": 252.00, "昨日鎖碼量": 97517, "融資增減(張)": -1939, "券資比": 3.0, "權證認售(萬)": -258, "權證認購(萬)": 0,
        "最高價": 256.00, "最低價": 245.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 9126, "均價": 252.50, "佔比": 9.36},
            {"分點": "美林", "買超": 4094, "均價": 252.38, "佔比": 4.20},
            {"分點": "摩根大通", "買超": 2875, "均價": 252.09, "佔比": 2.95},
            {"分點": "新加坡商瑞銀", "買超": 1566, "均價": 253.18, "佔比": 1.61},
            {"分點": "華南永昌", "買超": 1165, "均價": 252.43, "佔比": 1.19},
            {"分點": "元大", "買超": -5731, "均價": 251.83, "佔比": -5.88},
            {"分點": "富邦", "買超": -3711, "均價": 253.00, "佔比": -3.81},
            {"分點": "凱基-城中", "買超": -2040, "均價": 250.41, "佔比": -2.09},
            {"分點": "國票-敦北法人", "買超": -1708, "均價": 251.03, "佔比": -1.75},
            {"分點": "統一", "買超": -1377, "均價": 251.21, "佔比": -1.41}
        ]
    }
]

# ==============================================================================
# 4. 第三場 Round 3 三方官方定案封單陣列 (2026/10/07 決戰日)
# ==============================================================================
ORDERS_GEMINI_S2R3 = [
    {"rank": "🥇 1", "ticker": "6173", "name": "信昌電(期)", "tool": "個股期", "size": "1口", "trigger": 281.0, "stop": 289.5, "t1": 268.0, "shares": 2000, "max_loss": 17000, "reason": "認售收購表第1名(+1641萬)！避險共振，融資大退-746張收全天最低284元，破位順勢追殺。"},
    {"rank": "🥈 2", "ticker": "2455", "name": "全新(期)", "tool": "個股期", "size": "1口", "trigger": 562.0, "stop": 578.0, "t1": 535.0, "shares": 2000, "max_loss": 19000, "reason": "大摩/小摩/高盛三大外資聯手爆砍1650張收最低567元，散戶融資逆勢攤平+395張，主跌段多殺多。"},
    {"rank": "🥉 3", "ticker": "2492", "name": "華新科(期)", "tool": "個股期", "size": "1口", "trigger": 384.0, "stop": 395.0, "t1": 365.0, "shares": 2000, "max_loss": 19000, "reason": "融資兩天暴增4721張高檔慘套引信！凱基城中與高盛已高檔調節，破384確認外資買盤竭盡踩踏。"},
    {"rank": "4", "ticker": "3406", "name": "玉晶光(期)", "tool": "個股期", "size": "1口", "trigger": 1035.0, "stop": 1055.0, "t1": 995.0, "shares": 2000, "max_loss": 20000, "reason": "凱基信義等隔日沖主力大倒-851張出貨，認售權證買盤湧入(+368萬)，千元整數關卡面臨回測。"},
    {"rank": "5", "ticker": "8039", "name": "台虹(期)", "tool": "個股期", "size": "1口", "trigger": 293.0, "stop": 302.0, "t1": 279.0, "shares": 2000, "max_loss": 18000, "reason": "大摩、元大、群益、高盛外資自營主力集體調節逾2300張，短均下彎，反彈動能衰竭。"}
]

ORDERS_CHATGPT_S2R3 = [
    {"rank": "🥇 1", "ticker": "2327", "name": "國巨*(期)", "tool": "個股期", "size": "1口", "trigger": 615.0, "stop": 625.0, "t1": 605.0, "shares": 2000, "max_loss": 20000, "reason": "散戶爆買1.5億認購權證虛熱，元大主力狂倒1185張現貨背離，破615支撐發動假突破回測。"},
    {"rank": "🥈 2", "ticker": "8039", "name": "台虹(期)", "tool": "個股期", "size": "1口", "trigger": 291.0, "stop": 301.0, "t1": 281.0, "shares": 2000, "max_loss": 20000, "reason": "外資持續提款出貨收全日低檔，5分K實體跌破291確認空頭趨勢延續。"},
    {"rank": "🥉 3", "ticker": "3189", "name": "景碩(期)", "tool": "個股期", "size": "1口", "trigger": 1055.0, "stop": 1065.0, "t1": 1035.0, "shares": 2000, "max_loss": 20000, "reason": "外資高盛提款，散戶融資逆勢接刀+386張，摜破1055展開弱勢補跌。"},
    {"rank": "4", "ticker": "6173", "name": "信昌電(期)", "tool": "個股期", "size": "1口", "trigger": 284.0, "stop": 294.0, "t1": 274.0, "shares": 2000, "max_loss": 20000, "reason": "融資潰退-746張，成交量窒息收全天最低284元，實體收黑直接空。"},
    {"rank": "5", "ticker": "2344", "name": "華邦電(期)", "tool": "個股期", "size": "2口", "trigger": 177.0, "stop": 182.0, "t1": 167.0, "shares": 4000, "max_loss": 20000, "reason": "台新單一分點狂砍萬張賣壓壓制，實體摜破177發動2口第二段主跌段追殺。"}
]

ORDERS_CLAUDE_S2R3 = [
    {"rank": "🥇 1", "ticker": "2492", "name": "華新科(期)", "tool": "個股期", "size": "1口", "trigger": 389.0, "stop": 398.5, "t1": 370.0, "shares": 2000, "max_loss": 19071, "reason": "⚠ 補位單；凱基台北出貨1014張均價377.5；富邦南屯隔日沖187張明早倒貨；融資連增4700張多殺多。"},
    {"rank": "🥈 2", "ticker": "3189", "name": "景碩(期)", "tool": "個股期", "size": "1口", "trigger": 1055.0, "stop": 1060.0, "t1": 1045.0, "shares": 2000, "max_loss": 10124, "reason": "⚠ 補位單；美商高盛賣超463張均價1072.5；融資+386張接刀；超窄5點停損換取高盈虧比。"},
    {"rank": "🥉 3", "ticker": "3406", "name": "玉晶光(期)", "tool": "個股期", "size": "1口", "trigger": 1040.0, "stop": 1045.0, "t1": 1030.0, "shares": 2000, "max_loss": 10123, "reason": "凱基信義單一出貨851張均價1055.8；凱基鳳山隔日沖明早要倒；融資+262張散戶接單；極窄停損。"},
    {"rank": "4", "ticker": "6173", "name": "信昌電(期)", "tool": "個股期", "size": "1口", "trigger": 265.5, "stop": 275.0, "t1": 246.5, "shares": 2000, "max_loss": 19061, "reason": "收最低284留長上影線，門檻設在極端深水區265.5確認崩跌才建立部位。"},
    {"rank": "5", "ticker": "8039", "name": "台虹(期)", "tool": "個股期", "size": "1口", "trigger": 289.0, "stop": 298.5, "t1": 270.0, "shares": 2000, "max_loss": 19063, "reason": "大摩賣超622張出貨；統一三重隔日沖買超82張成本297.9明早要倒；外資大賣-1850張續弱。"}
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
# 6. 量化撮合與方案 A 階梯結算引擎 (嚴格遵守 5分K 實體黑棒)
# ==============================================================================
def execute_quant_settlement(order, k_open, k_close, k_low, k_high, next_k_open, exit_k_close=None):
    trigger_p = float(order["trigger"])
    stop_p = float(order["stop"])
    t1_p = float(order["t1"])
    shares = order["shares"]
    
    # 公約第 1 條：必須出現「實體黑棒 (Close < Open) 且收盤跌破門檻」
    if not (k_close < k_open and k_close < trigger_p):
        return {
            "status": "⚪ 沒觸發 (空手防守)", "entry_price": None, "exit_price": None,
            "pnl_points": 0.0, "pnl_ntd": 0, "note": f"5分K未收黑破門檻 {trigger_p}，空手觀望。"
        }
    
    # 公約第 2 條：取不利撮合滑價進場
    entry_p = min(k_close, next_k_open)
    
    # 公約第 3 條：檢驗停損 (嚴格鎖定在 2 萬金盾內)
    if k_high >= stop_p:
        pts = entry_p - stop_p
        loss_ntd = int(pts * shares)
        effective_loss = max(loss_ntd, -MAX_STOP_LOSS_NTD)
        return {
            "status": "❌ 停損平倉 (2萬金盾風控鎖定)", "entry_price": entry_p, "exit_price": stop_p,
            "pnl_points": pts, "pnl_ntd": effective_loss, "note": f"盤中突破停損價 {stop_p}，依紀律立即停損出場。"
        }
        
    # 公約第 4 條：方案 A 停利 (命中 T1 立即全平保底)
    if k_low <= t1_p:
        pts = entry_p - t1_p
        return {
            "status": "🎯 方案 A 停利 (命中 T1)", "entry_price": entry_p, "exit_price": t1_p,
            "pnl_points": pts, "pnl_ntd": int(pts * shares), "note": f"盤中低點穿破 T1 ({t1_p})，依方案 A 全數平倉保底！"
        }
        
    # 公約第 5 條：13:25 尾盤強制平倉
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
# 7. 融資大數據模組 (更新至 10/06 最新官方紀錄)
# ==============================================================================
LOCAL_MARGIN_HISTORY_10D_S2 = {
    "6173": [
        {"date": "09/23", "buy": 1680, "sell": 1420, "change": 260, "balance": 11710},
        {"date": "09/24", "buy": 1850, "sell": 1365, "change": 485, "balance": 12195},
        {"date": "09/29", "buy": 1720, "sell": 1191, "change": 529, "balance": 12724},
        {"date": "09/30", "buy": 1420, "sell": 3080, "change": -1660, "balance": 11064},
        {"date": "10/01", "buy": 1560, "sell": 2417, "change": -857, "balance": 10207},
        {"date": "10/02", "buy": 1240, "sell": 2340, "change": -1100, "balance": 9107},
        {"date": "10/05", "buy": 1420, "sell": 1950, "change": -530, "balance": 8577},
        {"date": "10/06", "buy": 950, "sell": 1696, "change": -746, "balance": 7831}
    ],
    "2492": [
        {"date": "09/23", "buy": 3200, "sell": 2800, "change": 400, "balance": 28500},
        {"date": "09/24", "buy": 3500, "sell": 3100, "change": 400, "balance": 28900},
        {"date": "09/29", "buy": 4200, "sell": 3800, "change": 400, "balance": 29300},
        {"date": "09/30", "buy": 5100, "sell": 4300, "change": 800, "balance": 30100},
        {"date": "10/01", "buy": 4800, "sell": 4500, "change": 300, "balance": 30400},
        {"date": "10/02", "buy": 3500, "sell": 4696, "change": -1196, "balance": 29204},
        {"date": "10/05", "buy": 8950, "sell": 5568, "change": 3382, "balance": 32586},
        {"date": "10/06", "buy": 7650, "sell": 6311, "change": 1339, "balance": 33925}
    ],
    "2455": [
        {"date": "09/23", "buy": 1100, "sell": 950, "change": 150, "balance": 15200},
        {"date": "09/24", "buy": 1250, "sell": 1100, "change": 150, "balance": 15350},
        {"date": "09/29", "buy": 1400, "sell": 1200, "change": 200, "balance": 15550},
        {"date": "09/30", "buy": 1600, "sell": 1300, "change": 300, "balance": 15850},
        {"date": "10/01", "buy": 1200, "sell": 1450, "change": -250, "balance": 15600},
        {"date": "10/02", "buy": 1150, "sell": 1424, "change": -274, "balance": 15326},
        {"date": "10/05", "buy": 1350, "sell": 1500, "change": -150, "balance": 15176},
        {"date": "10/06", "buy": 2150, "sell": 1755, "change": 395, "balance": 15571}
    ]
}

@st.cache_data(ttl=300)
def fetch_stock_margin_10d(stock_code):
    code_str = str(stock_code).strip()
    fallback_data = LOCAL_MARGIN_HISTORY_10D_S2.get(code_str, [
        {"date": "09/24", "buy": 1250, "sell": 1100, "change": 150, "balance": 15150},
        {"date": "09/29", "buy": 1500, "sell": 1200, "change": 300, "balance": 15450},
        {"date": "09/30", "buy": 1200, "sell": 1300, "change": -100, "balance": 15350},
        {"date": "10/01", "buy": 1300, "sell": 1350, "change": -50, "balance": 15300},
        {"date": "10/02", "buy": 1450, "sell": 1350, "change": 100, "balance": 15400},
        {"date": "10/05", "buy": 1600, "sell": 1400, "change": 200, "balance": 15600},
        {"date": "10/06", "buy": 1800, "sell": 1750, "change": 50, "balance": 15650}
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
            "6173": 99, "2455": 96, "2492": 93, "3042": 90, "3406": 87, 
            "8039": 84, "3189": 75, "2344": 65, "2327": 60, "2313": 20, "2408": 15, "3037": 10
        }
        score = score_dict.get(code, 50)
        alert_tag = "⚡ 待機狙擊" if score >= 85 else ("⚡ 次選觀察" if score >= 60 else "🛑 官方禁空")
        alert_desc = f"【{alert_tag}】10/06 融資: {margin_change:+d} 張，認售: {put_val:+d} 萬"
        
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

df_display = load_radar_market_data(DEFAULT_WATCHLIST_S2R3)
df_display.index = range(1, len(df_display) + 1)

# ==============================================================================
# 9. 側邊欄控制台 (真人裁判長與三大 AI 並列總天梯)
# ==============================================================================
st.sidebar.title("⚔️ S2-R3 戰情決策控制台")
st.sidebar.markdown(f"**決戰輪次**：`Season 2 Round 3` ({S2_R3_DATE})")
st.sidebar.markdown(f"**母池籌碼基準**：`{DATA_BASE_DATE}` 證交所官方盤後數據")

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 第二季公證總資產天梯榜")
st.sidebar.markdown(f"""
<div class="metric-card-referee">
    <div style="font-size: 12px; color: #FFD700; font-weight: bold;">👑 最高裁判長 (個人實戰專戶)</div>
    <div style="font-size: 21px; font-weight: bold; color: #FFF;">NT$ {int(EQUITY_REFEREE):,}</div>
    <div style="font-size: 11px; color: #FFD700;">R2淨賺 +NT$ 36,351 (勝率78%) 👑</div>
</div>
<div class="metric-card-gpt">
    <div style="font-size: 12px; color: #BBB;">🟦 ChatGPT 戰情室 (AI 榜首)</div>
    <div style="font-size: 20px; font-weight: bold; color: #FFF;">NT$ {int(EQUITY_CHATGPT):,}</div>
    <div style="font-size: 11px; color: #64B5F6;">S2-R2: +NT$ 24,608 (破百萬)</div>
</div>
<div class="metric-card-claude">
    <div style="font-size: 12px; color: #BBB;">🟪 Claude 戰情室 (AI 亞軍)</div>
    <div style="font-size: 20px; font-weight: bold; color: #FFF;">NT$ {int(EQUITY_CLAUDE):,}</div>
    <div style="font-size: 11px; color: #BA68C8;">S2-R2: +NT$ 8,758 (全新立功)</div>
</div>
<div class="metric-card-gemini">
    <div style="font-size: 12px; color: #BBB;">🟥 Gemini 戰情室 (伺機反攻)</div>
    <div style="font-size: 20px; font-weight: bold; color: #FFF;">NT$ {int(EQUITY_GEMINI):,}</div>
    <div style="font-size: 11px; color: #E57373;">S2-R2: -NT$ 10,115 (晶技落袋)</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.info(f"🛡️ **S2-R3 執法公約**：\n• 必須出現 5分K 實體黑棒且收破門檻\n• 單筆最大停損 **≤ NT$ 20,000 (金盾)**\n• 命中 T1 方案 A 立即全平保底\n• 13:25 尾盤強制市價平倉")

# ==============================================================================
# 10. 主頁面六大核心分頁
# ==============================================================================
st.title("⚔️ 三 AI 量化短空競賽｜第二場 (Season 2) Round 3 旗艦戰情室")
st.caption(f"官方公證生效日：{S2_R3_DATE} 開盤生效｜大數據依據：{DATA_BASE_DATE} 臺灣證券交易所官方主力分點/融資券/獨門權證收購表")

tab_workspace, tab_broker, tab_margin, tab_orders, tab_radar, tab_s2r2_report = st.tabs([
    "🖥️ 專業操盤工作台 (K線與分點)",
    "🏢 主力分點 (10/06 全景矩陣總表)",
    "📈 融資增減 (10/06 官方增減排行)",
    "⚔️ S2-R3 三方官方決戰名冊", 
    "📊 12檔母池籌碼雷達全景表",
    "📜 S2-R2 歷史公證戰果歸檔庫"
])

# ------------------------------------------------------------------------------
# TAB 1: 專業操盤工作台
# ------------------------------------------------------------------------------
with tab_workspace:
    left_side, right_side = st.columns([1.35, 3.65], gap="medium")
    
    with left_side:
        st.markdown("### 📋 短空鎖碼清單 (10/06 基準)")
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
                <span style="color: #AAA;">10/06 官方融資：</span><span style="font-weight: bold; color: {'#FF4444' if target_row['融資增減(張)']>=0 else '#00FF66'};">{target_row['融資增減(張)']:+,} 張</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px;">
                <span style="color: #AAA;">權證認售買超：</span><span style="font-weight: bold; color: {'#FF4444' if target_row['權證認售(萬)']>0 else '#FFF'};">{target_row['權證認售(萬)']:+,} 萬元</span>
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

        st.markdown(f"#### 🏢 【{target_name}】主力分點鎖碼持倉明細 (10/06 盤後)")
        b_list = target_row.get("各分點清單", [])
        if b_list:
            df_b = pd.DataFrame(b_list)
            df_b.index = range(1, len(df_b) + 1)
            st.dataframe(df_b, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: 🏢 主力分點全景矩陣總表 (10/06 盤後)
# ------------------------------------------------------------------------------
with tab_broker:
    st.subheader(f"🏢 12 檔母池主力關鍵分點全景矩陣總表 ({DATA_BASE_DATE} 官方盤後大數據)")
    st.caption("⚡ 免逐檔切換！單一總表直接展開前五大買超/賣超主力與總量，滾動滑鼠一覽無遺。")

    matrix_rows = []
    for item in DEFAULT_WATCHLIST_S2R3:
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

        if c_code == "6173":
            diag = "👑 認售收購第一名(+1641萬)，融資大退收最低"
        elif c_code == "2455":
            diag = "🚨 三大外資集體倒貨1650張，散戶融資逆勢接刀"
        elif c_code == "2492":
            diag = "⚡ 融資兩天暴增4721張慘套引信，外資高檔對敲"
        elif c_code == "3042":
            diag = "🚨 華南永昌單一狂砍1623張清倉，雪崩破底"
        elif c_code == "3406":
            diag = "⚡ 凱基信義等隔日沖倒貨851張，認售買盤湧入"
        elif c_code == "8039":
            diag = "🟠 大摩元大群益高盛主力集體提款逾2300張"
        elif c_code == "2327":
            diag = "🟡 散戶1.5億買認購虛熱，元大狂倒1185張現貨"
        elif c_code == "2344":
            diag = "⚡ 台新單一分點狂倒萬張，壓制大摩護盤"
        elif c_code in ["2313", "2408", "3037"]:
            diag = "🛑 法人天量鎖碼/保證金超標，官方嚴格禁空"
        else:
            diag = "⚪ 外資主力高檔震盪整理"

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
# TAB 3: 📈 融資增減 (10/06 官方排行榜)
# ------------------------------------------------------------------------------
with tab_margin:
    st.subheader(f"📊 12 檔母池 {MARGIN_DISPLAY_DATE} 官方融資增減排行榜 (按增減張數降序)")
    st.caption("資料來源：臺灣證券交易所官方公佈。🔴 紅色代表融資增加（散戶高檔接刀/追價慘套），🟢 綠色代表融資減少（斷頭停損/主力洗盤）。")

    summary_margin_list = []
    for item in DEFAULT_WATCHLIST_S2R3:
        c_code = item["代號"]
        c_name = item["名稱"]
        c_price = item["昨收"]
        df_10d = fetch_stock_margin_10d(c_code)
        
        last_chg
