import json
import time
from datetime import datetime
from typing import Any, Dict, Optional
import pandas as pd
import requests
import streamlit as st

# ==========================================
# 1. 系統組態與母池設定
# ==========================================
UNIVERSE = {
    "8039": {"name": "台虹", "market": "TWSE"},
    "2408": {"name": "南亞科", "market": "TWSE"},
    "2327": {"name": "國巨", "market": "TWSE"},
    "2344": {"name": "華邦電", "market": "TWSE"},
    "3037": {"name": "欣興", "market": "TWSE"},
    "2313": {"name": "華通", "market": "TWSE"},
    "2455": {"name": "全新", "market": "TWSE"},
    "3406": {"name": "玉晶光", "market": "TWSE"},
    "2492": {"name": "華新科", "market": "TWSE"},
    "3042": {"name": "晶技", "market": "TWSE"},
    "3189": {"name": "景碩", "market": "TWSE"},
    "6173": {"name": "信昌電", "market": "TPEx"},
}


# ==========================================
# 2. 數據服務：臺灣證券交易所 (TWSE) 官方 API
# ==========================================
class StockDataService:

  def __init__(self):
    self.headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }

  def fetch_twse_margin(self, date_str: str) -> Dict[str, Any]:
    """從證交所抓取全市場融資融券明細，自動定位個股表並清洗代號空白"""
    url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={date_str}&selectType=ALL&response=json"
    margin_dict = {}
    try:
      resp = requests.get(url, headers=self.headers, timeout=10)
      if resp.status_code == 200:
        data = resp.json()

        # 遍歷所有 tables，精準鎖定包含「代號」與「買進」的個股明細表
        target_rows = []
        for table in data.get("tables", []):
          fields = table.get("fields", [])
          if any("代號" in f for f in fields) and any(
              "買進" in f for f in fields
          ):
            target_rows = table.get("data", [])
            break

        if not target_rows:
          target_rows = data.get("data", [])

        for row in target_rows:
          if len(row) < 7:
            continue

          # 清洗代號：去除全形與半形空格
          code = str(row[0]).strip().replace(" ", "")

          if code in UNIVERSE:
            buy_qty = int(str(row[2]).replace(",", "").strip() or 0)
            sell_qty = int(str(row[3]).replace(",", "").strip() or 0)
            cash_qty = int(str(row[4]).replace(",", "").strip() or 0)
            balance = int(str(row[6]).replace(",", "").strip() or 0)

            # 單日淨增減 = 買進 - 賣出 - 現金償還
            net_change = buy_qty - sell_qty - cash_qty

            margin_dict[code] = {
                "margin_change": net_change,
                "margin_balance": balance,
            }
    except Exception as e:
      print(f"TWSE 融資抓取異常: {e}")
    return margin_dict

  def fetch_twse_institutional(self, date_str: str) -> Dict[str, Any]:
    """從證交所抓取外陸資買賣超股數並換算為張數"""
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALLBUT0999&response=json"
    inst_dict = {}
    try:
      resp = requests.get(url, headers=self.headers, timeout=10)
      if resp.status_code == 200:
        data = resp.json()
        for row in data.get("data", []):
          code = str(row[0]).strip().replace(" ", "")
          if code in UNIVERSE:
            foreign_net = int(str(row[4]).replace(",", "").strip() or 0)
            inst_dict[code] = {"foreign_net_sheets": foreign_net // 1000}
    except Exception as e:
      print(f"TWSE 法人抓取異常: {e}")
    return inst_dict


# ==========================================
# 3. Streamlit 網頁應用介面
# ==========================================
st.set_page_config(page_title="短空狙擊雷達 - 正式版", layout="wide")
st.title("⚡ 短空狙擊雷達：12 檔母池「30 家短空分點 × 融資增減」矩陣")

service = StockDataService()

with st.sidebar:
  st.header("⚙️ 控制台")
  selected_date = st.date_input("查詢日期", value=None)
  date_param = (
      selected_date.strftime("%Y%m%d")
      if selected_date
      else datetime.now().strftime("%Y%m%d")
  )

  if st.button("🔄 刷新數據"):
    st.cache_data.clear()
    st.rerun()

  st.markdown("---")
  st.markdown("""
    **💡 量化空方評級：**
    * 🚨 **多殺多引信**：融資逆勢大增 ＋ 外資狂砍
    * ⚠️ **隔日沖倒貨**：鎖漲停隔日沖重壓，待開盤踩踏
    * 🛡️ **浮額清洗**：融資暴減清洗乾淨（防強彈）
    """)


@st.cache_data(ttl=300)
def load_market_data(d_str: str):
  margin_data = service.fetch_twse_margin(d_str)
  inst_data = service.fetch_twse_institutional(d_str)
  return margin_data, inst_data


with st.spinner("正在自臺灣證券交易所官方 API 同步融資與法人數據..."):
  margin_map, inst_map = load_market_data(date_param)

# 整合 12 檔母池看板
summary_rows = []
for code, info in UNIVERSE.items():
  m_info = margin_map.get(code, {"margin_change": 0, "margin_balance": 0})
  i_info = inst_map.get(code, {"foreign_net_sheets": 0})

  m_change = m_info["margin_change"]
  f_net = i_info["foreign_net_sheets"]

  # 量化空方條件研判
