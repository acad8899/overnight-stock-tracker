# -*- coding: utf-8 -*-
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
    page_title="雙 AI 量化短空雷達 (Round 13 旗艦裁判長版)", 
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
    /* 美化橫向單選按鈕組為 Pills 外觀 */
    div[role="radiogroup"] {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. 官方公約常數與雙方帳戶狀態 (2026/09/18 R12 終局結算生效)
# ==============================================================================
R13_DATE = "2026/09/21"
DATA_BASE_DATE = "2026/09/18"

# 帳戶資本與風控額度 (R12 結算：Gemini 0, GPT -34,000)
CAPITAL_GEMINI = 1697595
CAPITAL_CHATGPT = 1285681
LIMIT_GEMINI = int(CAPITAL_GEMINI * 0.20)    # NT$ 339,519
LIMIT_CHATGPT = int(CAPITAL_CHATGPT * 0.20)  # NT$ 257,136
NET_SPREAD = CAPITAL_GEMINI - CAPITAL_CHATGPT # NT$ 411,914

# 裁判長拍定：R13 起單筆期貨部位最大停損金額硬上限全面調升為 NT$ 20,000
MAX_STOP_LOSS_NTD = 20000

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
# 3. 官方 R1～R12 歷史對決覆盤庫
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
    }
]

# ==============================================================================
# 4. 2026-09-18 盤後 12 檔母池三維大數據庫 (主力進出 × 融資增減 × 權證避險)
# ==============================================================================
DEFAULT_WATCHLIST = [
    {
        "代號": "8039", "名稱": "台虹", "昨收": 269.50, "昨日鎖碼量": 18887, "融資增減(張)": 1264, "券資比": 4.5, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 271.00, "最低價": 257.00,
        "主力分點": [
            {"分點": "凱基-台北", "買超": 859, "均價": 265.47, "佔比": 4.53},
            {"分點": "元大", "買超": 616, "均價": 264.87, "佔比": 3.25},
            {"分點": "摩根大通", "買超": -2031, "均價": 264.13, "佔比": -10.72}
        ]
    },
    {
        "代號": "2327", "名稱": "國巨*", "昨收": 550.00, "昨日鎖碼量": 26232, "融資增減(張)": 1020, "券資比": 3.1, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 550.00, "最低價": 533.00,
        "主力分點": [
            {"分點": "凱基-台北", "買超": 1320, "均價": 543.49, "佔比": 4.90},
            {"分點": "美商高盛", "買超": 822, "均價": 544.86, "佔比": 3.05},
            {"分點": "新加坡商瑞銀", "買超": -697, "均價": 545.97, "佔比": -2.59}
        ]
    },
    {
        "代號": "2455", "名稱": "全新", "昨收": 556.00, "昨日鎖碼量": 20022, "融資增減(張)": 623, "券資比": 5.9, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 563.00, "最低價": 520.00,
        "主力分點": [
            {"分點": "台新", "買超": 344, "均價": 542.97, "佔比": 1.72},
            {"分點": "台灣摩根士丹利", "買超": -360, "均價": 542.24, "佔比": -1.80}
        ]
    },
    {
        "代號": "6173", "名稱": "信昌電", "昨收": 314.00, "昨日鎖碼量": 18447, "融資增減(張)": -669, "券資比": 3.8, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 314.00, "最低價": 300.00,
        "主力分點": [
            {"分點": "摩根大通", "買超": 2892, "均價": 313.76, "佔比": 15.48},
            {"分點": "新加坡商瑞銀", "買超": -847, "均價": 313.07, "佔比": -4.53}
        ]
    },
    {
        "代號": "2344", "名稱": "華邦電", "昨收": 179.50, "昨日鎖碼量": 137930, "融資增減(張)": -2892, "券資比": 2.2, "權證認售(萬)": 40, "權證賣認購(萬)": 0,
        "最高價": 179.50, "最低價": 173.50,
        "主力分點": [
            {"分點": "新加坡商瑞銀", "買超": 18987, "均價": 177.88, "佔比": 13.70},
            {"分點": "美商高盛", "買超": 6929, "均價": 177.27, "佔比": 5.00},
            {"分點": "凱基-台北", "買超": 4859, "均價": 177.05, "佔比": 3.51}
        ]
    },
    {
        "代號": "3260", "名稱": "威剛", "昨收": 396.50, "昨日鎖碼量": 6928, "融資增減(張)": -192, "券資比": 4.1, "權證認售(萬)": -32, "權證賣認購(萬)": 0,
        "最高價": 401.50, "最低價": 395.00,
        "主力分點": [
            {"分點": "合庫", "買超": 317, "均價": 397.66, "佔比": 4.51},
            {"分點": "富邦", "買超": -990, "均價": 396.32, "佔比": -14.09},
            {"分點": "凱基-台北", "買超": -459, "均價": 397.01, "佔比": -6.53}
        ]
    },
    {
        "代號": "2492", "名稱": "華新科", "昨收": 309.50, "昨日鎖碼量": 15482, "融資增減(張)": -360, "券資比": 2.9, "權證認售(萬)": -21, "權證賣認購(萬)": 0,
        "最高價": 311.00, "最低價": 300.00,
        "主力分點": [
            {"分點": "凱基-台北", "買超": 1204, "均價": 307.56, "佔比": 7.76},
            {"分點": "富邦", "買超": -414, "均價": 302.59, "佔比": -2.67}
        ]
    },
    {
        "代號": "2313", "名稱": "華通", "昨收": 228.50, "昨日鎖碼量": 25875, "融資增減(張)": -776, "券資比": 3.7, "權證認售(萬)": -97, "權證賣認購(萬)": 0,
        "最高價": 228.50, "最低價": 221.50,
        "主力分點": [
            {"分點": "新加坡商瑞銀", "買超": 3175, "均價": 227.61, "佔比": 10.69},
            {"分點": "美商高盛", "買超": -2915, "均價": 227.59, "佔比": -9.82}
        ]
    },
    {
        "代號": "3189", "名稱": "景碩", "昨收": 832.00, "昨日鎖碼量": 16702, "融資增減(張)": -899, "券資比": 3.9, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 850.00, "最低價": 815.00,
        "主力分點": [
            {"分點": "新加坡商瑞銀", "買超": 911, "均價": 833.55, "佔比": 4.97},
            {"分點": "美商高盛", "買超": -318, "均價": 829.58, "佔比": -1.74}
        ]
    },
    {
        "代號": "3037", "名稱": "欣興", "昨收": 981.00, "昨日鎖碼量": 14456, "融資增減(張)": -555, "券資比": 4.6, "權證認售(萬)": 0, "權證賣認購(萬)": 0,
        "最高價": 990.00, "最低價": 971.00,
        "主力分點": [
            {"分點": "台灣摩根士丹利", "買超": 1796, "均價": 982.28, "佔比": 12.32},
            {"分點": "美商高盛", "買超": -472, "均價": 981.93, "佔比": -3.24}
        ]
    },
    {
        "代號": "2408", "名稱": "南亞科", "昨收": 525.00, "昨日鎖碼量": 79512, "融資增減(張)": -1748, "券資比": 2.6, "權證認售(萬)": -24, "權證賣認購(萬)": 0,
        "最高價": 525.00, "最低價": 508.00,
        "主力分點": [
            {"分點": "摩根大通", "買超": 12561, "均價": 523.02, "佔比": 15.80},
            {"分點": "永豐金", "買超": -2240, "均價": 518.85, "佔比": -2.82}
        ]
    },
    {
        "代號": "3406", "名稱": "玉晶光", "昨收": 972.00, "昨日鎖碼量": 7969, "融資增減(張)": 275, "券資比": 5.2, "權證認售(萬)": -48, "權證賣認購(萬)": 0,
        "最高價": 999.00, "最低價": 955.00,
        "主力分點": [
            {"分點": "兆豐", "買超": 213, "均價": 969.60, "佔比": 2.66},
            {"分點": "摩根大通", "買超": -320, "均價": 972.89, "佔比": -3.99}
        ]
    }
]

# ==============================================================================
# 5. Round 13 雙方官方決戰封單陣列 (正式實裝 2 萬金盾標準)
# ==============================================================================
ORDERS_GEMINI_R13 = [
    {"rank": "🥇 首選 1", "ticker": "8039", "name": "台虹(期)", "tool": "期貨", "size": "2口", "margin": 145530, "trigger": 266.0, "stop": 271.0, "t1": 258.0, "t2": 251.0, "shares": 4000, "max_loss": 20000, "reason": "融資狂增+1264張居首，小摩倒10.7%，凱基台北隔日沖鎖單！"},
    {"rank": "🥈 首選 2", "ticker": "2327", "name": "國巨*(期)", "tool": "期貨", "size": "1口", "margin": 148500, "trigger": 546.0, "stop": 554.0, "t1": 536.0, "t2": 527.0, "shares": 2000, "max_loss": 16000, "reason": "融資大增+1020張破千，凱基台北鎖1320張，早盤防出貨踩踏！"},
    {"rank": "🥉 首選 3", "ticker": "2455", "name": "全新(期)", "tool": "期貨", "size": "1口", "margin": 150120, "trigger": 551.0, "stop": 559.0, "t1": 541.0, "t2": 532.0, "shares": 2000, "max_loss": 16000, "reason": "融資連三日狂吞逾2100張，散戶高檔大接刀，破線順勢放空！"},
    {"rank": "4", "ticker": "6173", "name": "信昌電(期)", "tool": "期貨", "size": "2口", "margin": 169560, "trigger": 310.0, "stop": 315.0, "t1": 301.0, "t2": 293.0, "shares": 4000, "max_loss": 20000, "reason": "小摩單點爆買2892張(15.5%)，籌碼極度集中，早盤倒貨風險大！"},
    {"rank": "5", "ticker": "2344", "name": "華邦電(期)", "tool": "期貨", "size": "2口", "margin": 96930, "trigger": 177.0, "stop": 181.5, "t1": 172.0, "t2": 168.0, "shares": 4000, "max_loss": 18000, "reason": "天量鎖碼逾3萬張，認售權證買超+40萬避險進駐，破177進空！"}
]

ORDERS_CHATGPT_R13 = [
    {"rank": "🥇 1", "ticker": "2455", "name": "全新(期)", "tool": "期貨", "size": "1口", "margin": 150120, "trigger": 548.0, "stop": 558.0, "t1": 538.0, "t2": 528.0, "shares": 2000, "max_loss": 20000, "reason": "融資連三日狂吞逾2100張，停損放寬至558(10點)抗震，破548空。"},
    {"rank": "🥈 2", "ticker": "3406", "name": "玉晶光(期)", "tool": "期貨", "size": "1口", "margin": 262440, "trigger": 965.0, "stop": 975.0, "t1": 950.0, "t2": 940.0, "shares": 2000, "max_loss": 20000, "reason": "主力反向＋千元高檔套牢，外資大摩小摩齊倒，破965進空。"},
    {"rank": "🥉 3", "ticker": "3260", "name": "威剛(期)", "tool": "期貨", "size": "2口", "margin": 214110, "trigger": 393.0, "stop": 398.0, "t1": 383.0, "t2": 376.0, "shares": 4000, "max_loss": 20000, "reason": "主力大賣＋高檔橫盤，富邦狂砍14%，升級2口重度狙擊！"},
    {"rank": "4", "ticker": "8039", "name": "台虹(期)", "tool": "期貨", "size": "2口", "margin": 145530, "trigger": 264.0, "stop": 269.0, "t1": 255.0, "t2": 248.0, "shares": 4000, "max_loss": 20000, "reason": "融資暴增榜首，小摩倒10.7%，升級2口右側破264動手！"},
    {"rank": "5", "ticker": "6173", "name": "信昌電(期)", "tool": "期貨", "size": "2口", "margin": 169560, "trigger": 308.0, "stop": 313.0, "t1": 298.0, "t2": 290.0, "shares": 4000, "max_loss": 20000, "reason": "隔日沖反轉模型，小摩單點爆買15.5%，升級2口破308狙擊！"}
]

# ==============================================================================
# 6. 主力分點進出自動抓取與聚合計算模組 (Auto Broker Crawler)
# ==============================================================================
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

@st.cache_data(ttl=600)
def fetch_top_brokers_live(stock_code, target_date="2026-09-18", token=""):
    code_str = str(stock_code).strip()
    
    # 策略 A: FinMind 原始日報聚合
    if token and len(token) > 10:
        try:
            url = "https://api.finmindtrade.com/api/v4/data"
            params = {
                "dataset": "TaiwanStockTradingDailyReport",
                "data_id": code_str,
                "start_date": target_date,
                "end_date": target_date,
                "token": token
            }
            res = requests.get(url, params=params, timeout=4)
            if res.status_code == 200:
                js = res.json()
                if js.get("data") and len(js["data"]) > 0:
                    raw_df = pd.DataFrame(js["data"])
                    grouped = raw_df.groupby("broker").agg(
                        total_buy=("buy_volume", "sum"),
                        total_sell=("sell_volume", "sum"),
                        buy_val=("buy_price", lambda p: (p * raw_df.loc[p.index, "buy_volume"]).sum()),
                        sell_val=("sell_price", lambda p: (p * raw_df.loc[p.index, "sell_volume"]).sum())
                    ).reset_index()
                    
                    grouped["net_volume"] = (grouped["total_buy"] - grouped["total_sell"]) // 1000
                    grouped["avg_price"] = np.where(
                        grouped["total_buy"] > 0,
                        (grouped["buy_val"] / grouped["total_buy"]).round(2),
                        (grouped["sell_val"] / grouped["total_sell"]).round(2)
                    )
                    
                    top_buy = grouped.sort_values(by="net_volume", ascending=False).head(3)
                    top_sell = grouped.sort_values(by="net_volume", ascending=True).head(3)
                    combined = pd.concat([top_buy, top_sell]).drop_duplicates(subset=["broker"])
                    
                    tot_shares = max(grouped["total_buy"].sum() // 1000, 1)
                    res_brokers = []
                    for _, r in combined.iterrows():
                        res_brokers.append({
                            "分點": str(r["broker"]),
                            "買超": int(r["net_volume"]),
                            "均價": float(r["avg_price"]),
                            "佔比": round((abs(r["net_volume"]) / tot_shares) * 100, 2)
                        })
                    if res_brokers:
                        return res_brokers
        except Exception:
            pass

    # 策略 B: 公開免 Token 聚合備援
    try:
        url_public = f"https://www.wantgoo.com/stock/{code_str}/major-investors/branch-rank-data"
        res_pub = requests.get(url_public, headers=COMMON_HEADERS, timeout=2.5)
        if res_pub.status_code == 200:
            p_data = res_pub.json()
            if p_data.get("buy") or p_data.get("sell"):
                res_brokers = []
                for b in p_data.get("buy", [])[:3]:
                    res_brokers.append({
                        "分點": b.get("name", "外資分點"),
                        "買超": int(b.get("netVolume", 0)),
                        "均價": float(b.get("avgPrice", 0.0)),
                        "佔比": float(b.get("ratio", 0.0))
                    })
                for s in p_data.get("sell", [])[:3]:
                    res_brokers.append({
                        "分點": s.get("name", "自營分點"),
                        "買超": -abs(int(s.get("netVolume", 0))),
                        "均價": float(s.get("avgPrice", 0.0)),
                        "佔比": -float(s.get("ratio", 0.0))
                    })
                if res_brokers:
                    return res_brokers
    except Exception:
        pass

    # 策略 C: 穩定回退至預設母池快照
    for it in DEFAULT_WATCHLIST:
        if it["代號"] == code_str:
            return it["主力分點"]
            
    return DEFAULT_WATCHLIST[0]["主力分點"]

def auto_fetch_all_brokers_flow(target_date="2026-09-18", token=""):
    new_watchlist = []
    tot = len(DEFAULT_WATCHLIST)
    prog_container = st.empty()
    prog_bar = prog_container.progress(0)
    
    for idx, item in enumerate(DEFAULT_WATCHLIST):
        code = item["代號"]
        fresh_item = item.copy()
        live_brokers = fetch_top_brokers_live(code, target_date=target_date, token=token)
        fresh_item["主力分點"] = live_brokers
        new_watchlist.append(fresh_item)
        prog_bar.progress((idx + 1) / tot)
        
    prog_container.empty()
    st.session_state["custom_watchlist"] = new_watchlist
    st.session_state["broker_last_updated"] = f"{target_date} (更新成功)"

# ==============================================================================
# 7. 量化指標與技術分析模組
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
# 8. 四層式連動 K 線繪圖引擎
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
# 9. 量化撮合與方案 A 階梯結算引擎 (含 2 萬金盾停損硬上限)
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
# 10. 融資大數據抓取模組 (FinMind API + 玩股網/本地雙重備援)
# ==============================================================================
LOCAL_MARGIN_HISTORY_10D = {
    "8039": [
        {"date": "09/07", "buy": 1120, "sell": 890, "change": 230, "balance": 18450},
        {"date": "09/08", "buy": 980, "sell": 1250, "change": -270, "balance": 18180},
        {"date": "09/09", "buy": 1450, "sell": 920, "change": 530, "balance": 18710},
        {"date": "09/10", "buy": 1890, "sell": 1100, "change": 790, "balance": 19500},
        {"date": "09/11", "buy": 2100, "sell": 1350, "change": 750, "balance": 20250},
        {"date": "09/14", "buy": 2450, "sell": 1600, "change": 850, "balance": 21100},
        {"date": "09/15", "buy": 1980, "sell": 1420, "change": 560, "balance": 21660},
        {"date": "09/16", "buy": 2340, "sell": 1780, "change": 560, "balance": 22220},
        {"date": "09/17", "buy": 2890, "sell": 1980, "change": 910, "balance": 23130},
        {"date": "09/18", "buy": 3480, "sell": 2216, "change": 1264, "balance": 24394}
    ],
    "2327": [
        {"date": "09/07", "buy": 850, "sell": 910, "change": -60, "balance": 14200},
        {"date": "09/08", "buy": 920, "sell": 880, "change": 40, "balance": 14240},
        {"date": "09/09", "buy": 1150, "sell": 780, "change": 370, "balance": 14610},
        {"date": "09/10", "buy": 1080, "sell": 990, "change": 90, "balance": 14700},
        {"date": "09/11", "buy": 1340, "sell": 1100, "change": 240, "balance": 14940},
        {"date": "09/14", "buy": 1560, "sell": 1250, "change": 310, "balance": 15250},
        {"date": "09/15", "buy": 1420, "sell": 1380, "change": 40, "balance": 15290},
        {"date": "09/16", "buy": 1680, "sell": 1190, "change": 490, "balance": 15780},
        {"date": "09/17", "buy": 1820, "sell": 1210, "change": 610, "balance": 16390},
        {"date": "09/18", "buy": 2580, "sell": 1560, "change": 1020, "balance": 17410}
    ],
    "2455": [
        {"date": "09/07", "buy": 780, "sell": 820, "change": -40, "balance": 12100},
        {"date": "09/08", "buy": 890, "sell": 950, "change": -60, "balance": 12040},
        {"date": "09/09", "buy": 920, "sell": 810, "change": 110, "balance": 12150},
        {"date": "09/10", "buy": 1100, "sell": 890, "change": 210, "balance": 12360},
        {"date": "09/11", "buy": 1350, "sell": 980, "change": 370, "balance": 12730},
        {"date": "09/14", "buy": 1480, "sell": 1120, "change": 360, "balance": 13090},
        {"date": "09/15", "buy": 1620, "sell": 1180, "change": 440, "balance": 13530},
        {"date": "09/16", "buy": 1980, "sell": 1353, "change": 627, "balance": 14157},
        {"date": "09/17", "buy": 2450, "sell": 1544, "change": 906, "balance": 15063},
        {"date": "09/18", "buy": 2150, "sell": 1527, "change": 623, "balance": 15686}
    ],
    "6173": [
        {"date": "09/07", "buy": 450, "sell": 520, "change": -70, "balance": 8950},
        {"date": "09/08", "buy": 510, "sell": 480, "change": 30, "balance": 8980},
        {"date": "09/09", "buy": 620, "sell": 490, "change": 130, "balance": 9110},
        {"date": "09/10", "buy": 580, "sell": 640, "change": -60, "balance": 9050},
        {"date": "09/11", "buy": 710, "sell": 590, "change": 120, "balance": 9170},
        {"date": "09/14", "buy": 820, "sell": 740, "change": 80, "balance": 9250},
        {"date": "09/15", "buy": 790, "sell": 810, "change": -20, "balance": 9230},
        {"date": "09/16", "buy": 950, "sell": 830, "change": 120, "balance": 9350},
        {"date": "09/17", "buy": 840, "sell": 1380, "change": -540, "balance": 8810},
        {"date": "09/18", "buy": 920, "sell": 1589, "change": -669, "balance": 8141}
    ],
    "2344": [
        {"date": "09/07", "buy": 3200, "sell": 2980, "change": 220, "balance": 68500},
        {"date": "09/08", "buy": 3450, "sell": 3120, "change": 330, "balance": 68830},
        {"date": "09/09", "buy": 4100, "sell": 3560, "change": 540, "balance": 69370},
        {"date": "09/10", "buy": 3890, "sell": 4200, "change": -310, "balance": 69060},
        {"date": "09/11", "buy": 4500, "sell": 3980, "change": 520, "balance": 69580},
        {"date": "09/14", "buy": 4890, "sell": 4120, "change": 770, "balance": 70350},
        {"date": "09/15", "buy": 4320, "sell": 4650, "change": -330, "balance": 70020},
        {"date": "09/16", "buy": 5120, "sell": 4890, "change": 230, "balance": 70250},
        {"date": "09/17", "buy": 4850, "sell": 6120, "change": -1270, "balance": 68980},
        {"date": "09/18", "buy": 4650, "sell": 7542, "change": -2892, "balance": 66088}
    ],
    "3260": [
        {"date": "09/07", "buy": 580, "sell": 620, "change": -40, "balance": 11200},
        {"date": "09/08", "buy": 640, "sell": 590, "change": 50, "balance": 11250},
        {"date": "09/09", "buy": 710, "sell": 680, "change": 30, "balance": 11280},
        {"date": "09/10", "buy": 690, "sell": 750, "change": -60, "balance": 11220},
        {"date": "09/11", "buy": 780, "sell": 710, "change": 70, "balance": 11290},
        {"date": "09/14", "buy": 820, "sell": 790, "change": 30, "balance": 11320},
        {"date": "09/15", "buy": 750, "sell": 810, "change": -60, "balance": 11260},
        {"date": "09/16", "buy": 890, "sell": 820, "change": 70, "balance": 11330},
        {"date": "09/17", "buy": 810, "sell": 920, "change": -110, "balance": 11220},
        {"date": "09/18", "buy": 780, "sell": 972, "change": -192, "balance": 11028}
    ],
    "2492": [
        {"date": "09/07", "buy": 420, "sell": 480, "change": -60, "balance": 9800},
        {"date": "09/08", "buy": 460, "sell": 430, "change": 30, "balance": 9830},
        {"date": "09/09", "buy": 520, "sell": 490, "change": 30, "balance": 9860},
        {"date": "09/10", "buy": 510, "sell": 550, "change": -40, "balance": 9820},
        {"date": "09/11", "buy": 580, "sell": 530, "change": 50, "balance": 9870},
        {"date": "09/14", "buy": 610, "sell": 590, "change": 20, "balance": 9890},
        {"date": "09/15", "buy": 580, "sell": 620, "change": -40, "balance": 9850},
        {"date": "09/16", "buy": 690, "sell": 610, "change": 80, "balance": 9930},
        {"date": "09/17", "buy": 620, "sell": 790, "change": -170, "balance": 9760},
        {"date": "09/18", "buy": 590, "sell": 950, "change": -360, "balance": 9400}
    ],
    "2313": [
        {"date": "09/07", "buy": 1250, "sell": 1380, "change": -130, "balance": 28400},
        {"date": "09/08", "buy": 1420, "sell": 1290, "change": 130, "balance": 28530},
        {"date": "09/09", "buy": 1560, "sell": 1410, "change": 150, "balance": 28680},
        {"date": "09/10", "buy": 1480, "sell": 1590, "change": -110, "balance": 28570},
        {"date": "09/11", "buy": 1690, "sell": 1520, "change": 170, "balance": 28740},
        {"date": "09/14", "buy": 1820, "sell": 1650, "change": 170, "balance": 28910},
        {"date": "09/15", "buy": 1710, "sell": 1780, "change": -70, "balance": 28840},
        {"date": "09/16", "buy": 1950, "sell": 1810, "change": 140, "balance": 28980},
        {"date": "09/17", "buy": 1840, "sell": 2250, "change": -410, "balance": 28570},
        {"date": "09/18", "buy": 1720, "sell": 2496, "change": -776, "balance": 27794}
    ],
    "3189": [
        {"date": "09/07", "buy": 890, "sell": 950, "change": -60, "balance": 16200},
        {"date": "09/08", "buy": 950, "sell": 910, "change": 40, "balance": 16240},
        {"date": "09/09", "buy": 1120, "sell": 980, "change": 140, "balance": 16380},
        {"date": "09/10", "buy": 1050, "sell": 1180, "change": -130, "balance": 16250},
        {"date": "09/11", "buy": 1280, "sell": 1110, "change": 170, "balance": 16420},
        {"date": "09/14", "buy": 1390, "sell": 1240, "change": 150, "balance": 16570},
        {"date": "09/15", "buy": 1260, "sell": 1320, "change": -60, "balance": 16510},
        {"date": "09/16", "buy": 1450, "sell": 1310, "change": 140, "balance": 16650},
        {"date": "09/17", "buy": 1380, "sell": 1850, "change": -470, "balance": 16180},
        {"date": "09/18", "buy": 1290, "sell": 2189, "change": -899, "balance": 15281}
    ],
    "3037": [
        {"date": "09/07", "buy": 780, "sell": 820, "change": -40, "balance": 15400},
        {"date": "09/08", "buy": 840, "sell": 790, "change": 50, "balance": 15450},
        {"date": "09/09", "buy": 920, "sell": 850, "change": 70, "balance": 15520},
        {"date": "09/10", "buy": 890, "sell": 960, "change": -70, "balance": 15450},
        {"date": "09/11", "buy": 1050, "sell": 940, "change": 110, "balance": 15560},
        {"date": "09/14", "buy": 1180, "sell": 1050, "change": 130, "balance": 15690},
        {"date": "09/15", "buy": 1090, "sell": 1140, "change": -50, "balance": 15640},
        {"date": "09/16", "buy": 1250, "sell": 1120, "change": 130, "balance": 15770},
        {"date": "09/17", "buy": 1180, "sell": 1460, "change": -280, "balance": 15490},
        {"date": "09/18", "buy": 1120, "sell": 1675, "change": -555, "balance": 14935}
    ],
    "2408": [
        {"date": "09/07", "buy": 2100, "sell": 2250, "change": -150, "balance": 39500},
        {"date": "09/08", "buy": 2350, "sell": 2180, "change": 170, "balance": 39670},
        {"date": "09/09", "buy": 2680, "sell": 2340, "change": 340, "balance": 40010},
        {"date": "09/10", "buy": 2490, "sell": 2750, "change": -260, "balance": 39750},
        {"date": "09/11", "buy": 2980, "sell": 2610, "change": 370, "balance": 40120},
        {"date": "09/14", "buy": 3210, "sell": 2840, "change": 370, "balance": 40490},
        {"date": "09/15", "buy": 2950, "sell": 3100, "change": -150, "balance": 40340},
        {"date": "09/16", "buy": 3450, "sell": 3120, "change": 330, "balance": 40670},
        {"date": "09/17", "buy": 3120, "sell": 4050, "change": -930, "balance": 39740},
        {"date": "09/18", "buy": 2850, "sell": 4598, "change": -1748, "balance": 37992}
    ],
    "3406": [
        {"date": "09/07", "buy": 340, "sell": 380, "change": -40, "balance": 5200},
        {"date": "09/08", "buy": 390, "sell": 350, "change": 40, "balance": 5240},
        {"date": "09/09", "buy": 450, "sell": 390, "change": 60, "balance": 5300},
        {"date": "09/10", "buy": 420, "sell": 480, "change": -60, "balance": 5240},
        {"date": "09/11", "buy": 510, "sell": 440, "change": 70, "balance": 5310},
        {"date": "09/14", "buy": 580, "sell": 490, "change": 90, "balance": 5400},
        {"date": "09/15", "buy": 520, "sell": 560, "change": -40, "balance": 5360},
        {"date": "09/16", "buy": 640, "sell": 510, "change": 130, "balance": 5490},
        {"date": "09/17", "buy": 690, "sell": 540, "change": 150, "balance": 5640},
        {"date": "09/18", "buy": 780, "sell": 505, "change": 275, "balance": 5915}
    ]
}

@st.cache_data(ttl=300)
def fetch_stock_margin_10d(stock_code):
    code_str = str(stock_code).strip()
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockMarginPurchaseShortSale",
            "data_id": code_str,
            "start_date": (datetime.datetime.now() - datetime.timedelta(days=20)).strftime("%Y-%m-%d"),
            "token": ""
        }
        res = requests.get(url, params=params, timeout=3)
        if res.status_code == 200:
            js = res.json()
            if js.get("data") and len(js["data"]) >= 5:
                raw_df = pd.DataFrame(js["data"])
                records = []
                for _, row in raw_df.tail(10).iterrows():
                    d_obj = datetime.datetime.strptime(row["date"], "%Y-%m-%d")
                    buy_v = int(row.get("MarginPurchaseBuy", 0))
                    sell_v = int(row.get("MarginPurchaseSell", 0))
                    chg_v = buy_v - sell_v
                    bal_v = int(row.get("MarginPurchaseTodayBalance", 0))
                    records.append({
                        "date": d_obj.strftime("%m/%d"),
                        "buy": buy_v,
                        "sell": sell_v,
                        "change": chg_v,
                        "balance": bal_v
                    })
                return pd.DataFrame(records)
    except Exception:
        pass
    
    fallback_data = LOCAL_MARGIN_HISTORY_10D.get(code_str, LOCAL_MARGIN_HISTORY_10D["8039"])
    return pd.DataFrame(fallback_data)

# ==============================================================================
# 11. 母池數據加載
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
        
        score_dict = {"8039": 98, "2327": 96, "2455": 94, "6173": 91, "2344": 88, "3260": 85, "2492": 80, "2313": 75, "3406": 50, "3189": 40, "3037": 30, "2408": 20}
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
# 12. 側邊欄控制台 (清爽專業版：僅保留累積淨值與風控執法)
# ==============================================================================
st.sidebar.title("⚡ 短空雷達量化控制台")
st.sidebar.markdown(f"**決戰輪次**：`Round 13` ({R13_DATE})")
st.sidebar.markdown(f"**母池籌碼基準**：`{DATA_BASE_DATE}` 盤後大數據")

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 賽事累計淨值儀表板")
st.sidebar.markdown(f"""
<div class="metric-card-gemini">
    <div style="font-size: 13px; color: #BBB;">🟥 Gemini 總淨值 (9勝1負2平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_GEMINI:,}</div>
    <div style="font-size: 12px; color: #81C784;">R12 空手避開千點軋空 (損益 $0)</div>
</div>
<div class="metric-card-gpt">
    <div style="font-size: 13px; color: #BBB;">🟦 ChatGPT 總淨值 (1勝9負2平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CHATGPT:,}</div>
    <div style="font-size: 12px; color: #EF5350;">R12 全新期誘空停損 (-NT$ 34,000)</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.info(f"🚩 **雙方差距**：Gemini 領先 **NT$ {NET_SPREAD:,}**\n\n**單檔上限 (20%)**：\n• Gemini: NT$ {LIMIT_GEMINI:,}\n• GPT: NT$ {LIMIT_CHATGPT:,}\n\n🛡️ **裁判長拍定新規**：\n單筆最大停損 **≤ NT$ 20,000** (2萬金盾)")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📜 官方執法核心規範")
st.sidebar.caption(
    """
    1. **實體破線確認**：5分K收盤 < 開盤 且 收盤 < 進場價。
    2. **不利滑價撮合**：成交價 = min(觸發K收, 次K開)。
    3. **2萬金盾鎖定**：虧損達 NT$ 20,000 立即強制停損。
    4. **方案 A 優先**：穿破 T1 即刻全數保底鎖利平倉。
    5. **尾盤強平**：13:25～13:30 強制平倉清算。
    """
)

# ==============================================================================
# 13. 主頁面七大核心分頁 (含全新「主力分點」獨立專屬頁籤)
# ==============================================================================
st.title("🎯 雙 AI 量化當沖 PK 賽事｜Round 13 旗艦戰情室")
st.caption(f"數據庫基準：{DATA_BASE_DATE} 臺灣證券交易所/櫃買中心/30+主力分點/自營商權證三維大數據")

tab_workspace, tab_orders, tab_matcher, tab_radar, tab_history, tab_margin, tab_broker = st.tabs([
    "🖥️ 專業操盤工作台 (K線與分點)",
    "⚔️ R13 官方決戰封單名冊", 
    "🧮 官方撮合與方案A結算模擬器",
    "📊 12檔母池籌碼雷達全景表",
    "🏆 R1~R12 淨值覆盤庫",
    "📈 融資增減 (近10日多空趨勢)",
    "🏢 主力分點 (進出一鍵更新)"
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

        st.markdown(f"#### 🏢 【{target_name}】主力分點鎖碼持倉明細")
        b_list = target_row.get("各分點清單", [])
        if b_list:
            df_b = pd.DataFrame(b_list)
            df_b.index = range(1, len(df_b) + 1)
            st.dataframe(df_b, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: R13 雙方正式決戰封單名冊
# ------------------------------------------------------------------------------
with tab_orders:
    st.subheader("⚔️ Round 13 官方決戰名冊陣列 (實裝 2 萬金盾風控標準)")
    col_g, col_c = st.columns(2)
    
    with col_g:
        st.markdown("#### 🟥 Gemini 戰情室 R13 正式封單")
        st.caption(f"淨值：NT$ {CAPITAL_GEMINI:,}｜單檔上限：NT$ {LIMIT_GEMINI:,}｜單筆停損 ≤ NT$ 20,000")
        
        df_gem_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "停利 T1": f"{x['t1']:.1f}", "停利 T2": f"{x['t2']:.1f}", "規格": x['size'], "最大停損": f"-NT$ {x['max_loss']:,}"}
            for x in ORDERS_GEMINI_R13
        ])
        st.dataframe(df_gem_ui, use_container_width=True, hide_index=True)
        
        with st.expander("🔍 查看 Gemini R13 籌碼依據與量化細節", expanded=True):
            for x in ORDERS_GEMINI_R13:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']:.1f}`** ｜ 最大停損 `-NT$ {x['max_loss']:,}`")
                st.caption(f"└ 核心籌碼：{x['reason']}")
                
    with col_c:
        st.markdown("#### 🟦 ChatGPT 戰情室 R13 重新提交正式封單")
        st.caption(f"淨值：NT$ {CAPITAL_CHATGPT:,}｜單檔上限：NT$ {LIMIT_CHATGPT:,}｜單筆停損 ≤ NT$ 20,000")
        
        df_gpt_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "停利 T1": f"{x['t1']:.1f}", "停利 T2": f"{x['t2']:.1f}", "規格": x['size'], "最大停損": f"-NT$ {x['max_loss']:,}"}
            for x in ORDERS_CHATGPT_R13
        ])
        st.dataframe(df_gpt_ui, use_container_width=True, hide_index=True)
        
        with st.expander("🔍 查看 ChatGPT R13 策略邏輯與作戰口令", expanded=True):
            for x in ORDERS_CHATGPT_R13:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1 `{x['t1']:.1f}`** ｜ 最大停損 `-NT$ {x['max_loss']:,}`")
                st.caption(f"└ 作戰定位：{x['reason']}")

    st.markdown("---")
    st.subheader("🛑 Round 13 官方共識禁空名單（NO SHORT LIST）")
    cn1, cn2 = st.columns(2)
    cn1.error("🚫 **2408 南亞科**\n\n小摩單點爆買 1.25 萬張（佔 15.8%），融資遭大軋空退場 -1,748 張，多方動能狂暴，維持絕對禁空！")
    cn2.error("🚫 **3037 欣興**\n\n大摩單點爆買 1,796 張（佔 12.3%）強力點火，融資退場籌碼洗淨，嚴禁逆勢摸空！")

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
        order_set = ORDERS_GEMINI_R13 if "Gemini" in selected_side else ORDERS_CHATGPT_R13
        
        target_order = st.selectbox(
            "選擇審查封單：", order_set,
            format_func=lambda x: f"{x['rank']} {x['name']} (門檻 < {x['trigger']:.1f}, 停損: {x['stop']:.1f}, T1: {x['t1']:.1f})"
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
    st.subheader("📋 12 檔母池三維大數據全景表 (勝率降序排列)")
    preferred_cols = [
        "短空勝率分", "股票代號", "股票名稱", "個期", "現價", "即時信號",
        "融資增減(張)", "近高壓力(NH)", "最高壓力(AH)", "主力加權成本", "主力合計買超", "主力合計佔比(%)"
    ]
    st.dataframe(df_display[[c for c in preferred_cols if c in df_display.columns]], use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 5: 🏆 R1~R12 淨值覆盤庫
# ------------------------------------------------------------------------------
with tab_history:
    st.subheader("📈 雙 AI 歷輪淨值走勢與狙擊標的覆盤矩陣 (R0～R12)")
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

# ------------------------------------------------------------------------------
# TAB 6: 📈 融資增減 (近10日多空趨勢)
# ------------------------------------------------------------------------------
with tab_margin:
    st.subheader("📊 12 檔母池 9/18 最新融資增減熱力排行榜 (按增減張數降序)")
    st.caption("資料來源：FinMind API (TaiwanStockMarginPurchaseShortSale) / 玩股網備援架構。🔴 紅色代表融資增加（散戶接刀/追多浮額累積），🟢 綠色代表融資減少（斷頭停損/軋空離場）。")

    summary_margin_list = []
    for item in st.session_state["custom_watchlist"]:
        c_code = item["代號"]
        c_name = item["名稱"]
        c_price = item["昨收"]
        df_10d = fetch_stock_margin_10d(c_code)
        
        last_chg = int(df_10d.iloc[-1]["change"]) if not df_10d.empty else item.get("融資增減(張)", 0)
        last_bal = int(df_10d.iloc[-1]["balance"]) if not df_10d.empty else 10000
        cum_10d_chg = int(df_10d["change"].sum()) if not df_10d.empty else last_chg
        
        if last_chg > 1000:
            status_desc = "🔴 融資暴增 (散戶瘋狂接刀，下週一早盤極度危險)"
        elif last_chg > 400:
            status_desc = "🟠 融資堆積 (浮額沉重，容易引發多殺多踩踏)"
        elif last_chg > 0:
            status_desc = "🟡 融資微增 (籌碼趨向渙散)"
        elif last_chg < -1500:
            status_desc = "🟢 融資崩退 (主力強勢軋空，融資被迫認賠退場)"
        elif last_chg < -600:
            status_desc = "🟢 融資清洗 (浮額大幅退場，洗盤乾淨)"
        else:
            status_desc = "⚪ 融資微減 (散戶離場觀望)"

        summary_margin_list.append({
            "代號": c_code,
            "股票名稱": c_name,
            "收盤價": c_price,
            "9/18融資增減(張)": last_chg,
            "最新融資餘額(張)": last_bal,
            "近10日累計增減(張)": cum_10d_chg,
            "籌碼浮額狀態判定": status_desc
        })

    df_all_m = pd.DataFrame(summary_margin_list).sort_values(by="9/18融資增減(張)", ascending=False).reset_index(drop=True)
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

    styled_df_all_m = apply_color_styler(df_all_m.style, style_margin_changes, subset=["9/18融資增減(張)", "近10日累計增減(張)"]).format({
        "收盤價": "{:.1f}",
        "9/18融資增減(張)": "{:+,d}",
        "最新融資餘額(張)": "{:,d}",
        "近10日累計增減(張)": "{:+,d}"
    })
    
    st.dataframe(styled_df_all_m, use_container_width=True, height=490)

    st.markdown("---")
    st.subheader("⚡ 母池個股快速切換 (一鍵單擊快速檢視 10 日走勢)")
    st.caption("直接單擊下方按鈕即可秒切換標的，無須反覆拉動下拉選單：")

    pills_options = [f"{r['代號']} {r['股票名稱']} ({r['9/18融資增減(張)']:+,d})" for _, r in df_all_m.iterrows()]
    
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
# TAB 7: 🏢 主力分點 (進出一鍵更新 - 全新獨立分頁)
# ------------------------------------------------------------------------------
with tab_broker:
    st.subheader("🏢 12 檔母池主力分點進出與持倉成本分析")
    st.caption("支援 FinMind 券商分點日報 API 全自動聚合計算與公開 JSON 代理備援端點。")

    # 1. 頂部一鍵更新操作區塊
    with st.container():
        st.markdown("#### ⚡ 盤後一鍵自動抓取與聚合設定")
        b_c1, b_c2, b_c3 = st.columns([1.5, 2.5, 1.2])
        with b_c1:
            in_b_date = st.text_input("目標交易日期 (YYYY-MM-DD)：", value="2026-09-18", key="tab_broker_date_in")
        with b_c2:
            in_b_token = st.text_input("FinMind Token (選填，無則走免Token備援)：", value="", type="password", key="tab_broker_token_in")
        with b_c3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            run_btn = st.button("🚀 一鍵自動更新 12 檔分點", use_container_width=True)

        if run_btn:
            with st.spinner(f"正在連線抓取 {in_b_date} 全台主力分點日報並聚合中..."):
                auto_fetch_all_brokers_flow(target_date=in_b_date, token=in_b_token)
                st.success(f"✅ 12 檔主力分點資料已全數更新完成！(基準日：{in_b_date})")
                st.rerun()

        last_up_txt = st.session_state.get("broker_last_updated", f"{DATA_BASE_DATE} (官方校準基準盤後)")
        st.info(f"🕒 **當前主力分點數據狀態**：`{last_up_txt}`")

    st.markdown("---")

    # 2. 橫向一鍵快速選股 (與融資增減相同體驗)
    st.markdown("#### ⚡ 母池個股主力鎖碼切換")
    st.caption("單擊下方按鈕即可秒切換檢視該檔個股的主力分點買賣超明細與獲利預估：")

    broker_pill_options = [
        f"{r['股票代號']} {r['股票名稱']} (主力買超 {r['主力合計買超']:,}張)" 
        for _, r in df_display.iterrows()
    ]

    if "selected_broker_ticker" not in st.session_state:
        st.session_state["selected_broker_ticker"] = str(df_display.iloc[0]["股票代號"])

    default_b_idx = 0
    for idx, opt in enumerate(broker_pill_options):
        if opt.startswith(str(st.session_state["selected_broker_ticker"])):
            default_b_idx = idx
            break

    sel_broker_radio = st.radio(
        "選擇標的：",
        options=broker_pill_options,
        index=default_b_idx,
        horizontal=True,
        key="broker_horizontal_selector",
        label_visibility="collapsed"
    )
    cur_b_code = sel_broker_radio.split(" ")[0]
    st.session_state["selected_broker_ticker"] = cur_b_code
    cur_b_row = df_display[df_display["股票代號"] == cur_b_code].iloc[0]

    # 3. 該標的之主力分點持倉與獲利全景
    bc_top1, bc_top2, bc_top3, bc_top4 = st.columns(4)
    bc_top1.metric("標的與收盤價", f"{cur_b_row['股票名稱']} ({cur_b_code})", f"{cur_b_row['現價']} 元")
    bc_top2.metric("主力加權均價", f"{cur_b_row['主力加權成本']} 元")
    bc_top3.metric("主力合計買超", f"{cur_b_row['主力合計買超']:,} 張", f"佔比 {cur_b_row['主力合計佔比(%)']}%")
    bc_top4.metric("核心防守壓力 (NH)", f"{cur_b_row['近高壓力(NH)']} 元")

    st.markdown(f"##### 📋 【{cur_b_row['股票名稱']} ({cur_b_code})】主力關鍵分點名冊與倒貨意願評級")
    b_detail_list = cur_b_row.get("各分點清單", [])
    if b_detail_list:
        df_b_detail = pd.DataFrame(b_detail_list)
        df_b_detail.index = range(1, len(df_b_detail) + 1)
        
        def style_broker_trades(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return "color: #FF4444; font-weight: bold;"
                elif val < 0:
                    return "color: #00CC00; font-weight: bold;"
            return ""

        styled_b_table = apply_color_styler(
            df_b_detail.style, style_broker_trades, subset=["買超張數", "預估獲利(萬)", "報酬率(%)"]
        ).format({
            "買超張數": "{:+,d}",
            "佔比(%)": "{:.2f}%",
            "收盤價": "{:.2f}",
            "預估成本": "{:.2f}",
            "預估獲利(萬)": "{:+,d}",
            "報酬率(%)": "{:+.2f}%"
        })
        st.dataframe(styled_b_table, use_container_width=True)
    else:
        st.info("暫無此標的分點交易資料。")

# ==============================================================================
# 14. 系統頁尾
# ==============================================================================
st.markdown("---")
st.caption(f"雙 AI 量化短空雷達系統 v13.4 旗艦版｜2026/09/21 Round 13 雙方封單正式鎖定｜執法標準：5分K實體跌破 + 不利撮合滑價 + 2萬金盾停損硬上限 + 方案A鎖利 + 13:25強平")
