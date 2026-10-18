import json
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import pandas as pd
import requests
import streamlit as st

# ==========================================
# 1. 系統組態：12 檔母池與 30 家短空主力庫
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

# 30 家精選短空與隔日沖主力庫
TOP30_BROKERS = {
    # 隔日沖出貨幫 (10家)
    "富邦": "隔日沖鎖單", "凱基-台北": "隔日沖鎖單", "凱基-城中": "隔日沖鎖單",
    "國票-敦北法人": "隔日沖鎖單", "統一": "隔日沖鎖單", "統一-城中": "隔日沖鎖單",
    "元大-士林": "隔日沖鎖單", "元大-土城": "隔日沖鎖單", "凱基-虎尾": "隔日沖鎖單", "富邦-建國": "隔日沖鎖單",
    # 外資出貨天團 (8家)
    "美商高盛": "外資重磅提款", "台灣摩根士丹利": "外資出貨", "美林": "外資出貨",
    "摩根大通": "外資出貨", "新加坡商瑞銀": "外資主力", "港商野村": "外資主力",
    "花旗環球": "外資出貨", "港商麥格理": "外資出貨",
    # 本土當沖與壓盤分點 (8家)
    "元大": "短空當沖", "元大-台北": "短空當沖", "凱基": "短空當沖", "國泰-敦南": "短線出貨",
    "群益金鼎": "短空當沖", "群益金鼎-台北": "短空當沖", "永豐金": "短空當沖", "新光": "短空當沖",
    # 地方短線大戶 (4家)
    "玉山-嘉義": "隔日沖出貨", "元大-新盛": "隔日沖出貨", "國票-安和": "隔日沖出貨", "統一-新台中": "隔日沖出貨"
}

# 內建 10/16 關鍵主力分點明細庫 (直接對齊 Yahoo 官方公布資料)
CHIP_DETAIL_DATABASE = {
    "8039": [
        {"分點": "富邦", "屬性": "隔日沖鎖單", "買賣超": +3493, "均價": 311.21, "佔比": 11.93},
        {"分點": "凱基-城中", "屬性": "隔日沖鎖單", "買賣超": +1548, "均價": 310.82, "佔比": 5.28},
        {"分點": "凱基-台北", "屬性": "隔日沖鎖單", "買賣超": +1159, "均價": 307.02, "佔比": 3.96},
        {"分點": "統一", "屬性": "隔日沖鎖單", "買賣超": +770, "均價": 310.02, "佔比": 2.63},
        {"分點": "統一-城中", "屬性": "隔日沖鎖單", "買賣超": +728, "均價": 311.36, "佔比": 2.49},
        {"分點": "元大", "屬性": "短空當沖", "買賣超": +707, "均價": 303.94, "佔比": 2.41},
        {"分點": "國票-敦北法人", "屬性": "隔日沖鎖單", "買賣超": +691, "均價": 311.50, "佔比": 2.36},
        {"分點": "國泰-敦南", "屬性": "短線出貨", "買賣超": -638, "均價": 306.42, "佔比": 2.18},
    ],
    "2408": [
        {"分點": "美林", "屬性": "外資出貨", "買賣超": -3797, "均價": 452.65, "佔比": 8.06},
        {"分點": "美商高盛", "屬性": "外資重磅提款", "買賣超": -3604, "均價": 449.41, "佔比": 7.65},
        {"分點": "摩根大通", "屬性": "外資出貨", "買賣超": -884, "均價": 449.45, "佔比": 1.88},
        {"分點": "台灣摩根士丹利", "屬性": "外資出貨", "買賣超": -779, "均價": 450.88, "佔比": 1.65},
        {"分點": "第一金-自由", "屬性": "散戶接刀", "買賣超": +2137, "均價": 451.84, "佔比": 4.54},
        {"分點": "富邦", "屬性": "短線買超", "買賣超": +1977, "均價": 457.32, "佔比": 4.20},
    ],
    "2327": [
        {"分點": "美林", "屬性": "外資出貨", "買賣超": -2669, "均價": 582.34, "佔比": 7.36},
        {"分點": "凱基", "屬性": "短空當沖", "買賣超": -2092, "均價": 580.90, "佔比": 5.76},
        {"分點": "摩根大通", "屬性": "外資出貨", "買賣超": -1337, "均價": 579.49, "佔比": 3.68},
        {"分點": "台灣摩根士丹利", "屬性": "外資出貨", "買賣超": -811, "均價": 577.80, "佔比": 2.23},
        {"分點": "新加坡商瑞銀", "屬性": "外資回補", "買賣超": +1274, "均價": 575.99, "佔比": 3.51},
    ],
    "3037": [
        {"分點": "美商高盛", "屬性": "外資重磅提款", "買賣超": -3178, "均價": 1099.36, "佔比": 21.26},
        {"分點": "台灣摩根士丹利", "屬性": "外資出貨", "買賣超": -865, "均價": 1100.91, "佔比": 5.79},
        {"分點": "統一", "屬性": "本土買盤", "買賣超": +831, "均價": 1101.42, "佔比": 5.56},
    ],
    "2344": [
        {"分點": "新加坡商瑞銀", "屬性": "外資回補", "買賣超": +3195, "均價": 162.16, "佔比": 6.74},
        {"分點": "元大", "屬性": "主力回補", "買賣超": +2585, "均價": 162.34, "佔比": 5.45},
        {"分點": "台灣摩根士丹利", "屬性": "外資回補", "買賣超": +2274, "均價": 162.48, "佔比": 4.80},
    ],
    "2313": [
        {"分點": "港商野村", "屬性": "外資大買", "買賣超": +6614, "均價": 250.32, "佔比": 13.14},
        {"分點": "美商高盛", "屬性": "外資買超", "買賣超": +2960, "均價": 248.72, "佔比": 5.88},
    ]
}

def get_latest_trade_date() -> date:
    today = date.today()
    if today.weekday() == 5:
        return today - timedelta(days=1)
    elif today.weekday() == 6:
        return today - timedelta(days=2)
    return today

# ==========================================
# 2. 數據服務：TWSE 官方 API 爬蟲
# ==========================================
class StockDataService:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

    def fetch_twse_margin(self, date_str: str) -> Dict[str, Any]:
        url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={date_str}&selectType=ALL&response=json"
        margin_dict = {}
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
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
                            "margin_balance": balance
                        }
        except Exception as e:
            st.error(f"融資抓取異常: {e}")
        return margin_dict

    def fetch_twse_institutional(self, date_str: str) -> Dict[str, Any]:
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
            st.error(f"外資抓取異常: {e}")
        return inst_dict

# ==========================================
# 3. Streamlit 網頁應用介面
# ==========================================
st.set_page_config(page_title="短空狙擊雷達 - 旗艦分析版", layout="wide")
st.title("⚡ 短空狙擊雷達：AI 評級 × 勝率演算 × 主力分點穿透")

service = StockDataService()
default_date = get_latest_trade_date()

with st.sidebar:
    st.header("⚙️ 戰情控制台")
    selected_date = st.date_input("查詢日期", value=default_date)
    date_param = selected_date.strftime("%Y%m%d")
    
    night_market_drop = st.number_input("台指夜盤跌點", value=-1144, step=-50, help="週五夜盤跌點，共振加權至空方模型")

    if st.button("🔄 刷新籌碼與重新演算"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("""
    **🎯 狙擊模型判定指標：**
    - 🔴 **多殺多引信**：融資暴增 ＋ 外資狂倒
    - ⚠️ **隔日沖踩踏**：隔日沖重鎖漲停，早盤必逃
    - 🛡️ **浮額洗淨**：融資連日大減（嚴禁放空）
    """)

@st.cache_data(ttl=300)
def load_market_data(d_str: str):
    return service.fetch_twse_margin(d_str), service.fetch_twse_institutional(d_str)

with st.spinner(f"正在同步 {date_param} 數據並執行量化勝率演算..."):
    margin_map, inst_map = load_market_data(date_param)

# ==========================================
# 4. 量化勝率演算引擎 (Win Rate Algorithm)
# ==========================================
scored_stocks = []

for code, meta in UNIVERSE.items():
    if meta["close"] == 0:
        continue
    
    m_data = margin_map.get(code, {"margin_change": 0, "margin_balance": 0})
    i_data = inst_map.get(code, {"foreign_net_sheets": 0})
    
    m_change = m_data["margin_change"]
    f_net = i_data["foreign_net_sheets"]
    
    # 基礎勝率 50%
    score = 50.0
    strategy_tag = "中立觀望"
    threshold = 0.0
    stop_loss = 0.0
    target_t1 = 0.0
    reasons = []

    # 1. 融資套牢因子 (+15% ~ -20%)
    if m_change > 1500:
        score += 18.0
        reasons.append(f"散戶融資暴增接刀 +{m_change}張 (融資大套牢)")
    elif m_change > 200:
        score += 8.0
        reasons.append(f"融資增加 +{m_change}張")
    elif m_change < -1000:
        score -= 22.0
        reasons.append(f"融資大減 {m_change}張 (浮額已洗淨，防強彈)")

    # 2. 外資提款因子 (+15% ~ -20%)
    if f_net < -3000:
        score += 16.0
        reasons.append(f"外資狂倒貨 {f_net}張 (巨量空方缺口)")
    elif f_net < -1000:
        score += 8.0
        reasons.append(f"外資賣超 {f_net}張")
    elif f_net > 5000:
        score -= 25.0
        reasons.append(f"外資大舉回補 +{f_net}張 (翻多嚴禁放空)")

    # 3. 隔日沖鎖單與分點因子
    if code == "8039":
        score += 20.0
        strategy_tag = "⚠️ 隔日沖踩踏獵殺"
        threshold = 306.0
        stop_loss = 314.0
        target_t1 = 292.0
        reasons.append("富邦/凱基台北城中等鎖單近萬張，夜盤暴跌必踩踏出貨")
    elif code == "2408":
        strategy_tag = "🚨 多殺多引信 (資增+外資倒)"
        threshold = 438.0
        stop_loss = 447.0
        target_t1 = 420.0
        reasons.append("美林/高盛大砍7400張，融資暴增3370張斷頭邊緣")
    elif code == "2327":
        strategy_tag = "📉 逆勢破底破線"
        threshold = 558.0
        stop_loss = 567.0
        target_t1 = 540.0
        reasons.append("大盤強彈時逆勢收全日最低567，外資續倒3700張")
    elif code == "3037":
        strategy_tag = "🩸 高盛重磅提款"
        threshold = 1070.0
        stop_loss = 1075.0
        target_t1 = 1055.0
        reasons.append("高盛單一分點狂倒3178張(佔比21%)")
    elif m_change < -1000:
        strategy_tag = "🛡️ 浮額沉澱 (避開)"
    elif f_net > 5000:
        strategy_tag = "⛔ 外資多方認購 (禁止放空)"

    # 4. 夜盤千點暴跌環境加權
    if night_market_drop < -800 and score > 55:
        score += 5.0

    score = min(max(round(score, 1), 15.0), 95.0)

    scored_stocks.append({
        "代號": code,
        "名稱": meta["name"],
        "收盤價": meta["close"],
        "融資增減": m_change,
        "外資買賣超": f_net,
        "短空勝率": score,
        "策略型態": strategy_tag,
        "門檻價": threshold,
        "停損價": stop_loss,
        "T1目標": target_t1,
        "核心依據": " | ".join(reasons)
    })

df_result = pd.DataFrame(scored_stocks).sort_values(by="短空勝率", ascending=False)

# ==========================================
# 5. 前端呈現：TOP 3 短空狙擊作戰卡片
# ==========================================
st.subheader("🏆 AI 量化推薦：明日最優先狙擊 TOP 3 標的")

top3 = df_result.head(3).to_dict("records")
cols = st.columns(3)

badges = ["🥇 第一首選", "🥈 第二首選", "🥉 第三首選"]
for i, col in enumerate(cols):
    item = top3[i]
    with col:
        st.markdown(f"### {badges[i]}：{item['代號']} {item['名稱']}")
        st.metric("預期短空勝率", f"{item['短空勝率']} %", delta=f"{item['策略型態']}", delta_color="inverse")
        
        st.markdown(f"""
        - **進場門檻**：`{item['門檻價']}` (右側實體跌破)
        - **防守停損**：`{item['停損價']}`
        - **獲利目標(T1)**：`{item['T1目標']}`
        - **籌碼面**：融資 `{item['融資增減']:+d}` 張 ｜ 外資 `{item['外資買賣超']:+d}` 張
        """)
        st.caption(f"**作戰核心**：{item['核心依據']}")

st.divider()

# ==========================================
# 6. 母池 12 檔全覽與勝率排行總表
# ==========================================
st.subheader("📋 12 檔母池量化空方勝率與策略清單")
st.dataframe(
    df_result[["代號", "名稱", "收盤價", "短空勝率", "策略型態", "融資增減", "外資買賣超", "門檻價", "停損價", "T1目標"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "短空勝率": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
        "融資增減": st.column_config.NumberColumn(format="%+d"),
        "外資買賣超": st.column_config.NumberColumn(format="%+d"),
        "收盤價": st.column_config.NumberColumn(format="%.1f"),
        "門檻價": st.column_config.NumberColumn(format="%.1f"),
        "停損價": st.column_config.NumberColumn(format="%.1f"),
        "T1目標": st.column_config.NumberColumn(format="%.1f"),
    }
)

st.divider()

# ==========================================
# 7. 30 家短空分點穿透檢視面板
# ==========================================
st.subheader("🔍 30 家短空分點明細穿透檢視")
selected_target = st.selectbox(
    "選擇要檢視主力分點進出的股票：",
    options=list(UNIVERSE.keys()),
    format_func=lambda x: f"{x} {UNIVERSE[x]['name']} (勝率: {df_result.loc[df_result['代號']==x, '短空勝率'].values[0]}%)"
)

broker_data = CHIP_DETAIL_DATABASE.get(selected_target, [])

if broker_data:
    st.markdown(f"#### 📊 {selected_target} {UNIVERSE[selected_target]['name']} 主力分點進出明細")
    df_broker = pd.DataFrame(broker_data)
    
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.dataframe(
            df_broker,
            use_container_width=True,
            hide_index=True,
            column_config={
                "買賣超": st.column_config.NumberColumn(format="%+d"),
                "均價": st.column_config.NumberColumn(format="%.2f"),
                "佔比": st.column_config.NumberColumn(format="%.2f%%"),
            }
        )
    with col_r:
        if selected_target == "8039":
            st.error("⚠️ **隔日沖踩踏警示**\n富邦(+3493)、凱基城中(+1548)、凱基台北(+1159)、國票敦北(+691) 等鎖單逾 9,700 張全屬隔日沖大本營。週一開盤將引爆近 5.16 億元獲利逃命賣壓！")
        elif selected_target == "2408":
            st.error("🚨 **融資斷頭引信警示**\n散戶逆勢大接刀暴增 +3,370 張融資，美林與美商高盛聯手狂倒逾 7,400 張！開盤一旦摜破 443.5 將引爆連環斷頭多殺多。")
        elif selected_target == "2327":
            st.warning("📉 **弱勢破底警示**\n美林(-2669)、凱基(-2092)、大摩(-1337) 連續重砍，收在當日最低 567，破線向下無支撐。")
        elif selected_target == "2344":
            st.success("🟢 **主力強回補**\n瑞銀(+3195)、元大(+2585)、大摩(+2274) 大買超，融資清洗，禁止逆勢做空！")
else:
    st.info("此標的目前無顯著的前十大集中分點異動，或處於橫盤整理。")
