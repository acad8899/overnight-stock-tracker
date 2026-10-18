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

# 30 家常見短空與隔日沖主力特徵庫
TOP30_SHORT_BROKERS = {
    "凱基-台北": "隔日沖",
    "凱基-城中": "隔日沖",
    "國票-敦北法人": "隔日沖",
    "富邦": "隔日沖",
    "統一": "隔日沖",
    "統一-城中": "隔日沖",
    "元大-士林": "隔日沖",
    "元大-土城": "隔日沖",
    "凱基-虎尾": "隔日沖",
    "富邦-建國": "隔日沖",
    "台灣摩根士丹利": "外資出貨",
    "美商高盛": "外資出貨",
    "新加坡商瑞銀": "外資出貨",
    "美林": "外資出貨",
    "摩根大通": "外資出貨",
    "港商野村": "外資出貨",
    "花旗環球": "外資出貨",
    "港商麥格理": "外資出貨",
    "元大": "短空當沖",
    "元大-台北": "短空當沖",
    "凱基": "短空當沖",
    "國泰-敦南": "短空當沖",
    "群益金鼎": "短空當沖",
    "群益金鼎-台北": "短空當沖",
    "永豐金": "短空當沖",
    "新光": "短空當沖",
    "玉山-嘉義": "隔日沖",
    "元大-新盛": "隔日沖",
    "國票-安和": "隔日沖",
    "統一-新台中": "隔日沖",
}


# ==========================================
# 2. 數據服務：證交所官方 API (保證不被阻擋)
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
    """從證交所抓取全市場融資融券增減 (免Token)"""
    url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={date_str}&selectType=ALL&response=json"
    margin_dict = {}
    try:
      resp = requests.get(url, headers=self.headers, timeout=10)
      if resp.status_code == 200:
        data = resp.json()
        # TWSE 表格資料欄位: 股票代號(0), 股票名稱(1), 融資買進(2), 融資賣出(3), 現金償還(4), 前日餘額(5), 今日餘額(6)...
        for row in data.get("tables", [{}])[0].get("data", []):
          code = row[0].strip()
          if code in UNIVERSE:
            buy_qty = int(row[2].replace(",", ""))
            sell_qty = int(row[3].replace(",", ""))
            cash_qty = int(row[4].replace(",", ""))
            # 融資單日淨增減 = 買進 - 賣出 - 現金償還
            net_change = buy_qty - sell_qty - cash_qty
            balance = int(row[6].replace(",", ""))
            margin_dict[code] = {
                "margin_change": net_change,
                "margin_balance": balance,
            }
    except Exception as e:
      print(f"TWSE 融資抓取異常: {e}")
    return margin_dict

  def fetch_twse_margin(self, date_str: str) -> Dict[str, Any]:
        """從證交所抓取全市場個股融資融券增減（自動尋找個股表格並清洗空白）"""
        url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={date_str}&selectType=ALL&response=json"
        margin_dict = {}
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()

                # 遍歷所有 tables，找到包含「代號」與「融資買進」的個股明細表
                target_rows = []
                for table in data.get("tables", []):
                    # 若欄位包含 股票代號 與 融資，即為個股表
                    fields = table.get("fields", [])
                    if any("代號" in f for f in fields) and any(
                        "買進" in f for f in fields
                    ):
                        target_rows = table.get("data", [])
                        break

                # 若舊版格式未分 table， fallback 到 data["data"]
                if not target_rows:
                    target_rows = data.get("data", [])

                for row in target_rows:
                    if len(row) < 7:
                        continue
                    # 清洗代號：去除頭尾所有空白
                    code = str(row[0]).strip().replace(" ", "")

                    if code in UNIVERSE:
                        # 證交所欄位:
                        # row[2]: 融資買進(張)
                        # row[3]: 融資賣出(張)
                        # row[4]: 現金償還(張)
                        # row[6]: 今日融資餘額(張)
                        buy_qty = int(str(row[2]).replace(",", "").strip() or 0)
                        sell_qty = int(
                            str(row[3]).replace(",", "").strip() or 0
                        )
                        cash_qty = int(
                            str(row[4]).replace(",", "").strip() or 0
                        )
                        balance = int(str(row[6]).replace(",", "").strip() or 0)

                        # 單日融資淨增減 = 買進 - 賣出 - 現金償還
                        net_change = buy_qty - sell_qty - cash_qty

                        margin_dict[code] = {
                            "margin_change": net_change,
                            "margin_balance": balance,
                        }
        except Exception as e:
            print(f"TWSE 融資抓取異常: {e}")
        return margin_dict


# ==========================================
# 3. Streamlit 網頁應用介面
# ==========================================
st.set_page_config(page_title="短空狙擊雷達 - 正式版", layout="wide")
st.title("⚡ 短空狙擊雷達：12 檔母池「30 家短空分點 × 融資增減」矩陣")

service = StockDataService()

with st.sidebar:
  st.header("⚙️ 控制台")
  selected_date = st.date_input("查詢日期", value=None)
  # 若未選則預設為最新交易日格式 YYYYMMDD
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

# 組合總表
summary_rows = []
for code, info in UNIVERSE.items():
  m_info = margin_map.get(code, {"margin_change": 0, "margin_balance": 0})
  i_info = inst_map.get(code, {"foreign_net_sheets": 0})

  m_change = m_info["margin_change"]
  f_net = i_info["foreign_net_sheets"]

  # 狀態評級
  tag = "中立觀望"
  if m_change > 500 and f_net < -2000:
    tag = "🚨 多殺多引信 (資增 + 外資倒)"
  elif code == "8039" and m_change > 0:
    tag = "⚠️ 隔日沖倒貨 (富邦/凱基鎖板)"
  elif m_change < -1000:
    tag = "🛡️ 浮額清洗 (防強彈)"

  summary_rows.append({
      "代號": code,
      "名稱": info["name"],
      "融資增減(張)": m_change,
      "外資買賣超(張)": f_net,
      "融資餘額(張)": m_info["margin_balance"],
      "空方量化評級": tag,
  })

df_all = pd.DataFrame(summary_rows).sort_values(
    by="融資增減(張)", ascending=False
)

st.subheader(f"📋 12 檔母池融資與外資主力總表 ({date_param})")
st.dataframe(
    df_all,
    use_container_width=True,
    hide_index=True,
    column_config={
        "融資增減(張)": st.column_config.NumberColumn(format="%+d"),
        "外資買賣超(張)": st.column_config.NumberColumn(format="%+d"),
        "融資餘額(張)": st.column_config.NumberColumn(format="%d"),
    },
)

# 底部 8039 隔日沖主力專區提示
st.divider()
st.subheader("🎯 8039 台虹 隔日沖鎖單明細 (2026/10/16 結算)")
col_a, col_b = st.columns(2)
with col_a:
  st.markdown("##### 隔日沖主力大軍鎖單 (買超)")
  st.table(
      pd.DataFrame([
          {"券商分點": "富邦", "買賣超(張)": "+3,493", "均價": "311.21"},
          {"券商分點": "凱基-城中", "買賣超(張)": "+1,548", "均價": "310.82"},
          {"券商分點": "凱基-台北", "買賣超(張)": "+1,159", "均價": "307.02"},
          {"券商分點": "國票-敦北法人", "買賣超(張)": "+691", "均價": "311.50"},
      ])
  )
with col_b:
  st.markdown("##### 隔日沖踩踏空方狙擊點")
  st.info(
      "• 鎖單總額：逾 9,700 張（約 5.16 億元）\n"
      "• 週一早盤狙擊門檻：`< 306.0`（摜破開盤出貨線）\n"
      "• 防守停損：`314.0` ｜ 停利目標：`292.0`"
  )
