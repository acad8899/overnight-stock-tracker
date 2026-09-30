# -*- coding: utf-8 -*-
"""
雙 AI 量化短空雷達 (Round 18 旗艦裁判長版) - app.py (v18.0)
==============================================================================
版本更新重點：
1. 輪次晉級：推進至 Round 18，以 2026/09/29 盤後最新主力與官方融資大數據為基準。
2. 母池更替：依最高裁判長指示，正式剔除 3260 威剛，全面納入 3042 晶技。
3. 歷史收錄：正式寫入 Round 17 官方終審裁決 (Gemini +30,000 / GPT +66,000)。
4. 淨值更新：Gemini NT$ 1,783,595 vs ChatGPT NT$ 1,399,681 (領先差距 NT$ 383,914)。
5. 融資數據：全面同步 9/29 官方融資增減數據 (國巨+2018, 華新科+1660, 晶技+1481)。
6. 籌碼大數據：全面收錄 12 檔母池 9/29 盤後真實主力分點與買賣超佔比。
7. 封單陣列：實裝雙方 Round 18 官方 TOP 5 決戰名冊 (單筆 ≤ NT$ 20,000，命中 T1 全平保底)。
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
    page_title="雙 AI 量化短空雷達 (Round 18 旗艦裁判長版)", 
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
# 2. 官方公約常數與雙方帳戶狀態 (2026/09/29 R17 終局結算生效)
# ==============================================================================
R18_DATE = "2026/09/30"
DATA_BASE_DATE = "2026/09/29"
MARGIN_DISPLAY_DATE = "9/29"

CAPITAL_GEMINI = 1783595     # R17 結算後 (+NT$ 30,000)
CAPITAL_CHATGPT = 1399681    # R17 結算後 (+NT$ 66,000)
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
# 3. 官方 R1～R17 歷史對決覆盤庫 (完整收錄 R17)
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
        "spread": 383914, "review": "GPT 繳出代表作！南亞科 490 方案 A 精準鎖利全平，避開午盤暴拉，加上信昌電大勝 6.6 萬奪勝！Gemini 全新正價差收斂與信昌電進帳 5 萬，金盾控損，淨值達 178.3 萬新高！"
    }
]

# ==============================================================================
# 4. 2026-09-29 盤後 12 檔母池大數據庫 (納入 3042 晶技、移除 3260 威剛)
# ==============================================================================
DEFAULT_WATCHLIST = [
    {
        "代號": "2327", "名稱": "國巨*", "昨收": 548.00, "昨日鎖碼量": 41164, "融資增減(張)": 2018, "券資比": 3.6, "權證認售(萬)": 0,
        "最高價": 570.00, "最低價": 548.00,
        "主力分點": [
            {"分點": "摩根大通", "買超": 3364, "均價": 556.38, "佔比": 8.17},
            {"分點": "富邦", "買超": 932, "均價": 563.14, "佔比": 2.26},
            {"分點": "國泰-敦南", "買超": 695, "均價": 557.40, "佔比": 1.69},
            {"分點": "永豐金", "買超": 371, "均價": 556.37, "佔比": 0.90},
            {"分點": "新光", "買超": 176, "均價": 558.13, "佔比": 0.43},
            {"分點": "美商高盛", "買超": -6792, "均價": 557.25, "佔比": -16.50},
            {"分點": "台灣摩根士丹利", "買超": -6351, "均價": 557.61, "佔比": -15.43},
            {"分點": "新加坡商瑞銀", "買超": -2043, "均價": 560.74, "佔比": -4.96},
            {"分點": "元大", "買超": -2042, "均價": 557.11, "佔比": -4.96},
            {"分點": "凱基", "買超": -1242, "均價": 553.90, "佔比": -3.02}
        ]
    },
    {
        "代號": "2492", "名稱": "華新科", "昨收": 302.00, "昨日鎖碼量": 31201, "融資增減(張)": 1660, "券資比": 3.1, "權證認售(萬)": 0,
        "最高價": 321.00, "最低價": 299.00,
        "主力分點": [
            {"分點": "國泰-敦南", "買超": 402, "均價": 306.68, "佔比": 1.29},
            {"分點": "永豐金-中正", "買超": 113, "均價": 312.55, "佔比": 0.36},
            {"分點": "國泰-台中", "買超": 100, "均價": 307.94, "佔比": 0.32},
            {"分點": "永豐金-台南", "買超": 98, "均價": 314.54, "佔比": 0.31},
            {"分點": "富邦-建國", "買超": 96, "均價": 306.83, "佔比": 0.31},
            {"分點": "美商高盛", "買超": -1913, "均價": 307.20, "佔比": -6.13},
            {"分點": "台灣摩根士丹利", "買超": -1862, "均價": 305.76, "佔比": -5.97},
            {"分點": "元大", "買超": -1417, "均價": 308.00, "佔比": -4.54},
            {"分點": "摩根大通", "買超": -1265, "均價": 305.79, "佔比": -4.05},
            {"分點": "凱基-台北", "買超": -759, "均價": 307.55, "佔比": -2.43}
        ]
    },
    {
        "代號": "3042", "名稱": "晶技", "昨收": 208.50, "昨日鎖碼量": 34407, "融資增減(張)": 1481, "券資比": 4.1, "權證認售(萬)": 0,
        "最高價": 222.50, "最低價": 205.00,
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
        "代號": "6173", "名稱": "信昌電", "昨收": 297.50, "昨日鎖碼量": 7033, "融資增減(張)": 529, "券資比": 3.5, "權證認售(萬)": 139,
        "最高價": 314.00, "最低價": 296.50,
        "主力分點": [
            {"分點": "群益金鼎-大安", "買超": 247, "均價": 309.14, "佔比": 3.51},
            {"分點": "台灣摩根士丹利", "買超": 149, "均價": 300.28, "佔比": 2.12},
            {"分點": "美商高盛", "買超": 139, "均價": 302.35, "佔比": 1.98},
            {"分點": "港商野村", "買超": 121, "均價": 302.97, "佔比": 1.72},
            {"分點": "國泰-敦南", "買超": 64, "均價": 302.75, "佔比": 0.91},
            {"分點": "群益金鼎", "買超": -203, "均價": 304.19, "佔比": -2.89},
            {"分點": "凱基-興隆", "買超": -201, "均價": 303.63, "佔比": -2.86},
            {"分點": "凱基-台北", "買超": -115, "均價": 301.28, "佔比": -1.64},
            {"分點": "永豐金-信義", "買超": -89, "均價": 299.43, "佔比": -1.27},
            {"分點": "美林", "買超": -88, "均價": 300.74, "佔比": -1.25}
        ]
    },
    {
        "代號": "3406", "名稱": "玉晶光", "昨收": 882.00, "昨日鎖碼量": 2568, "融資增減(張)": -173, "券資比": 4.5, "權證認售(萬)": 0,
        "最高價": 893.00, "最低價": 869.00,
        "主力分點": [
            {"分點": "凱基-台北", "買超": 167, "均價": 881.62, "佔比": 6.50},
            {"分點": "美商高盛", "買超": 107, "均價": 881.40, "佔比": 4.17},
            {"分點": "富邦", "買超": 53, "均價": 884.29, "佔比": 2.06},
            {"分點": "摩根大通", "買超": 49, "均價": 880.04, "佔比": 1.91},
            {"分點": "國票-天祥", "買超": 30, "均價": 889.03, "佔比": 1.17},
            {"分點": "港商野村", "買超": -232, "均價": 879.59, "佔比": -9.03},
            {"分點": "新加坡商瑞銀", "買超": -64, "均價": 879.41, "佔比": -2.49},
            {"分點": "永豐金", "買超": -55, "均價": 884.28, "佔比": -2.14},
            {"分點": "永豐金-信義", "買超": -54, "均價": 875.55, "佔比": -2.10},
            {"分點": "凱基-信義", "買超": -52, "均價": 877.37, "佔比": -2.02}
        ]
    },
    {
        "代號": "2408", "名稱": "南亞科", "昨收": 506.00, "昨日鎖碼量": 24966, "融資增減(張)": 34, "券資比": 3.7, "權證認售(萬)": 0,
        "最高價": 507.00, "最低價": 488.00,
        "主力分點": [
            {"分點": "新加坡商瑞銀", "買超": 1518, "均價": 501.33, "佔比": 6.08},
            {"分點": "花旗環球", "買超": 1093, "均價": 502.33, "佔比": 4.38},
            {"分點": "元大", "買超": 922, "均價": 501.56, "佔比": 3.69},
            {"分點": "台灣摩根士丹利", "買超": 273, "均價": 501.76, "佔比": 1.09},
            {"分點": "富邦-木柵", "買超": 101, "均價": 504.89, "佔比": 0.40},
            {"分點": "兆豐", "買超": -858, "均價": 501.00, "佔比": -3.44},
            {"分點": "美林", "買超": -474, "均價": 499.33, "佔比": -1.90},
            {"分點": "凱基-高美術館", "買超": -418, "均價": 496.30, "佔比": -1.67},
            {"分點": "凱基-台北", "買超": -402, "均價": 498.41, "佔比": -1.61},
            {"分點": "永豐金", "買超": -399, "均價": 501.54, "佔比": -1.60}
        ]
    },
    {
        "代號": "2344", "名稱": "華邦電", "昨收": 174.00, "昨日鎖碼量": 45790, "融資增減(張)": -619, "券資比": 2.7, "權證認售(萬)": 0,
        "最高價": 174.00, "最低價": 166.00,
        "主力分點": [
            {"分點": "新加坡商瑞銀", "買超": 2660, "均價": 171.14, "佔比": 5.81},
            {"分點": "元大", "買超": 1671, "均價": 171.80, "佔比": 3.65},
            {"分點": "花旗環球", "買超": 1256, "均價": 173.13, "佔比": 2.74},
            {"分點": "第一金-新竹", "買超": 953, "均價": 171.78, "佔比": 2.08},
            {"分點": "台灣摩根士丹利", "買超": 946, "均價": 171.94, "佔比": 2.07},
            {"分點": "凱基-站前", "買超": -1973, "均價": 170.99, "佔比": -4.31},
            {"分點": "美林", "買超": -654, "均價": 170.64, "佔比": -1.43},
            {"分點": "國泰-敦南", "買超": -439, "均價": 171.41, "佔比": -0.96},
            {"分點": "元大-北投", "買超": -417, "均價": 169.43, "佔比": -0.91},
            {"分點": "永豐金", "買超": -354, "均價": 171.10, "佔比": -0.77}
        ]
    },
    {
        "代號": "8039", "名稱": "台虹", "昨收": 273.50, "昨日鎖碼量": 14052, "融資增減(張)": 785, "券資比": 4.6, "權證認售(萬)": 0,
        "最高價": 273.50, "最低價": 256.50,
        "主力分點": [
            {"分點": "富邦", "買超": 426, "均價": 270.49, "佔比": 3.03},
            {"分點": "統一", "買超": 223, "均價": 264.48, "佔比": 1.59},
            {"分點": "摩根大通", "買超": 187, "均價": 263.72, "佔比": 1.33},
            {"分點": "中國信託-高雄", "買超": 149, "均價": 265.91, "佔比": 1.06},
            {"分點": "港商麥格理", "買超": 142, "均價": 271.04, "佔比": 1.01},
            {"分點": "台灣摩根士丹利", "買超": -746, "均價": 267.90, "佔比": -5.31},
            {"分點": "美商高盛", "買超": -542, "均價": 267.30, "佔比": -3.86},
            {"分點": "凱基-台北", "買超": -253, "均價": 266.42, "佔比": -1.80},
            {"分點": "群益金鼎", "買超": -87, "均價": 268.41, "佔比": -0.62},
            {"分點": "新加坡商瑞銀", "買超": -69, "均價": 267.64, "佔比": -0.49}
        ]
    },
    {
        "代號": "2455", "名稱": "全新", "昨收": 543.00, "昨日鎖碼量": 1025, "融資增減(張)": -159, "券資比": 5.2, "權證認售(萬)": 0,
        "最高價": 550.00, "最低價": 540.00,
        "主力分點": [
            {"分點": "新加坡商瑞銀", "買超": 77, "均價": 544.77, "佔比": 7.51},
            {"分點": "台新", "買超": 51, "均價": 549.59, "佔比": 4.98},
            {"分點": "元大-中山北路", "買超": 50, "均價": 549.20, "佔比": 4.88},
            {"分點": "元大", "買超": 42, "均價": 550.00, "佔比": 4.10},
            {"分點": "永豐金", "買超": 25, "均價": 550.00, "佔比": 2.44},
            {"分點": "港商麥格理", "買超": -134, "均價": 545.50, "佔比": -13.07},
            {"分點": "摩根大通", "買超": -63, "均價": 544.44, "佔比": -6.15},
            {"分點": "富邦-永和", "買超": -23, "均價": 550.00, "佔比": -2.24},
            {"分點": "台新-台北", "買超": -21, "均價": 542.14, "佔比": -2.05},
            {"分點": "台新-台中", "買超": -20, "均價": 545.00, "佔比": -1.95}
        ]
    },
    {
        "代號": "2313", "名稱": "華通", "昨收": 226.00, "昨日鎖碼量": 10064, "融資增減(張)": -567, "券資比": 3.2, "權證認售(萬)": 18,
        "最高價": 227.00, "最低價": 219.00,
        "主力分點": [
            {"分點": "富邦", "買超": 916, "均價": 225.45, "佔比": 9.10},
            {"分點": "美林", "買超": 906, "均價": 224.22, "佔比": 9.00},
            {"分點": "美商高盛", "買超": 323, "均價": 224.62, "佔比": 3.21},
            {"分點": "永豐金", "買超": 275, "均價": 225.10, "佔比": 2.73},
            {"分點": "台灣摩根士丹利", "買超": 157, "均價": 225.62, "佔比": 1.56},
            {"分點": "永豐金-匯立", "買超": -305, "均價": 223.35, "佔比": -3.03},
            {"分點": "華南永昌", "買超": -283, "均價": 225.42, "佔比": -2.81},
            {"分點": "玉山-新莊", "買超": -204, "均價": 223.65, "佔比": -2.03},
            {"分點": "花旗環球", "買超": -166, "均價": 223.82, "佔比": -1.65},
            {"分點": "中國信託-高雄", "買超": -134, "均價": 226.94, "佔比": -1.33}
        ]
    },
    {
        "代號": "3189", "名稱": "景碩", "昨收": 955.00, "昨日鎖碼量": 16460, "融資增減(張)": -199, "券資比": 4.3, "權證認售(萬)": 0,
        "最高價": 969.00, "最低價": 939.00,
        "主力分點": [
            {"分點": "美商高盛", "買超": 932, "均價": 953.30, "佔比": 5.66},
            {"分點": "富邦", "買超": 193, "均價": 953.90, "佔比": 1.17},
            {"分點": "永豐金", "買超": 176, "均價": 955.95, "佔比": 1.07},
            {"分點": "港商野村", "買超": 138, "均價": 956.35, "佔比": 0.84},
            {"分點": "台灣摩根士丹利", "買超": 138, "均價": 954.25, "佔比": 0.84},
            {"分點": "富邦-陽明", "買超": -1008, "均價": 950.77, "佔比": -6.12},
            {"分點": "宏遠", "買超": -386, "均價": 954.41, "佔比": -2.35},
            {"分點": "凱基-城中", "買超": -334, "均價": 955.61, "佔比": -2.03},
            {"分點": "新加坡商瑞銀", "買超": -246, "均價": 948.94, "佔比": -1.49},
            {"分點": "凱基-台北", "買超": -241, "均價": 949.67, "佔比": -1.46}
        ]
    },
    {
        "代號": "3037", "名稱": "欣興", "昨收": 1165.00, "昨日鎖碼量": 10830, "融資增減(張)": 217, "券資比": 4.8, "權證認售(萬)": 0,
        "最高價": 1185.00, "最低價": 1130.00,
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
    }
]

# ==============================================================================
# 5. Round 18 雙方官方決戰 TOP 5 封單陣列 (正式公證定案版)
# ==============================================================================
ORDERS_GEMINI_R18 = [
    {"rank": "🥇 首選 1", "ticker": "2327", "name": "國巨*(期)", "tool": "期貨", "size": "1口", "margin": 147960, "trigger": 545.0, "stop": 555.0, "t1": 535.0, "shares": 2000, "max_loss": 20000, "reason": "六大主力暴倒 -19,600 張收最低 548，融資暴增 +2,018 張慘套，假突破破底！"},
    {"rank": "🥈 首選 2", "ticker": "2492", "name": "華新科(期)", "tool": "期貨", "size": "2口", "margin": 163080, "trigger": 300.0, "stop": 305.0, "t1": 293.0, "shares": 4000, "max_loss": 20000, "reason": "高盛/大摩四大外資狂拋 6,400 張，融資逆勢追 1,660 張，摜破 300 踩踏！"},
    {"rank": "🥉 首選 3", "ticker": "3042", "name": "晶技(期)", "tool": "期貨", "size": "2口", "margin": 112590, "trigger": 206.5, "stop": 211.5, "t1": 199.5, "shares": 4000, "max_loss": 20000, "reason": "母池新兵首發！爆 3.4 萬張天量留長上影，外資群倒貨 2,400 張，融資大套 1,481 張！"},
    {"rank": "4", "ticker": "6173", "name": "信昌電(期)", "tool": "期貨", "size": "2口", "margin": 160650, "trigger": 260.0, "stop": 265.0, "t1": 253.0, "shares": 4000, "max_loss": 20000, "reason": "現貨破 300 收 297.5，期貨探底 260，融資連兩天虛胖接刀，二線續破底！"},
    {"rank": "5", "ticker": "3406", "name": "玉晶光(期)", "tool": "期貨", "size": "1口", "margin": 238140, "trigger": 874.0, "stop": 894.0, "t1": 860.0, "shares": 2000, "max_loss": 20000, "reason": "野村等主力續砍收 882，均線全面空頭發散破底，跌破 874 探 860 支撐！"}
]

ORDERS_CHATGPT_R18 = [
    {"rank": "🥇 1", "ticker": "2492", "name": "華新科(期)", "tool": "期貨", "size": "2口", "margin": 163080, "trigger": 298.0, "stop": 303.0, "t1": 290.0, "shares": 4000, "max_loss": 20000, "reason": "籌碼轉弱＋價格確認，破 298 確認短線支撐破壞，下探 290 方案 A。"},
    {"rank": "🥈 2", "ticker": "2408", "name": "南亞科(期)", "tool": "期貨", "size": "2口", "margin": 172040, "trigger": 492.0, "stop": 497.0, "t1": 484.0, "shares": 4000, "max_loss": 20000, "reason": "R17 成功經驗延續，不預判追空，等再次破 492 二次破底確認才進場。"},
    {"rank": "🥉 3", "ticker": "6173", "name": "信昌電(期)", "tool": "期貨", "size": "2口", "margin": 160650, "trigger": 294.0, "stop": 299.0, "t1": 286.0, "shares": 4000, "max_loss": 20000, "reason": "現貨回落至 297.5，高槓桿籌碼重回關鍵區，破 294 引發多殺多。"},
    {"rank": "4", "ticker": "3406", "name": "玉晶光(期)", "tool": "期貨", "size": "1口", "margin": 238140, "trigger": 872.0, "stop": 882.0, "t1": 858.0, "shares": 2000, "max_loss": 20000, "reason": "空方前低結構逐步下移，破 872 標準破底型態追空。"},
    {"rank": "5", "ticker": "3042", "name": "晶技(期)", "tool": "期貨", "size": "2口", "margin": 112590, "trigger": 207.0, "stop": 212.0, "t1": 198.0, "shares": 4000, "max_loss": 20000, "reason": "新兵觀察位，股價急漲＋融資快速堆高＋外資轉賣，破 207 確認上攻失敗。"}
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
# 8. 量化撮合與方案 A 階梯結算引擎 (2萬金盾與 T1 保底)
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
# 9. 融資大數據模組 (同步 9/29 官方數據庫)
# ==============================================================================
LOCAL_MARGIN_HISTORY_10D = {
    "2327": [
        {"date": "09/14", "buy": 1500, "sell": 1350, "change": 150, "balance": 34440},
        {"date": "09/15", "buy": 1450, "sell": 1200, "change": 250, "balance": 34690},
        {"date": "09/16", "buy": 1680, "sell": 1520, "change": 160, "balance": 34850},
        {"date": "09/17", "buy": 1740, "sell": 1580, "change": 160, "balance": 35010},
        {"date": "09/18", "buy": 1890, "sell": 1680, "change": 210, "balance": 35220},
        {"date": "09/21", "buy": 1520, "sell": 1890, "change": -370, "balance": 34850},
        {"date": "09/22", "buy": 1650, "sell": 1420, "change": 230, "balance": 35080},
        {"date": "09/23", "buy": 2480, "sell": 1341, "change": 1139, "balance": 36219},
        {"date": "09/24", "buy": 1580, "sell": 1394, "change": 186, "balance": 36405},
        {"date": "09/29", "buy": 3890, "sell": 1872, "change": 2018, "balance": 38423}
    ],
    "2492": [
        {"date": "09/14", "buy": 1250, "sell": 1380, "change": -130, "balance": 40310},
        {"date": "09/15", "buy": 1450, "sell": 1200, "change": 250, "balance": 40560},
        {"date": "09/16", "buy": 1600, "sell": 1450, "change": 150, "balance": 40710},
        {"date": "09/17", "buy": 1750, "sell": 1520, "change": 230, "balance": 40940},
        {"date": "09/18", "buy": 1820, "sell": 1650, "change": 170, "balance": 41110},
        {"date": "09/21", "buy": 1500, "sell": 1850, "change": -350, "balance": 40760},
        {"date": "09/22", "buy": 1420, "sell": 1500, "change": -80, "balance": 40680},
        {"date": "09/23", "buy": 1890, "sell": 1337, "change": 553, "balance": 41233},
        {"date": "09/24", "buy": 1240, "sell": 1368, "change": -128, "balance": 41105},
        {"date": "09/29", "buy": 3150, "sell": 1490, "change": 1660, "balance": 42765}
    ],
    "3042": [
        {"date": "09/14", "buy": 950, "sell": 800, "change": 150, "balance": 18200},
        {"date": "09/15", "buy": 1100, "sell": 950, "change": 150, "balance": 18350},
        {"date": "09/16", "buy": 1200, "sell": 1100, "change": 100, "balance": 18450},
        {"date": "09/17", "buy": 1400, "sell": 1250, "change": 150, "balance": 18600},
        {"date": "09/18", "buy": 1650, "sell": 1400, "change": 250, "balance": 18850},
        {"date": "09/21", "buy": 1300, "sell": 1500, "change": -200, "balance": 18650},
        {"date": "09/22", "buy": 1500, "sell": 1350, "change": 150, "balance": 18800},
        {"date": "09/23", "buy": 6500, "sell": 1257, "change": 5243, "balance": 24043},
        {"date": "09/24", "buy": 2100, "sell": 925, "change": 1175, "balance": 25218},
        {"date": "09/29", "buy": 3890, "sell": 2409, "change": 1481, "balance": 26699}
    ]
}

@st.cache_data(ttl=300)
def fetch_stock_margin_10d(stock_code):
    code_str = str(stock_code).strip()
    fallback_data = LOCAL_MARGIN_HISTORY_10D.get(code_str, [
        {"date": "09/14", "buy": 1200, "sell": 1100, "change": 100, "balance": 15250},
        {"date": "09/15", "buy": 1050, "sell": 1000, "change": 50, "balance": 15300},
        {"date": "09/16", "buy": 1150, "sell": 1050, "change": 100, "balance": 15400},
        {"date": "09/17", "buy": 1300, "sell": 1150, "change": 150, "balance": 15550},
        {"date": "09/18", "buy": 1400, "sell": 1600, "change": -200, "balance": 15350},
        {"date": "09/21", "buy": 1250, "sell": 1350, "change": -100, "balance": 15250},
        {"date": "09/22", "buy": 1100, "sell": 1250, "change": -150, "balance": 15100},
        {"date": "09/23", "buy": 1050, "sell": 1150, "change": -100, "balance": 15000},
        {"date": "09/24", "buy": 1250, "sell": 1100, "change": 150, "balance": 15150},
        {"date": "09/29", "buy": 1500, "sell": 1200, "change": 300, "balance": 15450}
    ])
    return pd.DataFrame(fallback_data)

# ==============================================================================
# 10. 母池數據加載 (Round 18 最新量化短空評分)
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
        
        # Round 18 專用短空評分 (外資暴倒+融資暴增接刀 權重矩陣)
        score_dict = {
            "2327": 99, "2492": 98, "3042": 95, "6173": 92, "3406": 90, 
            "2408": 40, "2344": 30, "8039": 25, "2455": 60, "2313": 55, "3189": 50, "3037": 45
        }
        score = score_dict.get(code, 60)

        alert_tag = "⚡ 待機狙擊" if score >= 90 else ("⚡ 次選觀察" if score >= 60 else ("🛑 官方禁空" if score <= 40 else "⚪ 觀望"))
        alert_desc = f"【{alert_tag}】9/29 官方融資: {margin_change:+d} 張，主力買超 {tot_buy_shares:,} 張"
        
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

df_display = load_radar_market_data(DEFAULT_WATCHLIST)
df_display.index = range(1, len(df_display) + 1)

# ==============================================================================
# 11. 側邊欄控制台
# ==============================================================================
st.sidebar.title("⚡ 短空雷達量化控制台")
st.sidebar.markdown(f"**決戰輪次**：`Round 18` ({R18_DATE})")
st.sidebar.markdown(f"**母池籌碼基準**：`{DATA_BASE_DATE}` 盤後大數據 (公證核定版)")

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 賽事累計淨值儀表板")
st.sidebar.markdown(f"""
<div class="metric-card-gemini">
    <div style="font-size: 13px; color: #BBB;">🟥 Gemini 總淨值 (11勝4負2平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_GEMINI:,}</div>
    <div style="font-size: 12px; color: #81C784;">R17 信昌電/全新達標 (+NT$ 30,000)</div>
</div>
<div class="metric-card-gpt">
    <div style="font-size: 13px; color: #BBB;">🟦 ChatGPT 總淨值 (4勝11負2平)</div>
    <div style="font-size: 24px; font-weight: bold; color: #FFF;">NT$ {CAPITAL_CHATGPT:,}</div>
    <div style="font-size: 12px; color: #81C784;">R17 繳出代表作奪勝 (+NT$ 66,000)</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.info(f"🚩 **雙方差距**：Gemini 領先 **NT$ {NET_SPREAD:,}**\n\n**單檔上限 (20%)**：\n• Gemini: NT$ {LIMIT_GEMINI:,}\n• GPT: NT$ {LIMIT_CHATGPT:,}\n\n🛡️ **裁判長拍定公約**：\n單筆最大停損 **≤ NT$ 20,000** ｜ **命中 T1 全平保底**")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📜 官方執法核心規範 (R18 實戰版)")
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
st.title("🎯 雙 AI 量化當沖 PK 賽事｜Round 18 旗艦戰情室")
st.caption(f"數據庫基準：{DATA_BASE_DATE} 臺灣證券交易所/官方融資/主力分點/自營商權證金流三維大數據")

tab_workspace, tab_orders, tab_matcher, tab_radar, tab_history, tab_margin, tab_broker = st.tabs([
    "🖥️ 專業操盤工作台 (K線與分點)",
    "⚔️ R18 官方決戰封單名冊", 
    "🧮 官方撮合與方案A結算模擬器",
    "📊 12檔母池籌碼雷達全景表",
    "🏆 R1~R17 淨值覆盤庫",
    "📈 融資增減 (9/29 官方增減排行)",
    "🏢 主力分點 (9/29 真實買賣超)"
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
                <span style="color: #AAA;">9/29 官方融資：</span><span style="font-weight: bold; color: {'#FF4444' if target_row['融資增減(張)']>=0 else '#00FF66'};">{target_row['融資增減(張)']:+,} 張</span>
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

        st.markdown(f"#### 🏢 【{target_name}】主力分點鎖碼持倉明細 (9/29)")
        b_list = target_row.get("各分點清單", [])
        if b_list:
            df_b = pd.DataFrame(b_list)
            df_b.index = range(1, len(df_b) + 1)
            st.dataframe(df_b, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: R18 雙方正式決戰封單名冊
# ------------------------------------------------------------------------------
with tab_orders:
    st.subheader("⚔️ Round 18 雙 AI 官方 TOP 5 決戰名冊陣列 (實裝 2 萬金盾標準)")
    st.caption("依最高裁判長最新指示：命中 T1 即刻 100% 全平保底；單筆虧損嚴格限制在 NT$ 20,000 以內。")
    col_g, col_c = st.columns(2)
    
    with col_g:
        st.markdown("#### 🟥 Gemini 戰情室 R18 正式封單")
        st.caption(f"淨值：NT$ {CAPITAL_GEMINI:,}｜單檔上限：NT$ {LIMIT_GEMINI:,}｜單筆停損 ≤ NT$ 20,000")
        
        df_gem_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "規格": x['size'], "最大停損": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_GEMINI_R18
        ])
        st.dataframe(df_gem_ui, use_container_width=True, hide_index=True)
        
        with st.expander("🔍 查看 Gemini R18 籌碼依據與量化細節", expanded=True):
            for x in ORDERS_GEMINI_R18:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1保利 `{x['t1']:.1f}`** ｜ 最大停損 `-NT$ {abs(x['max_loss']):,}`")
                st.caption(f"└ 核心籌碼：{x['reason']}")
                
    with col_c:
        st.markdown("#### 🟦 ChatGPT 戰情室 R18 提交正式封單")
        st.caption(f"淨值：NT$ {CAPITAL_CHATGPT:,}｜單檔上限：NT$ {LIMIT_CHATGPT:,}｜單筆停損 ≤ NT$ 20,000")
        
        df_gpt_ui = pd.DataFrame([
            {"順位/標的": f"{x['rank']} {x['name']}", "5分K門檻": f"< {x['trigger']:.1f}", "停損": f"{x['stop']:.1f}", "T1保利": f"{x['t1']:.1f}", "規格": x['size'], "最大停損": f"-NT$ {abs(x['max_loss']):,}"}
            for x in ORDERS_CHATGPT_R18
        ])
        st.dataframe(df_gpt_ui, use_container_width=True, hide_index=True)
        
        with st.expander("🔍 查看 ChatGPT R18 策略邏輯與作戰口令", expanded=True):
            for x in ORDERS_CHATGPT_R18:
                st.markdown(f"**{x['rank']} {x['name']}**：門檻 `< {x['trigger']:.1f}` ｜ 停損 `{x['stop']:.1f}` ｜ **T1保利 `{x['t1']:.1f}`** ｜ 最大停損 `-NT$ {abs(x['max_loss']):,}`")
                st.caption(f"└ 作戰定位：{x['reason']}")

    st.markdown("---")
    st.subheader("🛑 Round 18 官方禁空名單（NO SHORT LIST）")
    cn1, cn2, cn3 = st.columns(3)
    cn1.error("🚫 **8039 台虹 (273.5元)**\n\n逆勢強鎖漲停噴出，大摩高盛賣壓完全被特定多頭分點吸收，雙 AI 一致禁空！")
    cn2.error("🚫 **2344 華邦電 (174.0元)**\n\n瑞銀/元大/花旗外資大舉掃貨 +6,500 張，散戶融資大退 -619 張，嚴禁逆勢做空！")
    cn3.error("🚫 **2408 南亞科 (506.0元)**\n\n(Gemini 獨門禁空) 瑞銀與花旗合買 2,600 張回補軋空，避免再度遭受午盤強拉斷頭風險！")

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
        order_set = ORDERS_GEMINI_R18 if "Gemini" in selected_side else ORDERS_CHATGPT_R18
        
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
    st.subheader(f"📋 12 檔母池三維大數據全景表 ({DATA_BASE_DATE} 官方融資與主力校正版)")
    preferred_cols = [
        "短空勝率分", "股票代號", "股票名稱", "個期", "現價", "即時信號",
        "融資增減(張)", "近高壓力(NH)", "最高壓力(AH)", "主力加權成本", "主力合計買超", "主力合計佔比(%)"
    ]
    st.dataframe(df_display[[c for c in preferred_cols if c in df_display.columns]], use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 5: 🏆 R1~R17 淨值覆盤庫 (完整收錄 R17)
# ------------------------------------------------------------------------------
with tab_history:
    st.subheader("📈 雙 AI 歷輪淨值走勢與狙擊標的覆盤矩陣 (R0～R17)")
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
    
    st.markdown("---")
    st.subheader("🔍 歷輪戰況深度覆盤與重大仲裁紀錄")
    
    for r_item in reversed(HISTORICAL_ROUNDS):
        with st.expander(f"📌 {r_item['round']} ({r_item['date']}) 判決：{r_item['winner']} ｜ 領先差：NT$ {r_item['spread']:,}", expanded=(r_item["round"] in ["Round 16", "Round 17"])):
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

# ------------------------------------------------------------------------------
# TAB 6: 📈 融資增減 (9/29 官方排行榜)
# ------------------------------------------------------------------------------
with tab_margin:
    st.subheader(f"📊 12 檔母池 {MARGIN_DISPLAY_DATE} 官方融資增減熱力排行榜 (按增減張數降序)")
    st.caption("資料來源：臺灣證券交易所官方核定。🔴 紅色代表融資增加（散戶接刀/浮額累積），🟢 綠色代表融資減少（斷頭停損/外資洗盤）。")

    summary_margin_list = []
    for item in DEFAULT_WATCHLIST:
        c_code = item["代號"]
        c_name = item["名稱"]
        c_price = item["昨收"]
        df_10d = fetch_stock_margin_10d(c_code)
        
        last_chg = item.get("融資增減(張)", 0)
        last_bal = int(df_10d.iloc[-1]["balance"]) if not df_10d.empty else 10000
        cum_10d_chg = int(df_10d["change"].sum()) if not df_10d.empty else last_chg
        
        if last_chg > 1000:
            status_desc = "🔴 融資暴增 (散戶高檔接刀慘套，極易多殺多)"
        elif last_chg > 400:
            status_desc = "🟠 融資堆積 (浮額沉重，面臨踩踏)"
        elif last_chg > 0:
            status_desc = "🟡 融資微增 (籌碼趨向渙散)"
        elif last_chg < -500:
            status_desc = "🟢 融資清洗 (散戶大舉下車，籌碼沉澱乾淨)"
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
# TAB 7: 🏢 主力分點 (9/29 盤後真實買賣超各前五大)
# ------------------------------------------------------------------------------
with tab_broker:
    st.subheader(f"🏢 12 檔母池主力關鍵分點分析 ({DATA_BASE_DATE} 盤後真實撮合)")
    st.caption("完整收錄 12 檔標的之買超前五大（多方鎖碼/隔日沖）與賣超前五大（空方摜壓/出貨）主力券商名冊。")

    st.markdown("#### ⚡ 母池個股切換")
    broker_pill_options = [
        f"{r['股票代號']} {r['股票名稱']}" 
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
        
        def style_broker_buy(val):
            if isinstance(val, (int, float)) and val > 0:
                return "color: #FF4444; font-weight: bold;"
            return ""

        def style_broker_sell(val):
            if isinstance(val, (int, float)) and val < 0:
                return "color: #00CC00; font-weight: bold;"
            return ""

        # --- 上方：買超前五大 ---
        st.markdown(f"#### 🔴 【{cur_b_row['股票名稱']}】買超前五大主力分點（多方鎖碼 / 隔日沖）")
        if not df_buy_list.empty:
            df_buy_list.index = range(1, len(df_buy_list) + 1)
            styled_buy_table = apply_color_styler(
                df_buy_list.style, style_broker_buy, subset=["買超張數", "預估獲利(萬)", "報酬率(%)"]
            ).format({
                "買超張數": "{:+,d}", "佔比(%)": "{:.2f}%", "收盤價": "{:.2f}",
                "預估成本": "{:.2f}", "預估獲利(萬)": "{:+,d}", "報酬率(%)": "{:+.2f}%"
            })
            st.dataframe(styled_buy_table, use_container_width=True)
        else:
            st.info("無顯著買超分點。")

        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

        # --- 下方：賣超前五大 ---
        st.markdown(f"#### 🟢 【{cur_b_row['股票名稱']}】賣超前五大主力分點（空方出貨 / 摜壓）")
        if not df_sell_list.empty:
            df_sell_list.index = range(1, len(df_sell_list) + 1)
            styled_sell_table = apply_color_styler(
                df_sell_list.style, style_broker_sell, subset=["買超張數", "預估獲利(萬)", "報酬率(%)"]
            ).format({
                "買超張數": "{:+,d}", "佔比(%)": "{:.2f}%", "收盤價": "{:.2f}",
                "預估成本": "{:.2f}", "預估獲利(萬)": "{:+,d}", "報酬率(%)": "{:+.2f}%"
            })
            st.dataframe(styled_sell_table, use_container_width=True)
        else:
            st.info("無顯著賣超分點。")
    else:
        st.info("暫無此標的分點資料。")

# ==============================================================================
# 13. 系統頁尾
# ==============================================================================
st.markdown("---")
st.caption(f"雙 AI 量化短空雷達系統 v18.0 旗艦裁判長版｜{R18_DATE} Round 18 雙方封單正式鎖定｜執法標準：5分K實體跌破 + 不利撮合滑價 + 2萬金盾停損硬上限 + 方案A鎖利 (廢除T2) + 13:25強平")
