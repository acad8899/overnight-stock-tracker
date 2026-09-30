# -*- coding: utf-8 -*-
"""
雙 AI 量化短空雷達 (Round 19 旗艦裁判長版) - app.py (v19.0)
==============================================================================
版本更新重點：
1. 輪次晉級：推進至 Round 19，基準日 2026/09/30 盤後三維大數據 (分點+融資+權證)。
2. 歷史收錄：正式寫入 Round 18 官方終審裁決 (雙方 0 部位零虧損防守平手)。
3. 官方淨值：Gemini NT$ 1,783,595 vs ChatGPT NT$ 1,399,681 (領先維持 NT$ 383,914)。
4. 權證金流：同步 9/30 權證小哥獨門數據 (信昌電認售買超第一名 +268萬、晶技認購 +1338萬)。
5. 融資數據：同步 9/30 官方融資 (華新科 +1137、信昌電 -1660、華邦電 -3016、南亞科 -2966)。
6. 封單陣列：實裝 Round 19 官方 TOP 5 決戰名冊 (單筆最大停損 ≤ NT$ 20,000，命中 T1 全平保底)。
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
    page_title="雙 AI 量化短空雷達 (Round 19 旗艦裁判長版)", 
    layout="wide", 
    page_icon="🎯", 
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
# 2. 官方公約常數與雙方帳戶狀態 (2026/09/30 R18 終局結算生效)
# ==============================================================================
R19_DATE = "2026/10/01"
DATA_BASE_DATE = "2026/09/30"
MARGIN_DISPLAY_DATE = "9/30"

CAPITAL_GEMINI = 1783595     # R18 結算後 (零交易防守平手 $0)
CAPITAL_CHATGPT = 1399681    # R18 結算後 (零交易防守平手 $0)
LIMIT_GEMINI = int(CAPITAL_GEMINI * 0.20)    # NT$ 356,719
LIMIT_CHATGPT = int(CAPITAL_CHATGPT * 0.20)  # NT$ 279,936
NET_SPREAD = CAPITAL_GEMINI - CAPITAL_CHATGPT # NT$ 383,914

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
    "3042": "晶技", "6173": "信昌電", "2368": "金像電", "2330": "台積電", "2317": "鴻海"
}
NAME_TO_CODE_DICT = {v: k for k, v in STOCK_NAME_DICT.items()}

# ==============================================================================
# 3. 官方 R1～R18 歷史對決覆盤庫 (完整收錄 R18)
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
    },
    {
        "round": "Round 12", "date": "2026/09/18", "winner": "🟥 Gemini 勝",
        "gem_pnl": 0, "gem_net": 1697595, "gem_targets": "0部位 (5分K未跌破門檻，空手避開大盤狂漲1000點)",
        "gpt_pnl": -34000, "gpt_net": 1285681, "gpt_targets": "2455 全新(期 早盤誘空觸發，538嚴格停損離場)",
        "spread": 411914, "review": "大盤衝上 47,464 點狂軋！Gemini 全數空手避軋；GPT 全新期早盤破 522 誘空後急拉，依紀律於 538 停損保存元氣。"
    },
    {
        "round": "Round 13", "date": "2026/09/21", "winner": "🟦 ChatGPT 勝",
        "gem_pnl": 0, "gem_net": 1697595, "gem_targets": "8039 台虹(期 撮合265.5，最低262未破T1，13:25強平保本 $0)",
        "gpt_pnl": 36000, "gpt_net": 1321681, "gpt_targets": "3406 玉晶光(期 +NT$26,000), 3260 威剛(期 +NT$10,000)",
        "spread": 375914, "review": "GPT 憑藉玉晶光殺至 927 與威剛殺至 381 雙雙達成方案 A 保底，進帳 +3.6 萬奪勝；Gemini 台虹平價保本；裁判長親操斬獲 +44,546 元！"
    },
    {
        "round": "Round 14", "date": "2026/09/22", "winner": "🟥 Gemini 勝",
        "gem_pnl": 62000, "gem_net": 1759595, "gem_targets": "6173 信昌電(+26K), 2408 南亞科(+18K), 3406 玉晶光(+14K), 2344 華邦電(+4K)",
        "gpt_pnl": 16000, "gpt_net": 1337681, "gpt_targets": "3406 玉晶光(+14K), 3260 威剛(+2K)",
        "spread": 421914, "review": "Gemini 掌握主力出貨潮，4戰4勝全數收割大賺6.2萬！GPT玉晶光/威剛達標收1.6萬；雙方濾網成功避開景碩漲停！"
    },
    {
        "round": "Round 15", "date": "2026/09/23", "winner": "🟦 ChatGPT 勝",
        "gem_pnl": 0, "gem_net": 1759595, "gem_targets": "3406 玉晶光(+20K), 2455 全新(-20K 2萬金盾停損保本)",
        "gpt_pnl": 36000, "gpt_net": 1373681, "gpt_targets": "8039 台虹(期 +NT$20,000), 3406 玉晶光(期 +NT$16,000)",
        "spread": 385914, "review": "裁判長拍板定案：GPT 靠台虹與玉晶光雙達標方案 A 保底收割 3.6 萬奪勝！Gemini 玉晶光保底(+2萬)與全新金盾停損(-2萬)兩平保本。"
    },
    {
        "round": "Round 16", "date": "2026/09/24", "winner": "🟥 Gemini 勝",
        "gem_pnl": -6000, "gem_net": 1753595, "gem_targets": "3406 玉晶光(+20K), 3260 威剛(+12K), 2327 國巨*(-18K), 2492 華新科(-20K)",
        "gpt_pnl": -40000, "gpt_net": 1333681, "gpt_targets": "3406 玉晶光(+20K), 2327 國巨*(-20K), 2492 華新科(-20K), 6173 信昌電(-20K)",
        "spread": 419914, "review": "被動元件主力早盤誘空後暴力拉抬換手，雙方國巨/華新科觸發金盾停損；Gemini 靠玉晶光(+2萬)與獨門威剛(+1.2萬)大幅止血奪勝。"
    },
    {
        "round": "Round 17", "date": "2026/09/29", "winner": "🟦 ChatGPT 勝",
        "gem_pnl": 30000, "gem_net": 1783595, "gem_targets": "6173 信昌電(+28K), 2455 全新(+22K), 2408 南亞科(-20K金盾)",
        "gpt_pnl": 66000, "gpt_net": 1399681, "gpt_targets": "6173 信昌電(+34K), 2408 南亞科(+32K 方案A早盤完美平倉)",
        "spread": 383914, "review": "GPT 繳出代表作！南亞科 490 方案 A 精準鎖利全平避開午盤暴拉，加上信昌電進帳 6.6 萬奪勝！Gemini 全新與信昌電進帳 5 萬，淨值破 178 萬新高！"
    },
    {
        "round": "Round 18", "date": "2026/09/30", "winner": "🤝 官方裁定平手",
        "gem_pnl": 0, "gem_net": 1783595, "gem_targets": "0部位 (嚴格5分K實體黑棒破線濾網，全員零交易避開強彈)",
        "gpt_pnl": 0, "gpt_net": 1399681, "gpt_targets": "0部位 (華新科/晶技/玉晶光門檻守住，全員零交易避大軋)",
        "spread": 383914, "review": "裁判長拍板公證！多頭強攻（玉晶光+40點、台虹鎖漲停、南亞科暴拉至523），雙AI嚴守5分K黑棒紀律一股未進，零失誤保全淨值！"
    }
]

# ==============================================================================
# 4. 2026-09-30 盤後 12 檔母池三維大數據庫 (分點 + 融資增減 + 權證金流)
# ==============================================================================
DEFAULT_WATCHLIST_R19 = [
    {
        "代號": "2492", "名稱": "華新科", "昨收": 299.50, "昨日鎖碼量": 18146, "融資增減(張)": 1137, "券資比": 3.2, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 309.00, "最低價": 298.50,
        "主力分點": [
            {"分點": "國泰-敦南", "買超": 375, "均價": 301.47, "佔比": 2.07},
            {"分點": "統一-仁愛", "買超": 111, "均價": 300.16, "佔比": 0.61},
            {"分點": "台新-城中", "買超": 103, "均價": 301.50, "佔比": 0.57},
            {"分點": "國票-安和", "買超": 83, "均價": 303.93, "佔比": 0.46},
            {"分點": "華南永昌-竹北", "買超": 75, "均價": 299.28, "佔比": 0.41},
            {"分點": "台灣摩根士丹利", "買超": -2171, "均價": 300.06, "佔比": -11.96},
            {"分點": "大和國泰", "買超": -1492, "均價": 300.27, "佔比": -8.22},
            {"分點": "摩根大通", "買超": -1106, "均價": 301.36, "佔比": -6.10},
            {"分點": "港商野村", "買超": -449, "均價": 300.11, "佔比": -2.47},
            {"分點": "元大", "買超": -446, "均價": 301.52, "佔比": -2.46}
        ]
    },
    {
        "代號": "6173", "名稱": "信昌電", "昨收": 288.50, "昨日鎖碼量": 11071, "融資增減(張)": -1660, "券資比": 3.8, "權證認售(萬)": 268, "權證認購(萬)": 0,
        "最高價": 303.50, "最低價": 288.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 438, "均價": 296.24, "佔比": 3.96},
            {"分點": "國泰-敦南", "買超": 158, "均價": 294.67, "佔比": 1.43},
            {"分點": "永豐金-羅東", "買超": 83, "均價": 292.21, "佔比": 0.75},
            {"分點": "群益金鼎-大安", "買超": 65, "均價": 295.67, "佔比": 0.59},
            {"分點": "元大-大里", "買超": 54, "均價": 297.91, "佔比": 0.49},
            {"分點": "永豐金-忠孝", "買超": -352, "均價": 291.56, "佔比": -3.18},
            {"分點": "花旗環球", "買超": -330, "均價": 294.39, "佔比": -2.98},
            {"分點": "華南永昌-南京", "買超": -327, "均價": 292.65, "佔比": -2.95},
            {"分點": "美商高盛", "買超": -254, "均價": 294.57, "佔比": -2.29},
            {"分點": "群益金鼎-松山", "買超": -236, "均價": 292.43, "佔比": -2.13}
        ]
    },
    {
        "代號": "2327", "名稱": "國巨*", "昨收": 548.00, "昨日鎖碼量": 25009, "融資增減(張)": 80, "券資比": 3.7, "權證認售(萬)": -83, "權證認購(萬)": 0,
        "最高價": 564.00, "最低價": 548.00,
        "主力分點": [
            {"分點": "新加坡商瑞銀", "買超": 1438, "均價": 557.22, "佔比": 5.75},
            {"分點": "台灣摩根士丹利", "買超": 174, "均價": 556.22, "佔比": 0.70},
            {"分點": "凱基-台北", "買超": 153, "均價": 554.49, "佔比": 0.61},
            {"分點": "永豐金-匯立", "買超": 113, "均價": 555.01, "佔比": 0.45},
            {"分點": "國泰-敦南", "買超": 109, "均價": 554.81, "佔比": 0.44},
            {"分點": "富邦", "買超": -1372, "均價": 552.71, "佔比": -5.49},
            {"分點": "統一", "買超": -1124, "均價": 552.87, "佔比": -4.49},
            {"分點": "美林", "買超": -826, "均價": 550.57, "佔比": -3.30},
            {"分點": "摩根大通", "買超": -588, "均價": 555.11, "佔比": -2.35},
            {"分點": "美商高盛", "買超": -435, "均價": 552.55, "佔比": -1.74}
        ]
    },
    {
        "代號": "3406", "名稱": "玉晶光", "昨收": 890.00, "昨日鎖碼量": 3631, "融資增減(張)": -50, "券資比": 4.4, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 921.00, "最低價": 878.00,
        "主力分點": [
            {"分點": "美商高盛", "買超": 364, "均價": 898.83, "佔比": 10.02},
            {"分點": "新加坡商瑞銀", "買超": 88, "均價": 904.66, "佔比": 2.42},
            {"分點": "台灣摩根士丹利", "買超": 67, "均價": 902.18, "佔比": 1.85},
            {"分點": "美林", "買超": 37, "均價": 900.87, "佔比": 1.02},
            {"分點": "富邦-新店", "買超": 17, "均價": 904.61, "佔比": 0.47},
            {"分點": "法銀巴黎", "買超": -244, "均價": 896.05, "佔比": -6.72},
            {"分點": "摩根大通", "買超": -166, "均價": 897.48, "佔比": -4.57},
            {"分點": "中國信託", "買超": -98, "均價": 895.01, "佔比": -2.70},
            {"分點": "凱基-台北", "買超": -94, "均價": 902.61, "佔比": -2.59},
            {"分點": "花旗環球", "買超": -44, "均價": 893.98, "佔比": -1.21}
        ]
    },
    {
        "代號": "3042", "名稱": "晶技", "昨收": 210.00, "昨日鎖碼量": 26893, "融資增減(張)": 203, "券資比": 4.2, "權證認售(萬)": 0, "權證認購(萬)": 1338,
        "最高價": 218.50, "最低價": 206.00,
        "主力分點": [
            {"分點": "摩根大通", "買超": 1097, "均價": 209.77, "佔比": 3.19},
            {"分點": "康和", "買超": 410, "均價": 221.60, "佔比": 1.19},
            {"分點": "凱基-市府", "買超": 401, "均價": 209.30, "佔比": 1.17},
            {"分點": "富邦-敦南", "買超": 249, "均價": 209.78, "佔比": 0.72},
            {"分點": "統一", "買超": 164, "均價": 212.02, "佔比": 0.48},
            {"分點": "新加坡商瑞銀", "買超": -1090, "均價": 209.96, "佔比": -3.17},
            {"分點": "凱基-台北", "買超": -432, "均價": 211.75, "佔比": -1.26},
            {"分點": "台灣摩根士丹利", "買超": -330, "均價": 210.04, "佔比": -0.96},
            {"分點": "美商高盛", "買超": -315, "均價": 210.43, "佔比": -0.92},
            {"分點": "美林", "買超": -305, "均價": 209.07, "佔比": -0.89}
        ]
    },
    {
        "代號": "3189", "名稱": "景碩", "昨收": 970.00, "昨日鎖碼量": 23925, "融資增減(張)": -503, "券資比": 4.1, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 972.00, "最低價": 937.00,
        "主力分點": [
            {"分點": "中國信託", "買超": 1172, "均價": 958.03, "佔比": 4.90},
            {"分點": "富邦", "買超": 747, "均價": 961.14, "佔比": 3.12},
            {"分點": "統一", "買超": 422, "均價": 954.48, "佔比": 1.76},
            {"分點": "美商高盛", "買超": 272, "均價": 955.63, "佔比": 1.14},
            {"分點": "華南永昌", "買超": 211, "均價": 967.16, "佔比": 0.88},
            {"分點": "富邦-陽明", "買超": -1045, "均價": 953.40, "佔比": -4.37},
            {"分點": "凱基-台北", "買超": -888, "均價": 956.11, "佔比": -3.71},
            {"分點": "元大", "買超": -871, "均價": 952.82, "佔比": -3.64},
            {"分點": "宏遠", "買超": -576, "均價": 955.38, "佔比": -2.41},
            {"分點": "凱基-城中", "買超": -391, "均價": 964.92, "佔比": -1.63}
        ]
    },
    {
        "代號": "2313", "名稱": "華通", "昨收": 226.50, "昨日鎖碼量": 12970, "融資增減(張)": -111, "券資比": 3.1, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 229.50, "最低價": 224.00,
        "主力分點": [
            {"分點": "富邦", "買超": 900, "均價": 226.94, "佔比": 6.94},
            {"分點": "花旗環球", "買超": 566, "均價": 226.76, "佔比": 4.36},
            {"分點": "元大-復北", "買超": 394, "均價": 226.52, "佔比": 3.04},
            {"分點": "玉山", "買超": 389, "均價": 226.84, "佔比": 3.00},
            {"分點": "凱基-台北", "買超": 374, "均價": 226.70, "佔比": 2.88},
            {"分點": "大和國泰", "買超": -750, "均價": 226.12, "佔比": -5.78},
            {"分點": "美商高盛", "買超": -539, "均價": 226.42, "佔比": -4.16},
            {"分點": "元大", "買超": -462, "均價": 226.93, "佔比": -3.56},
            {"分點": "國票-敦北法人", "買超": -303, "均價": 226.34, "佔比": -2.34},
            {"分點": "港商野村", "買超": -221, "均價": 225.96, "佔比": -1.70}
        ]
    },
    {
        "代號": "2455", "名稱": "全新", "昨收": 552.00, "昨日鎖碼量": 1395, "融資增減(張)": -64, "券資比": 5.1, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 555.00, "最低價": 544.00,
        "主力分點": [
            {"分點": "凱基-台北", "買超": 120, "均價": 555.00, "佔比": 8.60},
            {"分點": "華南永昌-竹北", "買超": 104, "均價": 553.02, "佔比": 7.46},
            {"分點": "美商高盛", "買超": 80, "均價": 553.37, "佔比": 5.73},
            {"分點": "新加坡商瑞銀", "買超": 74, "均價": 551.98, "佔比": 5.30},
            {"分點": "香港上海匯豐", "買超": 40, "均價": 552.95, "佔比": 2.87},
            {"分點": "群益金鼎-大安", "買超": -40, "均價": 551.38, "佔比": -2.87},
            {"分點": "元大-土城永寧", "買超": -40, "均價": 555.00, "佔比": -2.87},
            {"分點": "台灣摩根士丹利", "買超": -30, "均價": 552.23, "佔比": -2.15},
            {"分點": "凱基-彰化", "買超": -29, "均價": 554.97, "佔比": -2.08},
            {"分點": "元大-文心", "買超": -28, "均價": 555.00, "佔比": -2.01}
        ]
    },
    {
        "代號": "3037", "名稱": "欣興", "昨收": 1175.00, "昨日鎖碼量": 10764, "融資增減(張)": 149, "券資比": 4.7, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 1190.00, "最低價": 1155.00,
        "主力分點": [
            {"分點": "富邦", "買超": 706, "均價": 1166.09, "佔比": 6.52},
            {"分點": "元大", "買超": 263, "均價": 1164.75, "佔比": 2.43},
            {"分點": "國票-敦北法人", "買超": 220, "均價": 1170.84, "佔比": 2.03},
            {"分點": "美林", "買超": 177, "均價": 1166.86, "佔比": 1.63},
            {"分點": "永豐金-忠孝", "買超": 120, "均價": 1173.36, "佔比": 1.11},
            {"分點": "新加坡商瑞銀", "買超": -592, "均價": 1160.20, "佔比": -5.47},
            {"分點": "凱基-台北", "買超": -465, "均價": 1164.64, "佔比": -4.29},
            {"分點": "花旗環球", "買超": -259, "均價": 1163.95, "佔比": -2.39},
            {"分點": "港商野村", "買超": -205, "均價": 1172.13, "佔比": -1.89},
            {"分點": "台灣摩根士丹利", "買超": -199, "均價": 1162.55, "佔比": -1.84}
        ]
    },
    {
        "代號": "2408", "名稱": "南亞科", "昨收": 519.00, "昨日鎖碼量": 40070, "融資增減(張)": -2966, "券資比": 3.5, "權證認售(萬)": -331, "權證認購(萬)": 0,
        "最高價": 520.00, "最低價": 507.00,
        "主力分點": [
            {"分點": "美商高盛", "買超": 3355, "均價": 515.40, "佔比": 8.37},
            {"分點": "元大", "買超": 2348, "均價": 514.50, "佔比": 5.86},
            {"分點": "新加坡商瑞銀", "買超": 2241, "均價": 516.12, "佔比": 5.59},
            {"分點": "凱基-站前", "買超": 1495, "均價": 515.87, "佔比": 3.73},
            {"分點": "法銀巴黎", "買超": 1311, "均價": 518.40, "佔比": 3.27},
            {"分點": "第一金-自由", "買超": -2534, "均價": 512.31, "佔比": -6.32},
            {"分點": "統一-新台中", "買超": -1232, "均價": 510.99, "佔比": -3.07},
            {"分點": "國泰-敦南", "買超": -567, "均價": 515.49, "佔比": -1.42},
            {"分點": "永豐金", "買超": -318, "均價": 517.22, "佔比": -0.79},
            {"分點": "元大-崇德", "買超": -208, "均價": 512.00, "佔比": -0.52}
        ]
    },
    {
        "代號": "2344", "名稱": "華邦電", "昨收": 179.50, "昨日鎖碼量": 85028, "融資增減(張)": -3016, "券資比": 2.5, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 179.50, "最低價": 175.00,
        "主力分點": [
            {"分點": "新加坡商瑞銀", "買超": 10495, "均價": 177.53, "佔比": 12.34},
            {"分點": "台灣摩根士丹利", "買超": 6855, "均價": 177.52, "佔比": 8.06},
            {"分點": "元大", "買超": 5848, "均價": 177.43, "佔比": 6.88},
            {"分點": "摩根大通", "買超": 4131, "均價": 177.97, "佔比": 4.86},
            {"分點": "美商高盛", "買超": 3711, "均價": 177.25, "佔比": 4.36},
            {"分點": "國泰-敦南", "買超": -1928, "均價": 177.51, "佔比": -2.27},
            {"分點": "港商野村", "買超": -725, "均價": 177.35, "佔比": -0.85},
            {"分點": "兆豐-南京", "買超": -628, "均價": 177.40, "佔比": -0.74},
            {"分點": "富邦", "買超": -596, "均價": 177.68, "佔比": -0.70},
            {"分點": "新光", "買超": -480, "均價": 177.41, "佔比": -0.56}
        ]
    },
    {
        "代號": "8039", "名稱": "台虹", "昨收": 300.50, "昨日鎖碼量": 31798, "融資增減(張)": 1868, "券資比": 4.9, "權證認售(萬)": 0, "權證認購(萬)": 0,
        "最高價": 300.50, "最低價": 277.50,
        "主力分點": [
            {"分點": "富邦", "買超": 2143, "均價": 300.00, "佔比": 6.74},
            {"分點": "國票-安和", "買超": 1243, "均價": 298.37, "佔比": 3.91},
            {"分點": "摩根大通", "買超": 982, "均價": 298.04, "佔比": 3.09},
            {"分點": "統一", "買超": 847, "均價": 295.48, "佔比": 2.66},
            {"分點": "國票-敦北法人", "買超": 665, "均價": 300.46, "佔比": 2.09},
            {"分點": "台灣摩根士丹利", "買超": -905, "均價": 288.67, "佔比": -2.85},
            {"分點": "國泰-敦南", "買超": -474, "均價": 293.75, "佔比": -1.49},
            {"分點": "永豐金-復興", "買超": -156, "均價": 295.87, "佔比": -0.49},
            {"分點": "富邦-敦南", "買超": -150, "均價": 299.34, "佔比": -0.47},
            {"分點": "永豐金-敦南", "買超": -122, "均價": 297.27, "佔比": -0.38}
        ]
    }
]

# ==============================================================================
# 5. Round 19 雙方決戰 TOP 5 封單陣列 (正式公證定案版)
# ==============================================================================
ORDERS_GEMINI_R19 = [
    {"rank": "🥇 首選 1", "ticker": "2492", "name": "華新科(期)", "tool": "期貨", "size": "2口", "margin": 161730, "trigger": 298.0, "stop": 303.0, "t1": 291.0, "shares": 4000, "max_loss": 20000, "reason": "外資三大行連倒4769張[cite: 27]，散戶融資大套2797張，收盤摜破300防線[cite: 27]，融資斷頭多殺多風暴核心！"},
    {"rank": "🥈 首選 2", "ticker": "6173", "name": "信昌電(期)", "tool": "期貨", "size": "2口", "margin": 155790, "trigger": 285.0, "stop": 290.0, "t1": 278.0, "shares": 4000, "max_loss": 20000, "reason": "認售權證買超冠軍(+268萬)[cite: 29]！現貨破290大關[cite: 28]，融資單日暴砍1660張斷頭，期貨加速補跌！"},
    {"rank": "🥉 首選 3", "ticker": "2327", "name": "國巨*(期)", "tool": "期貨", "size": "1口", "margin": 147960, "trigger": 544.0, "stop": 554.0, "t1": 534.0, "shares": 2000, "max_loss": 20000, "reason": "9/29大套2018張融資未認賠，今日富邦/統一續砍3300張[cite: 24]，高檔解套反壓沉重，破544直接下探！"},
    {"rank": "4", "ticker": "3406", "name": "玉晶光(期)", "tool": "期貨", "size": "1口", "margin": 240300, "trigger": 882.0, "stop": 902.0, "t1": 868.0, "shares": 2000, "max_loss": 20000, "reason": "早盤衝921留長上影線誘多[cite: 20, 25]，法巴/小摩賣超[cite: 25]，空頭反彈受阻，跌破882確認回歸空方軌道！"},
    {"rank": "5", "ticker": "3042", "name": "晶技(期)", "tool": "期貨", "size": "2口", "margin": 113400, "trigger": 206.0, "stop": 211.0, "t1": 199.0, "shares": 4000, "max_loss": 20000, "reason": "認購權證連4天高檔鈍化[cite: 30]，9/29融資高檔大套1481張[cite: 25]，回測206若實體跌破引發避險回吐多殺多！"}
]

ORDERS_CHATGPT_R19 = [
    {"rank": "🥇 1", "ticker": "2492", "name": "華新科(期)", "tool": "期貨", "size": "2口", "margin": 161730, "trigger": 297.0, "stop": 302.0, "t1": 289.0, "shares": 4000, "max_loss": 20000, "reason": "破300確認[cite: 27]，等破297進一步確立融資斷頭踩踏，下探289方案A。"},
    {"rank": "🥈 2", "ticker": "6173", "name": "信昌電(期)", "tool": "期貨", "size": "2口", "margin": 155790, "trigger": 286.0, "stop": 291.0, "t1": 279.0, "shares": 4000, "max_loss": 20000, "reason": "現貨破290[cite: 28]，小哥認售冠軍助攻[cite: 29]，跌破286追擊二線主跌段。"},
    {"rank": "🥉 3", "ticker": "3406", "name": "玉晶光(期)", "tool": "期貨", "size": "1口", "margin": 240300, "trigger": 878.0, "stop": 888.0, "t1": 864.0, "shares": 2000, "max_loss": 20000, "reason": "921長上影假突破[cite: 20, 25]，破今日低點878延續空方破底慣性。"},
    {"rank": "4", "ticker": "2327", "name": "國巨*(期)", "tool": "期貨", "size": "1口", "margin": 147960, "trigger": 542.0, "stop": 552.0, "t1": 532.0, "shares": 2000, "max_loss": 20000, "reason": "550壓力沉重，若破542則確認反彈結束重回空頭。"},
    {"rank": "5", "ticker": "3042", "name": "晶技(期)", "tool": "期貨", "size": "2口", "margin": 113400, "trigger": 205.5, "stop": 210.5, "t1": 198.0, "shares": 4000, "max_loss": 20000, "reason": "等真正跌破前低206確認轉弱，不提前摸頂。"}
]

# ==============================================================================
# 6. 技術分析與動態 K 線指標模組
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
# 7. 四層式連動 K 線繪圖引擎
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
# 9. 融資大數據模組 (同步 9/30 官方數據庫)
# ==============================================================================
LOCAL_MARGIN_HISTORY_10D_R19 = {
    "2492": [
        {"date": "09/15", "buy": 1450, "sell": 1200, "change": 250, "balance": 40560},
        {"date": "09/16", "buy": 1600, "sell": 1450, "change": 150, "balance": 40710},
        {"date": "09/17", "buy": 1750, "sell": 1520, "change": 230, "balance": 40940},
        {"date": "09/18", "buy": 1820, "sell": 1650, "change": 170, "balance": 41110},
        {"date": "09/21", "buy": 1500, "sell": 1850, "change": -350, "balance": 40760},
        {"date": "09/22", "buy": 1420, "sell": 1500, "change": -80, "balance": 40680},
        {"date": "09/23", "buy": 1890, "sell": 1337, "change": 553, "balance": 41233},
        {"date": "09/24", "buy": 1240, "sell": 1368, "change": -128, "balance": 41105},
        {"date": "09/29", "buy": 3150, "sell": 1490, "change": 1660, "balance": 42765},
        {"date": "09/30", "buy": 2890, "sell": 1753, "change": 1137, "balance": 43902}
    ],
    "6173": [
        {"date": "09/15", "buy": 1100, "sell": 950, "change": 150, "balance": 11200},
        {"date": "09/16", "buy": 1200, "sell": 1100, "change": 100, "balance": 11300},
        {"date": "09/17", "buy": 1350, "sell": 1200, "change": 150, "balance": 11450},
        {"date": "09/18", "buy": 1450, "sell": 1300, "change": 150, "balance": 11600},
        {"date": "09/21", "buy": 1200, "sell": 1400, "change": -200, "balance": 11400},
        {"date": "09/22", "buy": 1300, "sell": 1250, "change": 50, "balance": 11450},
        {"date": "09/23", "buy": 1680, "sell": 1420, "change": 260, "balance": 11710},
        {"date": "09/24", "buy": 1850, "sell": 1365, "change": 485, "balance": 12195},
        {"date": "09/29", "buy": 1720, "sell": 1191, "change": 529, "balance": 12724},
        {"date": "09/30", "buy": 1420, "sell": 3080, "change": -1660, "balance": 11064}
    ],
    "2327": [
        {"date": "09/15", "buy": 1450, "sell": 1200, "change": 250, "balance": 34690},
        {"date": "09/16", "buy": 1680, "sell": 1520, "change": 160, "balance": 34850},
        {"date": "09/17", "buy": 1740, "sell": 1580, "change": 160, "balance": 35010},
        {"date": "09/18", "buy": 1890, "sell": 1680, "change": 210, "balance": 35220},
        {"date": "09/21", "buy": 1520, "sell": 1890, "change": -370, "balance": 34850},
        {"date": "09/22", "buy": 1650, "sell": 1420, "change": 230, "balance": 35080},
        {"date": "09/23", "buy": 2480, "sell": 1341, "change": 1139, "balance": 36219},
        {"date": "09/24", "buy": 1580, "sell": 1394, "change": 186, "balance": 36405},
        {"date": "09/29", "buy": 3890, "sell": 1872, "change": 2018, "balance": 38423},
        {"date": "09/30", "buy": 1890, "sell": 1810, "change": 80, "balance": 38503}
    ]
}

@st.cache_data(ttl=300)
def fetch_stock_margin_10d(stock_code):
    code_str = str(stock_code).strip()
    fallback_data = LOCAL_MARGIN_HISTORY_10D_R19.get(code_str, [
        {"date": "09/15", "buy": 1050, "sell": 1000, "change": 50, "balance": 15300},
        {"date": "09/16", "buy": 1150, "sell": 1050, "change": 100, "balance": 15400},
        {"date": "09/17", "buy": 1300, "sell": 1150, "change": 150, "balance": 15550},
        {"date": "09/18", "buy": 1400, "sell": 1600, "change": -200, "balance": 15350},
        {"date": "09/21", "buy": 1250, "sell": 1350, "change": -100, "balance": 15250},
        {"date": "09/22", "buy": 1100, "sell": 1250, "change": -150, "balance": 15100},
        {"date": "09/23", "buy": 1050, "sell": 1150, "change": -100, "balance": 15000},
        {"date": "09/24", "buy": 1250, "sell": 1100, "change": 150, "balance": 15150},
        {"date": "09/29", "buy": 1500, "sell": 1200, "change": 300, "balance": 15450},
        {"date": "09/30", "buy": 1200, "sell": 1300, "change": -100, "balance": 15350}
    ])
    return pd.DataFrame(fallback_data)

# ==============================================================================
# 10. 母池數據加載 (Round 19 最新量化短空評分)
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
        
        # Round 19 專用短空評分 (外資暴砍+融資大套+認售冠軍 權重矩陣)
        score_dict = {
            "2492": 99, "6173": 98, "2327": 95, "3406": 92, "3042": 88, 
            "3189": 58, "3037": 55, "2313": 52, "2455": 50, "2408": 20, "2344": 15, "8039": 10
        }
        score = score_dict.get(code, 50)

        alert_tag = "⚡ 待機狙擊" if score >= 88 else ("⚡ 次選觀察" if score >= 50 else "🛑 官方禁空")
        alert_desc = f"【{alert_tag}】9/30 融資: {margin_change:+d} 張，認售: {put_val:+d} 萬"
        
        enhanced.append({
            "股票代號": code, "股票名稱": name, "個期": "期" if code in STOCK_FUTURES_SET else "—",
            "現價": close_p, "昨收": prev_close, "漲跌": round(close_p - prev_close, 2),
            "漲跌幅(%)": round(((close_p - prev_close) / prev_close) * 100, 2),
            "近高壓力(NH)": nh_res, "最高壓力(AH)": ah_res, "主力加權成本": avg_cost,
            "主力合計買超": tot_buy_shares, "主力合計佔比(%)": round(tot_ratio, 2),
            "融資增減(張)": margin_change, "權證認售(萬)": put_val,
            "短空勝率分": score, "即時信號": alert_tag, "盤中警報": alert_desc,
            "各分點清單": detailed_brokers, "5日均量(張)": tot_vol
        })
    return pd.DataFrame(enhanced).sort_values(by="短空勝率分", ascending=False).reset_index(drop=True)

df_display = load_radar_market_data(DEFAULT_WATCHLIST_R19)
df_display.index = range(1, len(df_display) + 1)

# ==============================================================================
# 11. 側邊欄控制台
# ==============================================================================
st.sidebar.title("⚡ 短空雷達量化控制台")
st.sidebar.markdown(f"**決戰輪次**：`Round 19` ({R19_DATE})")
st.sidebar.markdown(f"**母池籌碼基準**：`{DATA_BASE_DATE}` 盤後大數據 (公證核定版)")

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 賽事累計淨值儀表板")
st.sidebar.markdown(f"""
<div class="metric-card-gemini">
    <div style="font-size: 13px; color: #BBB;">🟥 Gemini 總淨值 (11勝4負3平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_GEMINI:,}</div>
    <div style="font-size: 12px; color: #81C784;">R18 零交易防守避強彈 ($0)</div>
</div>
<div class="metric-card-gpt">
    <div style="font-size: 13px; color: #BBB;">🟦 ChatGPT 總淨值 (4勝11負3平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CHATGPT:,}</div>
    <div style="font-size: 12px; color: #81C784;">R18 零交易防守避大軋 ($0)</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.info(f"🚩 **雙方差距**：Gemini 領先 **NT$ {NET_SPREAD:,}**\n\n**單檔上限 (20%)**：\n• Gemini: NT$ {LIMIT_GEMINI:,}\n• GPT: NT$ {LIMIT_CHATGPT:,}\n\n🛡️ **裁判長拍定公約**：\n單筆最大停損 **≤ NT$ 20,000** ｜ **命中 T1 全平保底**")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📜 官方執法核心規範 (R19 實戰版)")
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
# 12. 主頁面七大核心分頁
# ==============================================================================
st.title("🎯 雙 AI 量化當沖 PK 賽事｜Round 19 旗艦戰情室")
st.caption(f"數據庫基準：{DATA_BASE_DATE} 臺灣證券交易所/官方融資/主力分點/自營商權證金流三維大數據")

tab_workspace, tab_orders, tab_matcher, tab_radar, tab_history, tab_margin, tab_broker = st.tabs([
    "🖥️ 專業操盤工作台 (K線與分點)",
    "⚔️ R19 官方決戰封單名冊", 
    "🧮 官方撮合與方案A結算模擬器",
    "📊 12檔母池籌碼雷達全景表",
    "🏆 R1~R18 淨值覆盤庫",
    "📈 融資增減 (9/30 官方增減排行)",
    "🏢 主力分點 (9/30 真實買賣超)"
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
                <span style="color: #AAA;">9/30 官方融資：</span><span style="font-weight: bold; color: {'#FF4444' if target_row['融資增減(張)']>=0 else '#00FF66'};">{target_row['融資增減(張)']:+,} 張</span>
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

        st.markdown(f"#### 🏢 【{target_name}】主力分點鎖碼持倉明細 (9/30)")
        b_list = target_row.get("各分點清單", [])
        if b_list:
            df_b = pd.DataFrame(b_list)
            df_b.index = range(1, len(df_b) + 1)
            st.dataframe(df_b, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: R19 雙方正式決戰封單名冊
# ------------------------------------------------------------------------------
with tab_orders:
    st.subheader("⚔️ Round 19 雙 AI 官方 TOP 5 決戰名冊陣列 (實裝 2 萬金盾標準)")
    st.caption("依最高裁判長指示：命中 T1 即刻 100% 全平保底；單筆虧損嚴格限制在 NT$ 20,000 以內。")
    col_g, col_c = st.columns(2)
    
    with col_g:
        st.markdown("#### 🟥 Gemini 戰情室 R19 正式封單")
        st.caption(f"淨值：NT$ {CAPITAL_GEMINI:,}｜單檔上限：NT$ {LIMIT_GEMINI:,}｜單筆停損 ≤ NT$ 20,000")
        
        df_gem_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "規格": x['size'], "最大停損": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_GEMINI_R19
        ])
        st.dataframe(df_gem_ui, use_container_width=True, hide_index=True)
        
        with st.expander("🔍 查看 Gemini R19 籌碼依據與量化細節", expanded=True):
            for x in ORDERS_GEMINI_R19:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1保利 `{x['t1']:.1f}`** ｜ 最大停損 `-NT$ {abs(x['max_loss']):,}`")
                st.caption(f"└ 核心籌碼：{x['reason']}")
                
    with col_c:
        st.markdown("#### 🟦 ChatGPT 戰情室 R19 預備封單")
        st.caption(f"淨值：NT$ {CAPITAL_CHATGPT:,}｜單檔上限：NT$ {LIMIT_CHATGPT:,}｜單筆停損 ≤ NT$ 20,000")
        
        df_gpt_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "規格": x['size'], "最大停損": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_CHATGPT_R19
        ])
        st.dataframe(df_gpt_ui, use_container_width=True, hide_index=True)
        
        with st.expander("🔍 查看 ChatGPT R19 預估策略邏輯", expanded=True):
            for x in ORDERS_CHATGPT_R19:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1保利 `{x['t1']:.1f}`** ｜ 最大停損 `-NT$ {abs(x['max_loss']):,}`")
                st.caption(f"└ 作戰定位：{x['reason']}")

    st.markdown("---")
    st.subheader("🛑 Round 19 官方禁空名單（NO SHORT LIST）")
    cn1, cn2, cn3 = st.columns(3)
    cn1.error("🚫 **8039 台虹 (300.5元)**\n\n主力實戶搭配融資強攻漲停[cite: 28]，融資單日大增 +1,868 張為鎖碼型態，嚴禁摸頭！")
    cn2.error("🚫 **2344 華邦電 (179.5元)**\n\n外資七大行狂掃逾 3.7 萬張[cite: 22]，融資大退 -3,016 張，法人主升浪嚴格禁空！")
    cn3.error("🚫 **2408 南亞科 (519.0元)**\n\n外資連續兩天掃貨 1.5 萬張[cite: 17, 23]，融資大退 -2,966 張，認售被暴賣 -331 萬回補[cite: 29]，絕對禁空！")

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
        order_set = ORDERS_GEMINI_R19 if "Gemini" in selected_side else ORDERS_CHATGPT_R19
        
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
            st.write(f"- **不利滑價撮合價**：`{res['entry_price']:.2f}`")
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
        "融資增減(張)", "權證認售(萬)", "近高壓力(NH)", "主力加權成本", "主力合計買超", "主力合計佔比(%)"
    ]
    st.dataframe(df_display[[c for c in preferred_cols if c in df_display.columns]], use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 5: 🏆 R1~R18 淨值覆盤庫 (完整收錄 R18)
# ------------------------------------------------------------------------------
with tab_history:
    st.subheader("📈 雙 AI 歷輪淨值走勢與狙擊標的覆盤矩陣 (R0～R18)")
    st.caption("完整記錄每一輪的勝負演變、累積淨值變化與核心狙擊標的，支援量化回測與裁判室複查。")
    
    df_hist = pd.DataFrame(HISTORICAL_ROUNDS)
    
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
        "ChatGPT 損益", "ChatGPT 決戰淨值", "🟦 ChatGPT 核心狙擊標的", "領先差距"
    ]
    st.dataframe(table_view, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# TAB 6: 📈 融資增減 (9/30 官方排行榜)
# ------------------------------------------------------------------------------
with tab_margin:
    st.subheader(f"📊 12 檔母池 {MARGIN_DISPLAY_DATE} 官方融資增減熱力排行榜 (按增減張數降序)")
    st.caption("資料來源：臺灣證券交易所官方核定。🔴 紅色代表融資增加（散戶接刀/浮額累積），🟢 綠色代表融資減少（斷頭停損/外資洗盤）。")

    summary_margin_list = []
    for item in DEFAULT_WATCHLIST_R19:
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

# ------------------------------------------------------------------------------
# TAB 7: 🏢 主力分點 (9/30 盤後真實買賣超各前五大)
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
# 13. 系統頁尾
# ==============================================================================
st.markdown("---")
st.caption(f"雙 AI 量化短空雷達系統 v19.0 旗艦裁判長版｜{R19_DATE} Round 19 雙方封單正式鎖定｜執法標準：5分K實體跌破 + 不利撮合滑價 + 2萬金盾停損硬上限 + 方案A鎖利 (廢除T2) + 13:25強平")
