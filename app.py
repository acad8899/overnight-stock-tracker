import json
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import pandas as pd
import requests
import streamlit as st

# ==========================================
# 1. 系統組態：12 檔母池設定
# ==========================================
UNIVERSE = {
    "8039": {"name": "台虹", "market": "TWSE", "close": 311.5, "high": 311.5, "low": 288.5},
    "2408": {"name": "南亞科", "market": "TWSE", "close": 447.5, "high": 461.0, "low": 443.5},
    "2327": {"name": "國巨", "market": "TWSE", "close": 567.0, "high": 595.0, "low": 567.0},
    "2344": {"name": "華邦電", "market": "TWSE", "close": 161.5, "high": 165.0, "low": 156.0},
    "3037": {"name": "欣興", "market": "TWSE", "close": 1090.0, "high": 1125.0, "low": 1085.0},
    "2313": {"name": "華通", "market": "TWSE", "close": 248.0, "high": 250.5, "low": 233.0},
    "2455": {"name": "全新", "market": "TWSE", "close": 493.0, "high": 508.0, "low": 487.0},
    "3406": {"name": "玉晶光", "market": "TWSE", "close": 1085.0, "high": 1220.0, "low": 1050.0},
    "2492": {"name": "華新科", "market": "TWSE", "close": 395.0, "high": 418.0, "low": 385.0},
    "3042": {"name": "晶技", "market": "TWSE", "close": 188.0, "high": 193.0, "low": 185.5},
    "3189": {"name": "景碩", "market": "TWSE", "close": 1000.0, "high": 1045.0, "low": 988.0},
    "6173": {"name": "信昌電", "market": "TPEx", "close": 0.0, "high": 0.0, "low": 0.0},
}

# 10/16 主力買賣超合計基準（張）
MAJOR_NET_SUMMARY = {
    "8039": 8586,
    "2408": -5807,
    "2327": -5643,
    "3037": -3212,
    "2344": 8054,
    "2313": 9574,
    "3406": -695,
    "2492": -1342,
    "3042": 15,
    "3189": -310,
    "2455": 252,
    "6173": 0
}

# 30 家重點分點明細
def get_stock_brokers(code: str):
    if code == "8039":
        return [
            {"分點": "富邦", "屬性": "隔日沖鎖單", "買賣超": 3493, "均價": 311.21, "佔比": 11.93},
            {"分點": "凱基-城中", "屬性": "隔日沖鎖單", "買賣超": 1548, "均價": 310.82, "佔比": 5.28},
            {"分點": "凱基-台北", "屬性": "隔日沖鎖單", "買賣超": 1159, "均價": 307.02, "佔比": 3.96},
            {"分點": "統一", "屬性": "隔日沖鎖單", "買賣超": 770, "均價": 310.02, "佔比": 2.63},
            {"分點": "統一-城中", "屬性": "隔日沖鎖單", "買賣超": 728, "均價": 311.36, "佔比": 2.49},
            {"分點": "元大", "屬性": "短空當沖", "買賣超": 707, "均價": 303.94, "佔比": 2.41},
            {"分點": "國票-敦北法人", "屬性": "隔日沖鎖單", "買賣超": 691, "均價": 311.50, "佔比": 2.36},
            {"分點": "國泰-敦南", "屬性": "短線出貨", "買賣超": -638, "均價": 306.42, "佔比": 2.18}
        ]
    elif code == "2408":
        return [
            {"分點": "美林", "屬性": "外資出貨", "買賣超": -3797, "均價": 452.65, "佔比": 8.06},
            {"分點": "美商高盛", "屬性": "外資重磅提款", "買賣超": -3604, "均價": 449.41, "佔比": 7.65},
            {"分點": "第一金-自由", "屬性": "散戶接刀", "買賣超": 2137, "均價": 451.84, "佔比": 4.54},
            {"分點": "富邦", "屬性": "短線買超", "買賣超": 1977, "均價": 457.32, "佔比": 4.20},
            {"分點": "摩根大通", "屬性": "外資出貨", "買賣超": -884, "均價": 449.45, "佔比": 1.88},
            {"分點": "台灣摩根士丹利", "屬性": "外資出貨", "買賣超": -779, "均價": 450.88, "佔比": 1.65}
        ]
    elif code == "2327":
        return [
            {"分點": "美林", "屬性": "外資出貨", "買賣超": -2669, "均價": 582.34, "佔比": 7.36},
            {"分點": "凱基", "屬性": "短空當沖", "買賣超": -2092, "均價": 580.90, "佔比": 5.76},
            {"分點": "摩根大通", "屬性": "外資出貨", "買賣超": -1337, "均價": 579.49, "佔比": 3.68},
            {"分點": "新加坡商瑞銀", "屬性": "外資回補", "買賣超": 1274, "均價": 575.99, "佔比": 3.51},
            {"分點": "台灣摩根士丹利", "屬性": "外資出貨", "買賣超": -811, "均價": 577.80, "佔比": 2.23}
        ]
    elif code == "3037":
        return [
            {"分點": "美商高盛", "屬性": "外資重磅提款", "買賣超": -3178, "均價": 1099.36, "佔比": 21.26},
            {"分點": "台灣摩根士丹利", "屬性": "外資出貨", "買賣超": -865, "均價": 1100.91, "佔比": 5.79},
            {"分點": "統一", "屬性": "本土買盤", "買賣超": 831, "均價": 1101.42, "佔比": 5.56}
        ]
    elif code == "2344":
        return [
            {"分點": "新加坡商瑞銀", "屬性": "外資回補", "買賣超": 3195, "均價": 162.16, "佔比": 6.74},
            {"分點": "元大", "屬性": "主力回補", "買賣超": 2585, "均價": 162.34, "佔比": 5.45},
            {"分點": "台灣摩根士丹利", "屬性": "外資回補", "買賣超": 2274, "均價": 162.48, "佔比": 4.80}
        ]
    elif code == "2313":
        return [
            {"分點": "港商野村", "屬性": "外資大買", "買賣超": 6614, "均價": 250.32, "佔比": 13.14},
            {"分點": "美商高盛", "屬性": "外資買超", "買賣超": 2960, "均價": 248.72, "佔比": 5.88}
        ]
    return []

# ==========================================
# 2. 數據服務：TWSE 官方 API 爬蟲
# ==========================================
class StockDataService:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

    def fetch_twse_margin(self, date_str: str) -> Dict[str, Any]:
        url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={date_str}&selectType=ALL&response=json"
        margin_dict = {}
        try:
            resp = requests.get(url, headers=self.headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                target_rows = []
                for table in data.get("tables", []):
                    fields = table.get("fields", [])
                    if any("代號" in f for f in fields) and any("買進" in f for f in fields):
                        target_rows = table.get("data", [])
                        break
                if not target_rows:
                    target_rows = data.get("data", [])

                for row in target_rows:
                    if len(row) < 7:
                        continue
                    code = str(row[0]).strip().replace(" ", "")
                    if code in UNIVERSE:
                        buy_qty = int(str(row[2]).replace(",", "").strip() or 0)
                        sell_qty = int(str(row[3]).replace(",", "").strip() or 0)
                        cash_qty = int(str(row[4]).replace(",", "").strip() or 0)
                        balance = int(str(row[6]).replace(",", "").strip() or 0)
                        margin_dict[code] = {
                            "margin_change": buy_qty - sell_qty - cash_qty,
                            "margin_balance": balance,
                        }
        except Exception:
            pass
        return margin_dict

    def fetch_twse_institutional(self, date_str: str) -> Dict[str, Any]:
        url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALLBUT0999&response=json"
        inst_dict = {}
        try:
            resp = requests.get(url, headers=self.headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                for row in data.get("data", []):
                    code = str(row[0]).strip().replace(" ", "")
                    if code in UNIVERSE:
                        foreign_net = int(str(row[4]).replace(",", "").strip() or 0)
                        inst_dict[code] = {"foreign_net_sheets": foreign_net // 1000}
        except Exception:
            pass
        return inst_dict

# ==========================================
# 3. Streamlit 網頁應用介面
# ==========================================
st.set_page_config(page_title="短空狙擊雷達 - 旗艦分析版", layout="wide")
st.title("⚡ 短空狙擊雷達：AI 評級 × 勝率演算 × 主力分點穿透")

service = StockDataService()
default_date = date(2026, 10, 16)

with st.sidebar:
    st.header("⚙️ 戰情控制台")
    selected_date = st.date_input("查詢日期", value=default_date)
    date_param = selected_date.strftime("%Y%m%d")

    night_market_drop = st.number_input(
        "台指夜盤跌點",
        value=-1144,
        step=-50,
        help="週五夜盤跌點，共振加權至空方模型",
