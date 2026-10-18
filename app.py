import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import requests
import streamlit as st

# ==========================================
# 1. 系統組態：12 檔母池與 30 家常見短空主力分點
# ==========================================
UNIVERSE = {
    "8039": {"name": "台虹", "symbol": "8039.TW"},
    "2408": {"name": "南亞科", "symbol": "2408.TW"},
    "2327": {"name": "國巨", "symbol": "2327.TW"},
    "2344": {"name": "華邦電", "symbol": "2344.TW"},
    "3037": {"name": "欣興", "symbol": "3037.TW"},
    "2313": {"name": "華通", "symbol": "2313.TW"},
    "2455": {"name": "全新", "symbol": "2455.TW"},
    "3406": {"name": "玉晶光", "symbol": "3406.TW"},
    "2492": {"name": "華新科", "symbol": "2492.TW"},
    "3042": {"name": "晶技", "symbol": "3042.TW"},
    "3189": {"name": "景碩", "symbol": "3189.TW"},
    "6173": {"name": "信昌電", "symbol": "6173.TWO"},
}

# 30 家常見短空與隔日沖主力分點定義
TOP30_SHORT_BROKERS = {
    # [1] 隔日沖鎖單倒貨天團 (10家) - 隔日早盤必拋售
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
    # [2] 國際外資提款重裝部隊 (8家) - 逢反彈大倒貨
    "台灣摩根士丹利": "外資出貨",
    "美商高盛": "外資出貨",
    "新加坡商瑞銀": "外資出貨",
    "美林": "外資出貨",
    "摩根大通": "外資出貨",
    "港商野村": "外資出貨",
    "花旗環球": "外資出貨",
    "港商麥格理": "外資出貨",
    # [3] 本土當沖與短空壓盤 (8家) - 當沖壓盤
    "元大": "短空當沖",
    "元大-台北": "短空當沖",
    "凱基": "短空當沖",
    "國泰-敦南": "短空當沖",
    "群益金鼎": "短空當沖",
    "群益金鼎-台北": "短空當沖",
    "永豐金": "短空當沖",
    "新光": "短空當沖",
    # [4] 地方隔日沖大戶 (4家) - 隔日沖出貨
    "玉山-嘉義": "隔日沖",
    "元大-新盛": "隔日沖",
    "國票-安和": "隔日沖",
    "統一-新台中": "隔日沖",
}


# ==========================================
# 2. Yahoo API 爬蟲服務（分點明細 + 融資融券）
# ==========================================
class YahooChipService:

  def __init__(self):
    self.broker_api = "https://tw.stock.yahoo.com/_td-stock/api/resource/StockServices.brokerTrading"
    self.margin_api = "https://tw.stock.yahoo.com/_td-stock/api/resource/StockServices.marginTrading"
    self.headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://tw.stock.yahoo.com/",
    }

  def get_stock_data(
      self, code: str, target_date: Optional[str] = None
  ) -> Optional[Dict[str, Any]]:
    meta = UNIVERSE.get(code)
    if not meta:
      return None

    symbol = meta["symbol"]
    params = {"symbol": symbol}
    if target_date:
      params["date"] = target_date

    buy_brokers, sell_brokers = [], []
    day_trade_lock_qty = 0  # 隔日沖鎖單買超張數
    foreign_dump_qty = 0  # 外資出貨賣超張數
    top30_active_list = []  # 命中的 30 家主力明細
    trade_date = target_date or "最新"

    # 1. 抓取券商分點數據
    try:
      resp_b = requests.get(
          self.broker_api, headers=self.headers, params=params, timeout=7
      )
      if resp_b.status_code == 200:
        data_b = resp_b.json()
        trade_date = data_b.get("date", trade_date)
        for item in data_b.get("list", []):
          diff_qty = item.get("diffQty", 0)
          b_name = item.get("brokerName", "")
          avg_p = round(item.get("avgPrice", 0.0), 2)
          ratio = item.get("ratio", 0.0)

          # 辨識是否為 30 家目標主力
          broker_tag = "一般券商"
          for target_name, tag in TOP30_SHORT_BROKERS.items():
            if target_name in b_name:
              broker_tag = tag
              top30_active_list.append({
                  "券商分點": b_name,
                  "類別": tag,
                  "買賣超(張)": diff_qty,
                  "均價": avg_p,
                  "佔比(%)": ratio,
              })
              if tag == "隔日沖" and diff_qty > 0:
                day_trade_lock_qty += diff_qty
              elif tag == "外資出貨" and diff_qty < 0:
                foreign_dump_qty += abs(diff_qty)
              break

          record = {
              "券商分點": b_name,
              "主力屬性": broker_tag,
              "買賣超(張)": diff_qty,
              "均價": avg_p,
              "佔比(%)": ratio,
          }

          if diff_qty > 0:
            buy_brokers.append(record)
          elif diff_qty < 0:
            sell_brokers.append(record)

        buy_brokers = sorted(
            buy_brokers, key=lambda x: x["買賣超(張)"], reverse=True
        )
        sell_brokers = sorted(sell_brokers, key=lambda x: x["買賣超(張)"])
    except Exception:
      pass

    # 2. 抓取信用交易 (融資增減)
    margin_change, margin_balance = 0, 0
    try:
      resp_m = requests.get(
          self.margin_api, headers=self.headers, params=params, timeout=7
      )
      if resp_m.status_code == 200:
        data_m = resp_m.json()
        m_list = data_m.get("list", [])
        if m_list:
          latest_m = m_list[0]
          margin_change = (
              latest_m.get("marginDiffQty")
              or latest_m.get("marginBalanceChange")
              or 0
          )
          margin_balance = latest_m.get("marginBalance", 0)
    except Exception:
      pass

    return {
        "code": code,
        "name": meta["name"],
        "date": trade_date,
        "margin_change": margin_change,
        "margin_balance": margin_balance,
        "day_trade_lock_qty": day_trade_lock_qty,
        "foreign_dump_qty": foreign_dump_qty,
        "top30_active_list": top30_active_list,
        "buy_brokers": buy_brokers,
        "sell_brokers": sell_brokers,
    }


# ==========================================
# 3. Streamlit 網頁應用看板
# ==========================================
st.set_page_config(page_title="短空狙擊雷達 - 30家短空主力版", layout="wide")
st.title("⚡ 短空狙擊雷達：12 檔母池「30 家短空分點 × 融資增減」矩陣")

crawler = YahooChipService()


@st.cache_data(ttl=300)
def load_all_chips(date_str: Optional[str] = None):
  results = {}
  for code in UNIVERSE.keys():
    data = crawler.get_stock_data(code, date_str)
    if data:
      results[code] = data
    time.sleep(0.3)
  return results


with st.sidebar:
  st.header("⚙️ 控制台")
  selected_date = st.date_input("查詢日期", value=None)
  date_param = selected_date.strftime("%Y-%m-%d") if selected_date else None

  if st.button("🔄 刷新籌碼數據"):
    st.cache_data.clear()
    st.rerun()

  st.markdown("---")
  st.subheader("🎯 30 家重點監控短空分點")
  st.caption(
      "包含凱基台北、城中、富邦、國票敦北、大摩、小摩、高盛、瑞銀、美林等 30"
      " 家核心主力。"
  )

with st.spinner("正在自 Yahoo API 解析 12 檔母池 30 家主力分點明細與融資..."):
  pool_data = load_all_chips(date_param)

# ==========================================
# 4. 母池快篩大盤表
# ==========================================
summary_list = []
for code, d in pool_data.items():
  # 空方狀態智能診斷
  tag = "中立觀望"
  if d["margin_change"] > 500 and d["foreign_dump_qty"] > 2000:
    tag = "🚨 多殺多引信 (資增 + 外資暴倒)"
  elif d["day_trade_lock_qty"] > 1500 and d["margin_change"] >= 0:
    tag = "⚠️ 隔日沖倒貨 (短線主力鎖單)"
  elif d["margin_change"] < -1000:
    tag = "🛡️ 浮額清洗 (防跌深強彈)"

  summary_list.append({
      "代號": code,
      "名稱": d["name"],
      "融資增減(張)": d["margin_change"],
      "外資狂倒量(張)": -d["foreign_dump_qty"],
      "隔日沖鎖單(張)": d["day_trade_lock_qty"],
      "30家主力活躍數": len(d["top30_active_list"]),
      "空方量化評級": tag,
  })

df_summary = pd.DataFrame(summary_list).sort_values(
    by="融資增減(張)", ascending=False
)

st.subheader("📋 12 檔母池 30 家短空主力活躍總表")
st.dataframe(
    df_summary,
    use_container_width=True,
    hide_index=True,
    column_config={
        "融資增減(張)": st.column_config.NumberColumn(format="%+d"),
        "外資狂倒量(張)": st.column_config.NumberColumn(format="%+d"),
        "隔日沖鎖單(張)": st.column_config.NumberColumn(format="%d"),
    },
)

st.divider()

# ==========================================
# 5. 單檔個股 30 家分點穿透檢視
# ==========================================
selected_code = st.selectbox(
    "選擇要深入穿透分點的標的：",
    options=list(UNIVERSE.keys()),
    format_func=lambda x: f"{x} {UNIVERSE[x]['name']}",
)

target = pool_data.get(selected_code)

if target:
  c1, c2, c3, c4 = st.columns(4)
  c1.metric(
      "融資增減",
      f"{target['margin_change']:+d} 張",
      delta_color="inverse",
      delta=f"{target['margin_change']} 張",
  )
  c2.metric(
      "隔日沖大軍鎖單",
      f"{target['day_trade_lock_qty']} 張",
      help="凱基台北、城中、富邦、國票敦北等鎖單量",
  )
  c3.metric(
      "外資集團狂倒量",
      f"-{target['foreign_dump_qty']} 張",
      help="高盛、摩根士丹利、瑞銀、美林等倒貨量",
  )
  c4.metric("融資總餘額", f"{target['margin_balance']:,} 張")

  st.markdown("#### 🎯 命中 30 家短空主力之分點進出明細")
  if target["top30_active_list"]:
    df_top30 = pd.DataFrame(target["top30_active_list"]).sort_values(
        by="買賣超(張)", key=abs, reverse=True
    )
    st.dataframe(df_top30, use_container_width=True, hide_index=True)
  else:
    st.info("今日無顯著的 30 家目標短空主力分點進出。")

  b_col, s_col = st.columns(2)
  with b_col:
    st.markdown("##### 🟢 買超前 10 大分點 (標註主力屬性)")
    st.dataframe(
        pd.DataFrame(target["buy_brokers"][:10]),
        use_container_width=True,
        hide_index=True,
    )
  with s_col:
    st.markdown("##### 🔴 賣超前 10 大分點 (標註主力屬性)")
    st.dataframe(
        pd.DataFrame(target["sell_brokers"][:10]),
        use_container_width=True,
        hide_index=True,
    )
