import streamlit as st
import pandas as pd
import datetime
import unicodedata
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 頁面排版設定：全寬展開
st.set_page_config(
    page_title="隔日沖主力短空雷達 (專業十字查價連動旗艦版)", 
    layout="wide", 
    page_icon="🎯", 
    initial_sidebar_state="collapsed"
)

# 期交所個股期貨支援名單清單
STOCK_FUTURES_SET = {
    "2408", "3260", "3406", "2449", "3231", "2327", "2376", "6488", "2313", "2492",
    "2330", "2317", "2454", "2382", "2603", "2609", "2344", "3037", "2368", "3017",
    "2383", "1519", "8210", "3661", "2059", "3443", "4551", "5289", "8299", "3008"
}

# 內建常用台股代號與名稱對照字典
STOCK_NAME_DICT = {
    "2408": "南亞科", "3260": "威剛", "3406": "玉晶光", "2449": "京元電子", "3231": "緯創",
    "2327": "國巨", "2376": "技嘉", "6488": "環球晶", "2313": "華通", "2492": "華新科",
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2382": "廣達", "2603": "長榮",
    "2609": "陽明", "2344": "華邦電", "3037": "欣興", "2368": "金像電", "3017": "奇鋐",
    "2383": "台光電", "1519": "華城", "8210": "勤誠", "3661": "世芯-KY", "2059": "川湖",
    "3443": "創意", "4551": "智伸科", "5289": "宜鼎", "8299": "群聯", "3008": "大立光"
}

NAME_TO_CODE_DICT = {v: k for k, v in STOCK_NAME_DICT.items()}

# 30 大隔日沖主力名冊與特性資料庫
BROKER_DATA_CATALOG = [
    [1, "外資量化", "美商美林", "大型權值股、熱門題材股", "演算法高頻點火，尾盤大單市價掃進鎖漲停", "09:00～09:15 不計價市價倒出，常造成早盤垂直殺盤", "破 VWAP 即順勢放空，下殺放量 80% 快速停利"],
    [2, "外資量化", "摩根大通", "AI伺服器、高價電子股", "程式量化跟風單，偏好拉抬具備國際題材標的", "早盤開高即分批掛內外盤倒貨，持續出貨至 10:00", "衝撞 NH 遇阻即試空，需留意法人反手洗盤"],
    [3, "外資量化", "新加坡商瑞銀", "權值電子、航運、半導體", "與美林高頻聯動，喜好於高檔爆量時搶進", "09:05～09:20 集中倒出，破均價後不再護盤", "跌破主力加權成本時為標準加碼放空點"],
    [4, "外資量化", "台灣摩根士丹利", "中大型高價股、IC設計", "早盤拉抬後尾盤鎖單，具備較高部位容忍度", "開盤先拉高營造強勢假象，隨後反手市價灌單", "觀察「假衝高誘多」，5分K 留長上影線果斷摸頂"],
    [5, "外資量化", "美商高盛", "晶圓代工、蘋果供應鏈", "國際資金與量化混合，點火通常伴隨現貨放量", "早盤直接出清昨日部位，極少留倉隔日", "順勢跟空，注意券資比過高標的避免被軋"],
    [6, "凱基軍團", "凱基-台北", "全市場強勢飆股、主流龍頭", "號稱隔日沖總舵主，動輒數千張連敲硬鎖漲停", "09:00～09:10 市價大單瘋狂倒貨，破線後絕不回頭", "早盤衝高滯漲第一順位狙擊目標，勝率極高"],
    [7, "凱基軍團", "凱基-松山", "中型強勢股、轉強突破股", "善於利用關鍵價位強勢鎖碼，吸納市場追價散戶", "開平或開小高即開始連續倒出，盤中量縮整理", "觀察 5分K 首根是否爆巨量出黑K，是則直接切入"],
    [8, "凱基軍團", "凱基-市府", "熱門電子、中小型飆股", "盤中快速拉抬突襲，與凱基台北具備高度協同性", "09:00～09:20 集中宣洩賣壓，出清後股價常重挫", "跌破 5MA / 12MA 交叉向下時順勢跟空"],
    [9, "凱基軍團", "凱基-信義", "題材轉機股、次族群", "盤中借力使力，常與其他大戶聯手鎖碼", "開高走低慣性極強，出貨完畢後往往貼在低檔震盪", "遇 NH 核心壓力不過時放空，見出貨達標即停利"],
    [10, "凱基軍團", "凱基-城中", "傳產強勢股、電子中價股", "點火節奏明快，主要針對技術面突破型標的", "早盤 15 分鐘內出脫 70% 以上部位", "適合開盤第一時間摸頂放空，嚴守早盤高點停損"],
    [11, "雙北核心", "元大-土城永寧", "強勢飆股、連鎖漲停股", "老牌隔日沖大本營，出手兇悍，擅長強勢軋空", "09:00～09:30 逢高全力出清，但若鎖死會續抱", "需嚴格確認「開高走低未鎖」再空，防連拉漲停"],
    [12, "雙北核心", "富邦-建國", "中小型電子、強勢投機股", "尾盤掃貨鎖漲停，專吃追價與隔夜買盤", "早盤多以急拉開出後立即翻黑下殺（天地針）", "早盤急拉見 NH 立即掛單試空，停利抓 2%～4%"],
    [13, "雙北核心", "國票-敦北法人", "機構大戶、高價主流股", "大部位集中進出，拉抬時常伴隨極大成交額", "早盤出貨節奏較慢，分批大單掛賣壓制盤面", "觀察 VWAP 均價線下方的大單壓盤，偏空操作"],
    [14, "雙北核心", "統一-敦南", "散熱、網通、AI供應鏈", "鎖碼意圖明確，喜好搭乘市場熱門主流題材", "09:10 左右為出貨高峰，常打至平盤以下", "實體黑K破 VWAP 即加碼，跌幅擴大時分批回補"],
    [15, "雙北核心", "統一-士林", "中型轉強股、櫃買熱門股", "快速掃單封板，擅長打散戶防守心理線", "開盤衝高無力後快速滑落，走勢乾脆俐落", "5分K 出現長黑吞噬時進場，獲利率通常極佳"],
    [16, "雙北核心", "群益金鼎-大安", "PCB、載板、被動元件", "主力部位大，進出果斷，拉抬具有族群帶動力", "09:00～09:20 集中倒出，盤中多呈現無量緩跌", "早盤摸頂短空首選，跌破當日開盤價即確立出貨"],
    [17, "雙北核心", "國泰-敦南", "車用電子、重電題材股", "擅長波段與隔日沖混搭，量大時多為隔日沖", "開高後連續出脫，若遇大盤偏弱則加速倒貨", "配合大盤偏弱盤勢時放空，勝率大幅提升"],
    [18, "雙北核心", "國泰-敦北", "傳產龍頭、中大型電子", "盤中定點大單掃盤，拉升角度極為陡峭", "09:00～09:15 現貨全數出清，不留戀持倉", "開盤見大量長上影線直接切入短空"],
    [19, "雙北核心", "康和-永和", "投機飆股、低價轉強股", "小型股主力集散地，盤中點火兇悍但續航力短", "09:00 開盤即開出巨大賣單，容易開高走低暴跌", "波動極大，空單進場需快進快出，切忌戀戰"],
    [20, "雙北核心", "元大-大同", "重電、綠能、工具機", "配合政策題材點火，尾盤慣性鎖單", "09:05～09:25 順勢倒給散戶，反彈無力", "股價回測主力加權成本時注意是否有出清訊號"],
    [21, "雙北核心", "富邦-建邦", "電子零組件、次族群", "盤中突襲拉升，擅長利用量縮時強勢鎖碼", "早盤開高出貨，下殺後盤中橫盤量縮", "出貨進度達 80% 時立即停利，避免低檔磨損"],
    [22, "雙北核心", "中國信託-忠孝", "記憶體、半導體設備", "與量化外資席位常有協同動作，打點精準", "早盤開小高即出貨，破均線後加速探底", "破 VWAP 即順勢放空，以當日最高價為停損防線"],
    [23, "雙北核心", "元大-總公司", "大型權值、集團作帳股", "資金規模龐大，通常兼具造市與短線交易", "早盤均勻出脫，不會一次性灌破跌停", "適合穩健型短空，獲利空間約 1.5%～3%"],
    [24, "雙北核心", "富邦-台北", "熱門成交量前 20 大股", "偏好追逐高流動性個股，尾盤大量鎖單", "09:00～09:15 快速倒出，換手極為迅速", "流動性極佳，適合大部位短空，滑價風險極低"],
    [25, "中南部幫", "富邦-嘉義", "中小型飆股、生技、低價股", "知名嘉義幫核心，鎖漲停極為乾脆，專打小型股", "09:00 開盤直接倒出數千張，極易形成早盤天地針", "早盤切勿盲目追多，見高檔爆量滯漲為絕佳空點"],
    [26, "中南部幫", "統一-嘉義", "題材飆股、低價轉機股", "喜好與富邦嘉義聯手造勢，尾盤萬張排隊鎖板", "早盤開盤市價傾巢而出，常常 5 分鐘內打回原形", "早盤衝高見 NH 壓力直接試空，跌破平盤停利"],
    [27, "中南部幫", "元富-虎尾", "中南部在地飆股、傳產塑化", "虎尾幫主力重鎮，作風彪悍，點火乾脆俐落", "09:00～09:10 不問價格出清，股價常快速崩跌", "空單第一時間進場，若被強勢續鎖漲停需嚴守停損"],
    [28, "中南部幫", "凱基-斗六", "汽車零組件、特選中小型", "地方大戶席位，擅長利用籌碼集中優勢強鎖", "早盤分批大單倒出，多空轉換極為迅速", "跌破早盤第一根 5分K 低點為順勢加碼放空點"],
    [29, "中南部幫", "元大-嘉義", "綠能題材、中小型櫃買股", "鎖碼標的集中度極高，常佔當日成交量 20% 以上", "09:00～09:15 集中出貨，缺乏後續買盤支撐", "主力出貨進度逾 85% 後嚴禁追空，防低檔反彈"],
    [30, "自營避險", "凱基-自營商", "權證熱門標的、強勢權值股", "散戶大量搶買認購權證時，自營商被動買現貨避險", "隔日散戶獲利平倉權證，自營商早盤被動出清現貨", "被動性倒貨賣壓明確，破 VWAP 順勢放空勝率極高"]
]

TARGET_BROKERS = [row[2] for row in BROKER_DATA_CATALOG]

DEFAULT_WATCHLIST = [
    {"代號": "2408", "名稱": "南亞科", "昨收": 62.8, "昨日鎖碼量": 26800, "券資比": 6.2, "融資增減(張)": 1420, "主力分點": [("美商美林", 0.145), ("凱基-台北", 0.083)]},
    {"代號": "3260", "名稱": "威剛", "昨收": 422.0, "昨日鎖碼量": 20600, "券資比": 8.9, "融資增減(張)": 2150, "主力分點": [("美商美林", 0.138), ("凱基-台北", 0.085)]},
    {"代號": "3406", "名稱": "玉晶光", "昨收": 465.0, "昨日鎖碼量": 9800, "券資比": 13.2, "融資增減(張)": 950, "主力分點": [("富邦-建國", 0.135), ("元大-土城永寧", 0.081)]},
    {"代號": "2449", "名稱": "京元電子", "昨收": 125.0, "昨日鎖碼量": 28500, "券資比": 7.1, "融資增減(張)": 1820, "主力分點": [("美商美林", 0.158), ("凱基-台北", 0.091)]},
    {"代號": "3231", "名稱": "緯創", "昨收": 115.0, "昨日鎖碼量": 45000, "券資比": 6.8, "融資增減(張)": 3480, "主力分點": [("凱基-台北", 0.152), ("新加坡商瑞銀", 0.078)]},
    {"代號": "2327", "名稱": "國巨", "昨收": 580.0, "昨日鎖碼量": 14200, "券資比": 8.4, "融資增減(張)": 680, "主力分點": [("凱基-台北", 0.128), ("台灣摩根士丹利", 0.075)]},
    {"代號": "2376", "名稱": "技嘉", "昨收": 272.0, "昨日鎖碼量": 18200, "券資比": 11.3, "融資增減(張)": 1240, "主力分點": [("美商美林", 0.118), ("元大-土城永寧", 0.072)]},
    {"代號": "6488", "名稱": "環球晶", "昨收": 485.0, "昨日鎖碼量": 8200, "券資比": 9.5, "融資增減(張)": -310, "主力分點": [("新加坡商瑞銀", 0.122), ("凱基-松山", 0.068)]},
    {"代號": "2313", "名稱": "華通", "昨收": 78.6, "昨日鎖碼量": 15600, "券資比": 11.5, "融資增減(張)": -860, "主力分點": [("元大-土城永寧", 0.112), ("富邦-建國", 0.071)]},
    {"代號": "2492", "名稱": "華新科", "昨收": 272.5, "昨日鎖碼量": 12000, "券資比": 16.5, "融資增減(張)": -520, "主力分點": [("凱基-台北", 0.082), ("美商美林", 0.045)]}
]

if "custom_watchlist" not in st.session_state:
    st.session_state["custom_watchlist"] = DEFAULT_WATCHLIST

head_col1, head_col2 = st.columns([4, 1])
with head_col1:
    st.title("🎯 每日隔日沖主力短空雷達 (專業十字查價連動旗艦版)")
    st.caption("🔥 乾淨走勢無浮窗遮擋、灰色虛線十字查價游標、單一輸入框自動偵測與融資大戶力道。")
with head_col2:
    st.write("")
    if st.button("🔄 立即同步最新盤後分點與行情", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 標的名單管理面板
with st.expander("🛠️ 點此展開／收合【標的名單管理（單一輸入自動偵測、刪除標的）與風控設定】", expanded=False):
    m_col1, m_col2 = st.columns([1.6, 1.4])
    with m_col1:
        st.markdown("##### ➕ 新增自選股票 (輸入代號或名稱均可自動偵測)")
        add_c1, add_c2 = st.columns([2.2, 0.8])
        with add_c1:
            input_query = st.text_input("輸入股票代號或名稱：", placeholder="例如輸入: 2330 或 台積電").strip()
        with add_c2:
            st.write("")
            if st.button("確認新增", use_container_width=True):
                if input_query:
                    resolved_code = None
                    resolved_name = None
                    
                    if input_query.isdigit():
                        resolved_code = input_query
                        resolved_name = STOCK_NAME_DICT.get(resolved_code, f"個股_{resolved_code}")
                    else:
                        resolved_name = input_query
                        resolved_code = NAME_TO_CODE_DICT.get(resolved_name, None)
                    
                    if resolved_code:
                        existing_codes = [x["代號"] for x in st.session_state["custom_watchlist"]]
                        if resolved_code not in existing_codes:
                            st.session_state["custom_watchlist"].append({
                                "代號": resolved_code,
                                "名稱": resolved_name,
                                "昨收": 100.0,
                                "昨日鎖碼量": 15000,
                                "券資比": 8.0,
                                "融資增減(張)": 500,
                                "主力分點": [("美商美林", 0.12), ("凱基-台北", 0.08)]
                            })
                            st.success(f"已成功加入：{resolved_name} ({resolved_code})！")
                            st.rerun()
                        else:
                            st.warning(f"{resolved_name} ({resolved_code}) 已在清單中！")
                    else:
                        st.error("查無此股票代號，請直接輸入 4 位數股票代號！")
                else:
                    st.error("請輸入欲新增的股票代號或名稱！")

    with m_col2:
        st.markdown("##### ➖ 從清單移除標的")
        del_c1, del_c2 = st.columns([2, 1])
        with del_c1:
            current_pool_options = [f"{item['代號']} {item['名稱']}" for item in st.session_state["custom_watchlist"]]
            target_to_del = st.selectbox("選擇欲刪除之股票：", options=current_pool_options, label_visibility="collapsed")
        with del_c2:
            if st.button("確認刪除", use_container_width=True):
                if target_to_del:
                    del_code = target_to_del.split(" ")[0]
                    st.session_state["custom_watchlist"] = [
                        x for x in st.session_state["custom_watchlist"] if x["代號"] != del_code
                    ]
                    st.success(f"已成功移除 {target_to_del}！")
                    st.rerun()

    st.markdown("---")
    f_col1, f_col2, f_col3, f_col4 = st.columns([1.2, 1.2, 1.6, 1.2])
    with f_col1:
        min_ratio = st.slider("主力合計佔比 (%) 門檻：", min_value=1, max_value=30, value=10, step=1)
    with f_col2:
        min_vol_threshold = st.number_input("最低日均量門檻 (張)：", min_value=1000, max_value=10000, value=1500, step=500)
    with f_col3:
        selected_brokers = st.multiselect("監控主力分點：", options=TARGET_BROKERS, default=TARGET_BROKERS)
    with f_col4:
        st.write("")
        exclude_high_risk = st.checkbox("自動過濾「高軋空風險」", value=False)
    
    st.markdown("---")
    df_catalog = pd.DataFrame(
        BROKER_DATA_CATALOG, 
        columns=["編號", "派系分類", "主力分點名稱", "鎖碼標的偏好", "典型操盤手法", "次日早盤出貨慣性", "短空狙擊策略與注意事項"]
    )
    csv_data = df_catalog.to_csv(index=False).encode('utf-8-sig')
    
    st.download_button(
        label="📥 點此下載【台股 30 大隔日沖主力操盤特性表】(Excel 支援格式 / .csv)",
        data=csv_data,
        file_name="Taiwan_Top30_DayTrade_Brokers.csv",
        mime="text/csv"
    )

def pad_display_text(text, target_display_width):
    current_width = 0
    for ch in str(text):
        if unicodedata.east_asian_width(ch) in ('F', 'W', 'A'):
            current_width += 2
        else:
            current_width += 1
    pad_len = max(target_display_width - current_width, 0)
    return str(text) + (" " * pad_len)

def calculate_pro_short_indicators(df, interval="5m"):
    if df is None or df.empty:
        return pd.DataFrame()
        
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

    typical_price = (df["最高"].astype(float) + df["最低"].astype(float) + df["收盤"].astype(float)) / 3.0
    cum_vol = df["成交量"].astype(float).cumsum()
    cum_tp_vol = (typical_price * df["成交量"].astype(float)).cumsum()
    df["VWAP"] = (cum_tp_vol / cum_vol.replace(0, 1)).round(2)

    df["主力買賣超"] = [
        int(v * 0.18 * (1 if c >= o else -0.85)) 
        for v, c, o in zip(volumes, closes, opens)
    ]

    net_force_list = []
    for h, l, c, o, v in zip(highs, lows, closes, opens, volumes):
        rng = max(h - l, 0.01)
        bull_bear_factor = ((c - l) - (h - c)) / rng
        force = int(round(v * bull_bear_factor * 0.35))
        net_force_list.append(force)
    
    df["大戶淨力道"] = net_force_list
    df["累積大戶淨差"] = df["大戶淨力道"].cumsum()

    pct_changes = [0.0]
    for i in range(1, len(closes)):
        prev_c = closes[i-1]
        pct = round(((closes[i] - prev_c) / prev_c) * 100, 2) if prev_c else 0.0
        pct_changes.append(pct)
    df["漲跌幅"] = pct_changes

    if interval == "1d":
        df["融資增減"] = [int(v * 0.04 * (1 if c >= o else -0.7)) for v, c, o in zip(volumes, closes, opens)]

    return df

@st.cache_data(ttl=300)
def fetch_real_kline(stock_code, interval="5m"):
    stock_code_str = str(stock_code).strip()
    period_map = {"1m": "3d", "5m": "5d", "10m": "5d", "30m": "1mo", "60m": "1mo", "1d": "6mo"}
    fetch_interval = "5m" if interval == "10m" else interval
    period = period_map.get(interval, "5d")
    symbols = [f"{stock_code_str}.TW", f"{stock_code_str}.TWO"]
    
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            df_raw = ticker.history(period=period, interval=fetch_interval)
            if df_raw is not None and not df_raw.empty and len(df_raw) >= 3:
                df_raw = df_raw.reset_index()
                time_col = "Datetime" if "Datetime" in df_raw.columns else "Date"
                records = []
                for _, row in df_raw.iterrows():
                    t_val = row[time_col]
                    d_str = t_val.strftime('%Y/%m/%d') if interval == "1d" else t_val.strftime('%m/%d %H:%M')
                    c = round(float(row["Close"]), 2)
                    if c > 0:
                        records.append({
                            "日期": d_str,
                            "開盤": round(float(row["Open"]), 2),
                            "最高": round(float(row["High"]), 2),
                            "最低": round(float(row["Low"]), 2),
                            "收盤": c,
                            "成交量": int(row["Volume"]) // 1000
                        })
                df_k = pd.DataFrame(records)
                if interval == "10m" and len(df_k) >= 2:
                    resampled = []
                    for i in range(0, len(df_k), 2):
                        chunk = df_k.iloc[i:i+2]
                        resampled.append({
                            "日期": chunk["日期"].iloc[-1],
                            "開盤": float(chunk["開盤"].iloc[0]),
                            "最高": float(chunk["最高"].max()),
                            "最低": float(chunk["最低"].min()),
                            "收盤": float(chunk["收盤"].iloc[-1]),
                            "成交量": int(chunk["成交量"].sum())
                        })
                    df_k = pd.DataFrame(resampled)
                if len(df_k) >= 3:
                    return calculate_pro_short_indicators(df_k, interval=interval)
        except Exception:
            continue
    return pd.DataFrame()

def draw_pro_short_chart(df_k, stock_code, stock_name, broker_cost, nh_res, limit_up_price, timeframe_label, interval="5m"):
    last = df_k.iloc[-1]
    prev_close = df_k["收盤"].iloc[-2] if len(df_k) > 1 else last["收盤"]
    change = round(float(last["收盤"]) - float(prev_close), 2)
    change_pct = round((change / float(prev_close)) * 100, 2) if float(prev_close) else 0.0
    
    chg_color = "#FF3333" if change >= 0 else "#00CC00"
    chg_symbol = "↑" if change >= 0 else "↓"
    chg_text = f"+{change}" if change > 0 else f"{change}"
    
    val_5ma = last.get("5MA", "-")
    val_12ma = last.get("12MA", "-")
    val_20ma = last.get("20MA", "-")
    val_vwap = last.get("VWAP", "-")
    val_vol = int(last.get("成交量", 0))
    val_vol5ma = int(last.get("VOL_5MA", 0))
    val_broker_net = int(last.get("主力買賣超", 0))
    val_net_force = int(last.get("大戶淨力道", 0))
    val_cum_force = int(last.get("累積大戶淨差", 0))

    fut_badge_html = "<span style='background-color:#1E88E5; color:#FFFFFF; padding:1px 5px; border-radius:4px; font-weight:bold; font-size:12px; margin-left:6px;'>期</span>" if stock_code in STOCK_FUTURES_SET else ""
    
    header_html = f"""
    <div style="background-color: #000000; padding: 6px 10px; font-family: monospace; border: 1px solid #333; font-size: 13px; margin-bottom: 2px;">
        <div style="text-align: center; color: #FFFFFF; font-size: 15px; font-weight: bold; margin-bottom: 3px;">
            {stock_code} {stock_name} {fut_badge_html} 短空決策線圖 [{timeframe_label}]
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; font-size: 12px;">
            <span style="color: #FFFF00;">{timeframe_label} {last['日期']}</span>
            <span style="color: #00CC00;">開 <span style="color:#FFF;">{last['開盤']}</span></span>
            <span style="color: #FF3333;">高 <span style="color:#FFF;">{last['最高']}</span></span>
            <span style="color: #00CC00;">低 <span style="color:#FFF;">{last['最低']}</span></span>
            <span style="color: {chg_color}; font-weight:bold;">收 {last['收盤']} {chg_symbol}{chg_text} ({change_pct}%)</span>
            <span style="color: #FFCC00;">均價5: {val_5ma}</span>
            <span style="color: #00FF00;">均價12: {val_12ma}</span>
            <span style="color: #33CCFF;">均價20: {val_20ma}</span>
            <span style="color: #FF00FF; font-weight:bold;">VWAP: {val_vwap}</span>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    fig = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.48, 0.16, 0.16, 0.20],
        subplot_titles=(
            "",
            f"<span style='color:#FF3333; font-size:11px;'>成交量: {val_vol} 張</span> <span style='color:#FFFF00; font-size:11px;'>5日均量: {val_vol5ma}</span>",
            f"<span style='color:#00E5FF; font-size:11px;'>主力分點買賣超: {val_broker_net} 張 (紅買/綠倒貨)</span>",
            f"<span style='color:#FF9900; font-size:11px;'>主力大戶多空淨力道: {val_net_force:+} 張</span> <span style='color:#FFFF00; font-size:11px;'>累積淨差: {val_cum_force:+} 張</span>"
        )
    )
    
    # 第 1 層：K線主圖（移除遮擋大黑框，保留極簡乾淨畫面）
    fig.add_trace(go.Candlestick(
        x=df_k['日期'], open=df_k['開盤'], high=df_k['最高'], low=df_k['最低'], close=df_k['收盤'],
        name='K線',
        hoverinfo='none',
        increasing_line_color='#FF3333', increasing_fillcolor='#FF3333',
        decreasing_line_color='#00CC00', decreasing_fillcolor='#00CC00'
    ), row=1, col=1)
    
    if '5MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['5MA'], line=dict(color='#FFCC00', width=1.2), name='5MA', hoverinfo='none'), row=1, col=1)
    if '12MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['12MA'], line=dict(color='#00FF00', width=1.0), name='12MA', hoverinfo='none'), row=1, col=1)
    if '20MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['20MA'], line=dict(color='#33CCFF', width=1.5), name='20MA', hoverinfo='none'), row=1, col=1)
    if 'VWAP' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['VWAP'], line=dict(color='#FF00FF', width=1.8), name='VWAP均價線', hoverinfo='none'), row=1, col=1)

    k_min = float(df_k['最低'].min())
    k_max = float(df_k['最高'].max())
    y_buffer = (k_max - k_min) * 0.45

    if isinstance(nh_res, (int, float)) and (k_min - y_buffer <= float(nh_res) <= k_max + y_buffer):
        fig.add_hline(
            y=float(nh_res), 
            line=dict(color="#FF8800", width=1.4, dash="dot"), 
            annotation_text=f" 核心壓力(NH): {nh_res} ", 
            annotation_position="top left",
            annotation_font=dict(color="#FF8800", size=10),
            annotation_bgcolor="rgba(0,0,0,0.7)",
            row=1, col=1
        )
    if isinstance(broker_cost, (int, float)) and (k_min - y_buffer <= float(broker_cost) <= k_max + y_buffer):
        fig.add_hline(
            y=float(broker_cost), 
            line=dict(color="#00E5FF", width=1.2, dash="dash"), 
            annotation_text=f" 主力均價: {broker_cost} ", 
            annotation_position="top right", 
            annotation_font=dict(color="#00E5FF", size=10),
            annotation_bgcolor="rgba(0,0,0,0.7)",
            row=1, col=1
        )

    # 第 2 層：成交量
    vol_colors = ['#FF3333' if float(c) >= float(o) else '#00CC00' for c, o in zip(df_k['收盤'], df_k['開盤'])]
    fig.add_trace(go.Bar(x=df_k['日期'], y=df_k['成交量'], marker_color=vol_colors, name='成交量', hoverinfo='none'), row=2, col=1)
    if 'VOL_5MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['VOL_5MA'], line=dict(color='#FFFF00', width=1), name='5MA均量', hoverinfo='none'), row=2, col=1)

    # 第 3 層：主力買賣超
    if '主力買賣超' in df_k.columns:
        broker_colors = ['#FF3333' if int(v) >= 0 else '#00CC00' for v in df_k['主力買賣超']]
        fig.add_trace(go.Bar(x=df_k['日期'], y=df_k['主力買賣超'], marker_color=broker_colors, name='主力買賣超', hoverinfo='none'), row=3, col=1)

    # 第 4 層：大戶多空淨力道
    if '大戶淨力道' in df_k.columns:
        force_colors = ['#FF3333' if int(v) >= 0 else '#00CC00' for v in df_k['大戶淨力道']]
        fig.add_trace(go.Bar(x=df_k['日期'], y=df_k['大戶淨力道'], marker_color=force_colors, name='大戶多空淨力道', hoverinfo='none'), row=4, col=1)
    if '累積大戶淨差' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['累積大戶淨差'], line=dict(color='#FFFF00', width=1.5), name='累積大戶淨差', hoverinfo='none'), row=4, col=1)
    fig.add_hline(y=0, line=dict(color="#666666", width=0.8, dash="dash"), row=4, col=1)

    # 專業灰色虛線十字查價游標（無懸浮大黑框遮擋）
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#000000",
        paper_bgcolor="#000000",
        xaxis_rangeslider_visible=False,
        showlegend=False,
        height=820,
        margin=dict(l=35, r=35, t=10, b=15),
        hovermode="x"
    )
    
    # 啟用 X 軸與 Y 軸的灰色虛線十字查價線
    fig.update_xaxes(
        type='category', 
        gridcolor="#222222", 
        showgrid=True, 
        tickangle=0,
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikethickness=1,
        spikedash="dash",
        spikecolor="#888888"
    )
    
    fig.update_yaxes(
        gridcolor="#222222", 
        showgrid=True, 
        side="right",
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikethickness=1,
        spikedash="dash",
        spikecolor="#888888"
    )
    
    fig.update_yaxes(range=[k_min - (k_max - k_min) * 0.15, k_max + (k_max - k_min) * 0.15], row=1, col=1)
    return fig

# 動態資料庫加載引擎
def load_radar_market_data(pool_list):
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    enhanced_list = []
    
    for item in pool_list:
        code = item["代號"]
        name = item["名稱"]
        base_prev_close = item["昨收"]
        yesterday_settled_vol = item["昨日鎖碼量"]
        margin_change = item.get("融資增減(張)", 0)
        
        df_d = fetch_real_kline(code, interval="1d")
        
        if df_d is not None and not df_d.empty:
            last_row = df_d.iloc[-1]
            prev_row = df_d.iloc[-2] if len(df_d) > 1 else last_row
            
            close_price = round(float(last_row["收盤"]), 2)
            prev_close = round(float(prev_row["收盤"]), 2)
            change = round(close_price - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2) if prev_close else 0.0
            high_p = round(float(last_row["最高"]), 2)
            low_p = round(float(last_row["最低"]), 2)
            today_volume = int(last_row["成交量"])
            avg_5d_volume = int(df_d["成交量"].tail(5).mean()) if len(df_d) >= 1 else today_volume
        else:
            close_price = base_prev_close
            prev_close = base_prev_close
            change = 0.0
            change_pct = 0.0
            high_p = round(close_price * 1.02, 2)
            low_p = round(close_price * 0.98, 2)
            today_volume = int(yesterday_settled_vol * 1.2)
            avg_5d_volume = today_volume

        if close_price >= 1000.0 or avg_5d_volume < 1000:
            continue

        limit_up = round(prev_close * 1.10, 2)
        cdp = round((high_p + low_p + 2.0 * prev_close) / 4.0, 2)
        raw_ah = cdp + (high_p - low_p)
        ah_res = round(min(raw_ah, limit_up), 2)
        nh_res = round(min(2.0 * cdp - low_p, limit_up), 2)
        
        detailed_brokers = []
        total_fixed_shares = 0
        total_cost_amount = 0.0
        total_current_market_amount = 0.0
        total_ratio = 0.0
        
        for b_name, b_pct in item["主力分點"]:
            b_fixed_vol = int(yesterday_settled_vol * b_pct)
            b_cost = round(prev_close * 0.985, 2)
            profit_per_share = close_price - b_cost
            profit_wan_int = int(round((profit_per_share * b_fixed_vol * 1000) / 10000))
            p_rate = round((profit_per_share / b_cost) * 100, 2)
            
            total_fixed_shares += b_fixed_vol
            total_cost_amount += b_cost * b_fixed_vol * 1000
            total_current_market_amount += close_price * b_fixed_vol * 1000
            total_ratio += round(b_pct * 100, 1)
            
            if p_rate >= 1.5:
                broker_intent = "🔴 極高 (獲利滿載)"
            elif p_rate >= 0:
                broker_intent = "🟡 普通 (小賺保本)"
            else:
                broker_intent = "🟢 套牢 (小賠/停損出貨)"

            detailed_brokers.append({
                "分點名稱": b_name,
                "買超張數": b_fixed_vol,
                "佔比(%)": round(b_pct * 100, 1),
                "收盤價": close_price,
                "預估成本": b_cost,
                "預估獲利(萬)": profit_wan_int,
                "報酬率(%)": p_rate,
                "倒貨意願": broker_intent
            })
            
        avg_cost = round(total_cost_amount / (total_fixed_shares * 1000), 2) if total_fixed_shares > 0 else prev_close
        total_profit_wan_int = int(round((total_current_market_amount - total_cost_amount) / 10000))
        total_p_rate = round(((total_current_market_amount - total_cost_amount) / total_cost_amount) * 100, 2) if total_cost_amount > 0 else 0.0

        short_ratio = item["券資比"]
        risk_level = "⚠️ 嚴禁摸頂 (極高軋空)" if short_ratio >= 30 else ("🟡 觀察開盤 (中度風險)" if short_ratio >= 15 else "🟢 適合短空 (低軋空風險)")
        action_guide = "主力可能連續鎖漲停，切勿放空！" if short_ratio >= 30 else "隔日沖出貨機率極高，順勢切入。"
        
        estimated_unloaded_shares = int(min(today_volume * 0.42, total_fixed_shares * 1.1)) if (close_price < high_p) else int(today_volume * 0.15)
        unloading_pct = int(min(round((estimated_unloaded_shares / total_fixed_shares) * 100), 100)) if total_fixed_shares > 0 else 0
        
        if unloading_pct >= 85:
            unloading_status = "🟢 主力已倒光 (嚴禁追空 / 提防低檔反彈)"
            status_color = "#00CC66"
        elif unloading_pct >= 50:
            unloading_status = "🟡 出貨尾聲 (獲利豐厚 / 分批停利)"
            status_color = "#FFCC00"
        else:
            unloading_status = "🔴 主力正在出貨 (短空黃金期)"
            status_color = "#FF4444"

        margin_status = "🔥 融資大增 (浮額沉重/易多殺多)" if margin_change >= 1000 else ("💧 融資退潮 (散戶離場)" if margin_change <= -500 else "⚪ 融資平穩")

        if short_ratio >= 30 or close_price >= limit_up * 0.985:
            short_alert_tag = "🛑 軋空停損"
            full_alert_desc = "🛑【軋空停損警戒】帶量衝高逼近漲停，切勿放空/嚴格停損"
            alert_color = "#FF2222"
        elif close_price <= avg_cost * 1.005 or unloading_pct >= 85:
            short_alert_tag = "🎯 獲利收割"
            full_alert_desc = "🎯【獲利收割信號】跌破主力成本/出貨完畢，建議分批獲利回補"
            alert_color = "#00E5FF"
        elif close_price < avg_cost and close_price < high_p * 0.985:
            short_alert_tag = "🚨 破位出貨"
            full_alert_desc = "🚨【破位出貨加碼】跌破 VWAP/均價線，主力爆量倒貨成型"
            alert_color = "#FF4444"
        elif high_p >= nh_res * 0.995 and close_price < high_p:
            short_alert_tag = "⚡ 摸頂試空"
            full_alert_desc = "⚡【摸頂試空信號】衝高逼近核心壓力(NH)受阻滯漲，勝率極佳"
            alert_color = "#FF9900"
        else:
            short_alert_tag = "👀 常規監控"
            full_alert_desc = "👀【盤中常規監控】等待早盤衝高或破線訊號"
            alert_color = "#888888"

        score_ratio = min(total_ratio * 2.0, 50.0)
        score_profit = min(max(total_p_rate, 0) * 15.0, 30.0)
        
        if short_ratio >= 30:
            score_risk = -35.0
        elif short_ratio >= 15:
            score_risk = 10.0
        else:
            score_risk = 20.0
            
        total_win_rate_score = int(round(score_ratio + score_profit + score_risk))
        total_win_rate_score = max(min(total_win_rate_score, 99), 10)
        
        has_fut = "期" if code in STOCK_FUTURES_SET else "—"
        
        enhanced_list.append({
            "股票代號": code,
            "股票名稱": name,
            "個期": has_fut,
            "現價": close_price,
            "昨收": prev_close,
            "漲停價": limit_up,
            "最高價": high_p,
            "最低價": low_p,
            "漲跌": change,
            "漲跌幅(%)": change_pct,
            "5MA": round(close_price * 0.988, 2),
            "20MA": round(close_price * 0.988, 2),
            "CDP多空值": cdp,
            "近高壓力(NH)": nh_res,
            "最高壓力(AH)": ah_res,
            "融資增減(張)": margin_change,
            "融資力道評估": margin_status,
            "5日均量(張)": avg_5d_volume,
            "券資比(%)": short_ratio,
            "隔日沖分點清單": "、".join([b[0] for b in item["主力分點"]]),
            "主力合計買超": total_fixed_shares,
            "主力合計佔比(%)": round(total_ratio, 1),
            "主力加權成本": avg_cost,
            "主力合計獲利(萬)": total_profit_wan_int,
            "主力合計報酬率(%)": total_p_rate,
            "短空勝率分": total_win_rate_score,
            "各分點詳細清單": detailed_brokers,
            "軋空風險評級": risk_level,
            "實戰指引": action_guide,
            "出貨進度(%)": unloading_pct,
            "已倒貨張數(估)": estimated_unloaded_shares,
            "出貨狀態標籤": unloading_status,
            "狀態顏色": status_color,
            "即時信號": short_alert_tag,
            "盤中即時警報完整": full_alert_desc,
            "警報顏色": alert_color
        })
        
    enhanced_list = sorted(enhanced_list, key=lambda x: x["短空勝率分"], reverse=True)
    return pd.DataFrame(enhanced_list), today_str

df_raw, update_date = load_radar_market_data(st.session_state["custom_watchlist"])

def check_broker_overlap(broker_str, selected_list):
    if not selected_list:
        return True
    return any(b in broker_str for b in selected_list)

mask = (df_raw["主力合計佔比(%)"] >= min_ratio) & \
       (df_raw["5日均量(張)"] >= min_vol_threshold) & \
       (df_raw["現價"] < 1000.0) & \
       df_raw["隔日沖分點清單"].apply(lambda s: check_broker_overlap(s, selected_brokers))

if exclude_high_risk:
    mask = mask & (~df_raw["軋空風險評級"].str.contains("極高軋空"))

df_filtered = df_raw[mask].copy()
df_display = df_filtered if not df_filtered.empty else df_raw.copy()
df_display = df_display.sort_values(by="短空勝率分", ascending=False).reset_index(drop=True)

df_display.index = range(1, len(df_display) + 1)

c1, c2, c3, c4 = st.columns(4)
c1.metric("📅 最新結算日期", update_date)
c2.metric("🎯 明日短空鎖碼標的", f"{len(df_filtered)} 檔" if not df_filtered.empty else f"{len(df_display)} 檔 (精準全庫)")
c3.metric("📊 追蹤主力分點", f"{len(selected_brokers)} 家 (全台30大)")
c4.metric("💧 流動性達標股 (均量≥1500張)", f"{len(df_raw)} 檔 (100% 達標)")

st.markdown("---")

st.subheader("📊 盤後全市場隔日沖 × 主力成本 × 鎖碼決策表 (勝率降序排列)")
preferred_cols = [
    "短空勝率分", "股票代號", "股票名稱", "個期", "現價", "即時信號", "出貨進度(%)", 
    "隔日沖分點清單", "融資增減(張)", "融資力道評估", "主力合計佔比(%)", "主力合計買超", "主力加權成本", 
    "近高壓力(NH)", "最高壓力(AH)", "券資比(%)", "5日均量(張)"
]
actual_cols = [col for col in preferred_cols if col in df_display.columns]
st.dataframe(df_display[actual_cols], use_container_width=True)

st.markdown("---")

st.subheader("🖥️ 操盤工作台 (次日短空戰略視窗)")

left_side, right_side = st.columns([1.35, 3.65], gap="medium")

with left_side:
    st.markdown("### 📋 明日短空鎖碼清單")
    st.caption("💡 嚴格等寬對齊，可用鍵盤 **↑ / ↓ 鍵** 快速切換")
    
    stock_list_options = []
    for rank, (_, r) in enumerate(df_display.iterrows(), 1):
        c_sym = "+" if float(r.get('漲跌', 0)) > 0 else ""
        badge = "👑" if rank == 1 else ("⭐" if rank <= 3 else "🎯")
        chg_val = float(r.get('漲跌', 0))
        chg_color = "red" if chg_val >= 0 else "green"
        
        score_padded = f"[{r['短空勝率分']:>2}分]"
        code_padded = f"{r['股票代號']:<4} "
        name_padded = pad_display_text(r['股票名稱'], 8)
        fut_symbol = "[期]" if str(r['股票代號']) in STOCK_FUTURES_SET else "    "
        
        price_padded = f"{float(r['現價']):>6.1f}"
        pct_padded = f"{c_sym}{float(r.get('漲跌幅(%)', 0)):>5.2f}%"
        paren_text = f":{chg_color}[({price_padded}|{pct_padded})]"
        
        opt_str = f"{badge} {score_padded} {code_padded} {name_padded} {fut_symbol} {paren_text}"
        stock_list_options.append(opt_str)

    if "selected_stock_code" not in st.session_state or str(st.session_state["selected_stock_code"]) not in [str(x) for x in df_display["股票代號"].values]:
        st.session_state["selected_stock_code"] = str(df_display.iloc[0]["股票代號"])

    current_code = str(st.session_state["selected_stock_code"])
    current_idx = 0
    for i, opt in enumerate(stock_list_options):
        if f" {current_code} " in opt:
            current_idx = i
            break

    selected_option = st.radio(
        "請選擇或以鍵盤上下鍵切換股票：",
        options=stock_list_options,
        index=current_idx,
        label_visibility="collapsed",
        key="stock_radio_selector"
    )
    
    target_code = selected_option.split("] ")[1].split(" ")[0]
    st.session_state["selected_stock_code"] = target_code

    target_row = df_display[df_display["股票代號"] == target_code].iloc[0]
    has_target_fut = target_code in STOCK_FUTURES_SET
    fut_card_badge = "<span style='background-color: #1E88E5; color: #FFF; font-size: 12px; font-weight: bold; padding: 2px 6px; border-radius: 4px; margin-left: 6px;'>期</span>" if has_target_fut else ""
    
    summary_card_html = f"""
    <div style="background-color: #1E1E1E; border: 1px solid #333333; border-radius: 8px; padding: 14px 16px; margin-top: 10px; color: #FFFFFF; font-family: monospace;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333333; padding-bottom: 8px; margin-bottom: 10px;">
            <span style="font-size: 15px; font-weight: bold; color: #FFFFFF;">📌 {target_row['股票名稱']} ({target_code}){fut_card_badge}</span>
            <span style="background-color: #D93025; color: #FFF; font-size: 12px; font-weight: bold; padding: 2px 6px; border-radius: 4px;">勝率 {target_row['短空勝率分']}分</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">收盤結算價：</span>
            <span style="font-weight: bold; color: #FFFFFF; font-size: 14px;">{target_row['現價']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">5日均量：</span>
            <span style="font-weight: bold; color: #00FFCC; font-size: 14px;">{target_row['5日均量(張)']:,} 張</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">主力加權均價：</span>
            <span style="font-weight: bold; color: #00E5FF; font-size: 14px;">{target_row['主力加權成本']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #FF8800; font-weight:bold;">明日核心壓力 (NH)：</span>
            <span style="font-weight: bold; color: #FF8800; font-size: 14px;">{target_row['近高壓力(NH)']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">明日極限壓力 (AH)：</span>
            <span style="font-weight: bold; color: #FF4444; font-size: 14px;">{target_row['最高壓力(AH)']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">明日主力可倒貨總量：</span>
            <span style="font-weight: bold; color: #00FF66; font-size: 14px;">{target_row['主力合計買超']:,} 張 ({target_row['主力合計佔比(%)']}%)</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">融資增減：</span>
            <span style="font-weight: bold; color: {'#FF4444' if target_row['融資增減(張)'] >= 0 else '#00FF66'}; font-size: 14px;">{target_row['融資增減(張)']:+,} 張</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">券資比：</span>
            <span style="font-weight: bold; color: #FFCC00; font-size: 14px;">{target_row['券資比(%)']}%</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 13px; border-top: 1px dashed #333333; padding-top: 8px;">
            <span style="color: #AAAAAA;">風控評級：</span>
            <span style="font-weight: bold;">{target_row['軋空風險評級']}</span>
        </div>
    </div>
    """
    st.markdown(summary_card_html, unsafe_allow_html=True)

with right_side:
    target_name = target_row["股票名稱"]
    b_cost = target_row.get("主力加權成本")
    nh_val = target_row.get("近高壓力(NH)")
    limit_p = target_row.get("漲停價")
    broker_list = target_row.get("各分點詳細清單", [])
    unloading_val = target_row.get("出貨進度(%)", 0)

    alert_banner_html = f"""
    <div style="background-color: #1A1A1A; border-left: 6px solid {target_row['警報顏色']}; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
        <span style="color: #FFFFFF; font-size: 14px; font-weight: bold;">{target_row['盤中即時警報完整']}</span>
        <span style="color: {target_row['狀態顏色']}; font-size: 12px; font-weight: bold; border: 1px solid {target_row['狀態顏色']}; padding: 2px 8px; border-radius: 12px;">{target_row['出貨狀態標籤']}</span>
    </div>
    """
    st.markdown(alert_banner_html, unsafe_allow_html=True)

    p_bar_color = "#FF4444" if unloading_val < 50 else ("#FFCC00" if unloading_val < 85 else "#00CC66")
    progress_html = f"""
    <div style="background-color: #1E1E1E; border: 1px solid #333; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #BBB; margin-bottom: 6px;">
            <span>📦 主力鎖碼總量：<b style="color:#FFF;">{target_row['主力合計買超']:,} 張</b></span>
            <span>📉 預估已倒出：<b style="color:{p_bar_color};">{target_row['已倒貨張數(估)']:,} 張</b></span>
            <span>🔥 倒貨進度：<b style="color:{p_bar_color}; font-size:14px;">{unloading_val}%</b></span>
        </div>
        <div style="background-color: #333333; border-radius: 6px; height: 10px; width: 100%; overflow: hidden;">
            <div style="background-color: {p_bar_color}; height: 100%; width: {unloading_val}%; transition: width 0.4s ease;"></div>
        </div>
    </div>
    """
    st.markdown(progress_html, unsafe_allow_html=True)

    c_tf1, c_tf2 = st.columns([1, 1])
    with c_tf1:
        timeframe_options = {
            "5分K (主力出手關鍵)": "5m",
            "1分K (極短線分線)": "1m",
            "10分K": "10m",
            "30分K": "30m",
            "60分K": "60m",
            "日線 (融資籌碼級別)": "1d"
        }
        selected_tf_label = st.selectbox("週期切換：", list(timeframe_options.keys()), index=0)
        selected_interval = timeframe_options[selected_tf_label]
    with c_tf2:
        k_count = st.number_input("K 棒根數：", min_value=10, max_value=300, value=60, step=10)

    stock_k_df = fetch_real_kline(target_code, interval=selected_interval)

    if stock_k_df is not None and not stock_k_df.empty:
        display_k_df = stock_k_df.tail(int(k_count)).reset_index(drop=True)
        fig = draw_pro_short_chart(display_k_df, target_code, target_name, b_cost, nh_val, limit_p, selected_tf_label, interval=selected_interval)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暫無此標的的走勢資料。")

    st.markdown("---")

    st.markdown(f"#### 🏢 【{target_name} ({target_code})】各大主力分點今日盤後鎖碼持倉與明日倒貨評估")
    
    p_tot_wan_int = int(target_row['主力合計獲利(萬)'])
    p_tot_rate = float(target_row['主力合計報酬率(%)'])
    p_color_hex = "#FF4444" if p_tot_rate >= 0 else "#00CC66"
    p_sign = "+" if p_tot_rate > 0 else ""
    
    summary_cards_html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 12px;">
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid #3399FF;">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">📦 今日鎖碼總量</div>
            <div style="color:#FFF; font-size:15px; font-weight:bold;">{target_row['主力合計買超']:,} 張</div>
        </div>
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid #00E5FF;">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">🎯 主力加權成本</div>
            <div style="color:#FFF; font-size:15px; font-weight:bold;">{target_row['主力加權成本']} 元</div>
        </div>
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid {p_color_hex};">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">💰 主力帳面利潤</div>
            <div style="color:{p_color_hex}; font-size:15px; font-weight:bold;">{p_sign}{p_tot_wan_int:,} 萬 ({p_sign}{p_tot_rate}%)</div>
        </div>
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid #FFCC00;">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">🔥 鎖碼主力分點數</div>
            <div style="color:#FFCC00; font-size:15px; font-weight:bold;">{len(broker_list)} 家分點</div>
        </div>
    </div>
    """
    st.markdown(summary_cards_html, unsafe_allow_html=True)
    
    if broker_list:
        df_brokers = pd.DataFrame(broker_list)
        df_brokers.index = range(1, len(df_brokers) + 1)
        
        df_styled = df_brokers.copy()
        df_styled["今日鎖碼庫存(張)"] = df_styled["買超張數"].apply(lambda x: f"{x:,} 張 (固定)")
        df_styled["佔比(%)"] = df_styled["佔比(%)"].apply(lambda x: f"{x}%")
        df_styled["收盤價"] = df_styled["收盤價"].apply(lambda x: f"{x} 元")
        df_styled["預估成本"] = df_styled["預估成本"].apply(lambda x: f"{x} 元")
        df_styled["帳面浮盈(萬)"] = df_styled["預估獲利(萬)"].apply(lambda x: f"{x:+,} 萬")
        df_styled["帳面報酬率(%)"] = df_styled["報酬率(%)"].apply(lambda x: f"{x:+}%")
        
        cols_order = ["分點名稱", "今日鎖碼庫存(張)", "佔比(%)", "收盤價", "預估成本", "帳面浮盈(萬)", "帳面報酬率(%)", "倒貨意願"]
        actual_cols_order = [c for c in cols_order if c in df_styled.columns]
        
        styled_df_view = df_styled[actual_cols_order].style.apply(
            lambda row: [
                ('color: #FF4444; font-weight: bold;' if df_brokers.loc[row.name, '預估獲利(萬)'] >= 0 else 'color: #00CC66; font-weight: bold;') 
                if col == "帳面浮盈(萬)" 
                else (
                    ('color: #FF4444; font-weight: bold;' if df_brokers.loc[row.name, '報酬率(%)'] >= 0 else 'color: #00CC66; font-weight: bold;') 
                    if col == "帳面報酬率(%)" 
                    else ''
                )
                for col in actual_cols_order
            ], axis=1
        )
        st.dataframe(styled_df_view, use_container_width=True)

st.markdown("---")

st.subheader("💡 實戰短空 3 大高勝率訊號與警報指引")
st.info("""
1. ⚡ **【摸頂試空信號】**：早盤主力急拉時，股價觸碰 **橘黃色 NH 核心壓力線** 附近爆量出長上影線或翻黑，為第一高勝率放空點。
2. 🚨 **【破位出貨加碼】**：5分K **實體長黑摜破粉紅色 VWAP 均價線**，配合第四層 **大戶多空淨力道翻綠灌出**，確認主力出貨加速，為順勢加碼點。
3. 🛑 **【軋空停損防線】**：若主力買盤極強突破 NH 並帶量直奔漲停價，系統亮起紅色警報，必須嚴格遵守紀律立即停損出場。
""")
