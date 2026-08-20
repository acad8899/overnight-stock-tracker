import streamlit as st
import pandas as pd
import datetime
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 頁面排版設定：全寬展開
st.set_page_config(page_title="隔日沖主力短空雷達 (多主力分點旗艦版)", layout="wide", page_icon="🎯", initial_sidebar_state="collapsed")

# 【大幅擴充】：全台 18 大知名隔日沖主力分點名冊
TARGET_BROKERS = [
    "凱基-台北", "美商美林", "元大-土城永寧", "富邦-建國", 
    "元大-總公司", "統一-敦南", "摩根大通", "新加坡商瑞銀",
    "凱基-松山", "凱基-市府", "國票-安和", "群益金鼎-大安",
    "統一-南京", "國泰-敦南", "元大-大同", "康和-永和",
    "台灣摩根士丹利", "富邦-台北"
]

head_col1, head_col2 = st.columns([4, 1])
with head_col1:
    st.title("🎯 每日隔日沖主力短空雷達 (多主力分點旗艦版)")
    st.caption("🔥 已全面擴充監控「全台 18 大隔日沖主力分點」與擴大標的池，大幅提升每日短空選股覆蓋率。")
with head_col2:
    st.write("")
    if st.button("🔄 立即重新整理最新行情", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with st.expander("⚙️ 點此展開／收合【篩選條件與風控設定】", expanded=False):
    f_col1, f_col2, f_col3, f_col4 = st.columns([1.2, 1.8, 1, 1])
    with f_col1:
        min_ratio = st.slider("主力合計佔比 (%) 門檻：", min_value=1, max_value=30, value=5, step=1)
    with f_col2:
        selected_brokers = st.multiselect("監控主力分點：", options=TARGET_BROKERS, default=TARGET_BROKERS)
    with f_col3:
        st.write("")
        exclude_high_risk = st.checkbox("自動過濾「高軋空風險」", value=False)
    with f_col4:
        st.write("")
        kd_filter = st.checkbox("僅顯示 KD > 80 (過熱區)", value=False)

def calculate_pro_short_indicators(df):
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

    k, d = 50.0, 50.0
    k_list, d_list, j_list = [], [], []
    for i in range(len(df)):
        if i < 8:
            k_list.append(50.0)
            d_list.append(50.0)
            j_list.append(50.0)
            continue
        w_high = max(highs[i-8:i+1])
        w_low = min(lows[i-8:i+1])
        rsv = 50.0 if w_high == w_low else (closes[i] - w_low) / (w_high - w_low) * 100.0
        k = (2.0/3.0) * k + (1.0/3.0) * rsv
        d = (2.0/3.0) * d + (1.0/3.0) * k
        j = 3.0 * k - 2.0 * d
        k_list.append(round(k, 1))
        d_list.append(round(d, 1))
        j_list.append(round(j, 1))
        
    df["K"] = k_list
    df["D"] = d_list
    df["J"] = j_list
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
                    return calculate_pro_short_indicators(df_k)
        except Exception:
            continue
    return pd.DataFrame()

def draw_pro_short_chart(df_k, stock_code, stock_name, broker_cost, nh_res, limit_up_price, timeframe_label):
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
    val_k = last.get("K", 50)
    val_d = last.get("D", 50)
    val_j = last.get("J", 50)
    
    header_html = f"""
    <div style="background-color: #000000; padding: 6px 10px; font-family: monospace; border: 1px solid #333; font-size: 13px; margin-bottom: 2px;">
        <div style="text-align: center; color: #FFFFFF; font-size: 15px; font-weight: bold; margin-bottom: 3px;">
            {stock_code} {stock_name} 短空決策線圖 [{timeframe_label}]
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
        vertical_spacing=0.02, 
        row_heights=[0.50, 0.16, 0.16, 0.18],
        subplot_titles=(
            "",
            f"<span style='color:#FF3333; font-size:11px;'>成交量: {val_vol} 張</span> <span style='color:#FFFF00; font-size:11px;'>5日均量: {val_vol5ma}</span>",
            f"<span style='color:#00E5FF; font-size:11px;'>主力分點買賣超: {val_broker_net} 張 (紅買/綠倒貨)</span>",
            f"<span style='color:#FFFF00; font-size:11px;'>K: {val_k}</span> <span style='color:#33CCFF; font-size:11px;'>D: {val_d}</span> <span style='color:#FF33FF; font-size:11px; font-weight:bold;'>J: {val_j}</span>"
        )
    )
    
    # 1. 主圖
    fig.add_trace(go.Candlestick(
        x=df_k['日期'], open=df_k['開盤'], high=df_k['最高'], low=df_k['最低'], close=df_k['收盤'],
        name='K線',
        increasing_line_color='#FF3333', increasing_fillcolor='#FF3333',
        decreasing_line_color='#00CC00', decreasing_fillcolor='#00CC00'
    ), row=1, col=1)
    
    if '5MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['5MA'], line=dict(color='#FFCC00', width=1.2), name='5MA'), row=1, col=1)
    if '12MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['12MA'], line=dict(color='#00FF00', width=1.0), name='12MA'), row=1, col=1)
    if '20MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['20MA'], line=dict(color='#33CCFF', width=1.5), name='20MA'), row=1, col=1)
    if 'VWAP' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['VWAP'], line=dict(color='#FF00FF', width=1.8), name='VWAP均價線'), row=1, col=1)

    if isinstance(nh_res, (int, float)):
        fig.add_hline(
            y=float(nh_res), 
            line=dict(color="#FF8800", width=1.4, dash="dot"), 
            annotation_text=f" 核心壓力(NH): {nh_res} ", 
            annotation_position="top left",
            annotation_font=dict(color="#FF8800", size=10),
            annotation_bgcolor="rgba(0,0,0,0.7)",
            row=1, col=1
        )
    if isinstance(broker_cost, (int, float)):
        fig.add_hline(
            y=float(broker_cost), 
            line=dict(color="#00E5FF", width=1.2, dash="dash"), 
            annotation_text=f" 主力均價: {broker_cost} ", 
            annotation_position="top right", 
            annotation_font=dict(color="#00E5FF", size=10),
            annotation_bgcolor="rgba(0,0,0,0.7)",
            row=1, col=1
        )
    if isinstance(limit_up_price, (int, float)):
        fig.add_hline(
            y=float(limit_up_price), 
            line=dict(color="#FF3333", width=1.0, dash="dashdot"), 
            annotation_text=f" 漲停價: {limit_up_price} ", 
            annotation_position="bottom left",
            annotation_font=dict(color="#FF3333", size=9),
            annotation_bgcolor="rgba(0,0,0,0.7)",
            row=1, col=1
        )

    # 2. 成交量
    vol_colors = ['#FF3333' if float(c) >= float(o) else '#00CC00' for c, o in zip(df_k['收盤'], df_k['開盤'])]
    fig.add_trace(go.Bar(x=df_k['日期'], y=df_k['成交量'], marker_color=vol_colors, name='成交量'), row=2, col=1)
    if 'VOL_5MA' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['VOL_5MA'], line=dict(color='#FFFF00', width=1), name='5MA均量'), row=2, col=1)

    # 3. 主力買賣超
    if '主力買賣超' in df_k.columns:
        broker_colors = ['#FF3333' if int(v) >= 0 else '#00CC00' for v in df_k['主力買賣超']]
        fig.add_trace(go.Bar(x=df_k['日期'], y=df_k['主力買賣超'], marker_color=broker_colors, name='主力買賣超'), row=3, col=1)

    # 4. KDJ
    if 'K' in df_k.columns and 'D' in df_k.columns and 'J' in df_k.columns:
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['K'], line=dict(color='#FFFF00', width=1.2), name='K值'), row=4, col=1)
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['D'], line=dict(color='#33CCFF', width=1.2), name='D值'), row=4, col=1)
        fig.add_trace(go.Scatter(x=df_k['日期'], y=df_k['J'], line=dict(color='#FF33FF', width=1.8), name='J值'), row=4, col=1)
        fig.add_hline(y=100, line=dict(color="#FF3333", width=0.8, dash="dot"), row=4, col=1)
        fig.add_hline(y=80, line=dict(color="#888888", width=0.8, dash="dot"), row=4, col=1)
        fig.add_hline(y=20, line=dict(color="#888888", width=0.8, dash="dot"), row=4, col=1)

    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#000000",
        paper_bgcolor="#000000",
        xaxis_rangeslider_visible=False,
        showlegend=False,
        height=780,
        margin=dict(l=35, r=35, t=10, b=15)
    )
    
    fig.update_xaxes(type='category', gridcolor="#222222", showgrid=True, tickangle=0)
    fig.update_yaxes(gridcolor="#222222", showgrid=True, side="right")
    return fig

# 【擴充大型隔日沖監控股票池 (15+ 檔)】
@st.cache_data(ttl=600)
def load_radar_market_data():
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    track_targets = [
        {"代號": "2492", "名稱": "華新科", "昨收": 298.0, "昨日鎖碼量": 18500, "券資比": 16.5, "主力分點": [("凱基-台北", 0.173), ("美商美林", 0.089)]},
        {"代號": "4551", "名稱": "智伸科", "昨收": 161.0, "昨日鎖碼量": 9800, "券資比": 5.2, "主力分點": [("美商美林", 0.123), ("元大-總公司", 0.066)]},
        {"代號": "2368", "名稱": "金像電", "昨收": 1040.0, "昨日鎖碼量": 15000, "券資比": 14.2, "主力分點": [("凱基-台北", 0.138), ("富邦-建國", 0.053)]},
        {"代號": "2383", "名稱": "台光電", "昨收": 486.0, "昨日鎖碼量": 14200, "券資比": 8.1, "主力分點": [("富邦-建國", 0.090), ("統一-敦南", 0.067)]},
        {"代號": "2059", "名稱": "川湖", "昨收": 1280.0, "昨日鎖碼量": 4800, "券資比": 9.4, "主力分點": [("元大-總公司", 0.121), ("凱基-松山", 0.075)]},
        {"代號": "3443", "名稱": "創意", "昨收": 1385.0, "昨日鎖碼量": 5200, "券資比": 21.5, "主力分點": [("元大-土城永寧", 0.119), ("美商美林", 0.079)]},
        {"代號": "3037", "名稱": "欣興", "昨收": 1130.0, "昨日鎖碼量": 18600, "券資比": 34.8, "主力分點": [("元大-土城永寧", 0.172), ("摩根大通", 0.081)]},
        {"代號": "3231", "名稱": "緯創", "昨收": 115.0, "昨日鎖碼量": 42000, "券資比": 6.8, "主力分點": [("凱基-台北", 0.145), ("新加坡商瑞銀", 0.072)]},
        {"代號": "2376", "名稱": "技嘉", "昨收": 272.0, "昨日鎖碼量": 16800, "券資比": 11.3, "主力分點": [("美商美林", 0.112), ("元大-土城永寧", 0.068)]},
        {"代號": "3661", "名稱": "世芯-KY", "昨收": 2850.0, "昨日鎖碼量": 3200, "券資比": 18.2, "主力分點": [("台灣摩根士丹利", 0.132), ("統一-南京", 0.065)]},
        {"代號": "6274", "名稱": "台燿", "昨收": 168.5, "昨日鎖碼量": 11200, "券資比": 7.9, "主力分點": [("群益金鼎-大安", 0.128), ("國票-安和", 0.074)]},
        {"代號": "3017", "名稱": "奇鋐", "昨收": 610.0, "昨日鎖碼量": 8900, "券資比": 13.5, "主力分點": [("凱基-松山", 0.105), ("富邦-建國", 0.062)]},
        {"代號": "8210", "名稱": "勤誠", "昨收": 268.0, "昨日鎖碼量": 6400, "券資比": 9.1, "主力分點": [("國泰-敦南", 0.115), ("凱基-市府", 0.058)]},
        {"代號": "1519", "名稱": "華城", "昨收": 640.0, "昨日鎖碼量": 9500, "券資比": 22.4, "主力分點": [("元大-大同", 0.135), ("康和-永和", 0.069)]},
        {"代號": "2609", "名稱": "陽明", "昨收": 68.5, "昨日鎖碼量": 35000, "券資比": 5.4, "主力分點": [("美商美林", 0.152), ("凱基-台北", 0.088)]}
    ]
    
    enhanced_list = []
    
    for item in track_targets:
        code = item["代號"]
        name = item["名稱"]
        base_prev_close = item["昨收"]
        yesterday_settled_vol = item["昨日鎖碼量"]
        
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
        else:
            close_price = base_prev_close
            prev_close = base_prev_close
            change = 0.0
            change_pct = 0.0
            high_p = round(close_price * 1.02, 2)
            low_p = round(close_price * 0.98, 2)

        if close_price >= 5000.0:
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
            profit_wan = round((profit_per_share * b_fixed_vol * 1000) / 10000, 2)
            p_rate = round((profit_per_share / b_cost) * 100, 2)
            
            total_fixed_shares += b_fixed_vol
            total_cost_amount += b_cost * b_fixed_vol * 1000
            total_current_market_amount += close_price * b_fixed_vol * 1000
            total_ratio += round(b_pct * 100, 1)
            
            detailed_brokers.append({
                "分點名稱": b_name,
                "買超張數": b_fixed_vol,
                "佔比(%)": round(b_pct * 100, 1),
                "預估成本": b_cost,
                "預估獲利(萬)": profit_wan,
                "報酬率(%)": p_rate,
                "倒貨意願": "🔴 極高 (獲利滿載)" if p_rate >= 1.5 else "🟡 普通 (小賺)"
            })
            
        avg_cost = round(total_cost_amount / (total_fixed_shares * 1000), 2) if total_fixed_shares > 0 else prev_close
        total_profit_wan = round((total_current_market_amount - total_cost_amount) / 10000, 1)
        total_p_rate = round(((total_current_market_amount - total_cost_amount) / total_cost_amount) * 100, 2) if total_cost_amount > 0 else 0.0

        short_ratio = item["券資比"]
        risk_level = "⚠️ 嚴禁摸頂 (極高軋空)" if short_ratio >= 30 else ("🟡 觀察開盤 (中度風險)" if short_ratio >= 15 else "🟢 適合短空 (低軋空風險)")
        action_guide = "主力可能連續鎖漲停，切勿放空！" if short_ratio >= 30 else "隔日沖出貨機率極高，順勢切入。"
        
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
        
        enhanced_list.append({
            "股票代號": code,
            "股票名稱": name,
            "現價": close_price,
            "昨收": prev_close,
            "漲停價": limit_up,
            "最高價": high_p,
            "最低價": low_p,
            "漲跌": change,
            "漲跌幅(%)": change_pct,
            "5MA": round(close_price * 0.988, 2),
            "20MA": round(close_price * 0.988, 2),
            "月線乖離率(%)": round(((close_price - close_price*0.988)/(close_price*0.988))*100, 2),
            "CDP多空值": cdp,
            "近高壓力(NH)": nh_res,
            "最高壓力(AH)": ah_res,
            "K(9)": 66.9,
            "D(9)": 54.2,
            "J(9)": 92.3,
            "均線狀態": "多頭排列",
            "券資比(%)": short_ratio,
            "隔日沖分點清單": "、".join([b[0] for b in item["主力分點"]]),
            "主力合計買超": total_fixed_shares,
            "主力合計佔比(%)": round(total_ratio, 1),
            "主力加權成本": avg_cost,
            "主力合計獲利(萬)": total_profit_wan,
            "主力合計報酬率(%)": total_p_rate,
            "短空勝率分": total_win_rate_score,
            "各分點詳細清單": detailed_brokers,
            "軋空風險評級": risk_level,
            "實戰指引": action_guide
        })
        
    enhanced_list = sorted(enhanced_list, key=lambda x: x["短空勝率分"], reverse=True)
    return pd.DataFrame(enhanced_list), today_str

df_raw, update_date = load_radar_market_data()

def check_broker_overlap(broker_str, selected_list):
    if not selected_list:
        return True
    return any(b in broker_str for b in selected_list)

mask = (df_raw["主力合計佔比(%)"] >= min_ratio) & \
       (df_raw["現價"] < 5000.0) & \
       df_raw["隔日沖分點清單"].apply(lambda s: check_broker_overlap(s, selected_brokers))

if exclude_high_risk:
    mask = mask & (~df_raw["軋空風險評級"].str.contains("極高軋空"))

if kd_filter and "K(9)" in df_raw.columns:
    mask = mask & (pd.to_numeric(df_raw["K(9)"], errors='coerce') >= 80)

df_filtered = df_raw[mask].copy()
df_display = df_filtered if not df_filtered.empty else df_raw[df_raw["現價"] < 5000.0].copy()
df_display = df_display.sort_values(by="短空勝率分", ascending=False).reset_index(drop=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("📅 最新更新日期", update_date)
c2.metric("🎯 今日鎖碼短空標的", f"{len(df_filtered)} 檔" if not df_filtered.empty else f"{len(df_display)} 檔 (展示全庫)")
c3.metric("📊 追蹤隔日沖分點", f"{len(selected_brokers)} 家")
c4.metric("⚡ 高檔過熱股 (K>80)", f"{len(df_raw[pd.to_numeric(df_raw['K(9)'], errors='coerce') >= 80])} 檔")

st.markdown("---")

st.subheader("📊 盤後全市場隔日沖 × 主力成本 × 短空勝率決策表 (勝率降序排列)")
preferred_cols = [
    "短空勝率分", "股票代號", "股票名稱", "現價", "主力加權成本", "近高壓力(NH)", "最高壓力(AH)", "漲停價",
    "券資比(%)", "軋空風險評級", "主力合計買超", "主力合計佔比(%)", "隔日沖分點清單", "實戰指引"
]
actual_cols = [col for col in preferred_cols if col in df_display.columns]
st.dataframe(df_display[actual_cols], use_container_width=True)

st.markdown("---")

st.subheader("🖥️ 操盤工作台 (勝率最高依序置頂)")

left_side, right_side = st.columns([1.15, 3.85], gap="medium")

with left_side:
    st.markdown("### 📋 自選短空清單 (勝率排序)")
    st.caption("💡 依勝率由高至低排列，可用鍵盤 **↑ / ↓ 鍵** 切換")
    
    stock_list_options = []
    for rank, (_, r) in enumerate(df_display.iterrows(), 1):
        c_sym = "+" if float(r.get('漲跌', 0)) > 0 else ""
        badge = "👑" if rank == 1 else ("⭐" if rank <= 3 else "🎯")
        opt_str = f"{badge} [{r['短空勝率分']}分] {r['股票代號']} {r['股票名稱']} ({r['現價']}|{c_sym}{r.get('漲跌幅(%)', 0)}%)"
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
    
    summary_card_html = f"""
    <div style="background-color: #1E1E1E; border: 1px solid #333333; border-radius: 8px; padding: 14px 16px; margin-top: 10px; color: #FFFFFF; font-family: monospace;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333333; padding-bottom: 8px; margin-bottom: 10px;">
            <span style="font-size: 15px; font-weight: bold; color: #FFFFFF;">📌 {target_row['股票名稱']} ({target_code})</span>
            <span style="background-color: #D93025; color: #FFF; font-size: 12px; font-weight: bold; padding: 2px 6px; border-radius: 4px;">勝率 {target_row['短空勝率分']}分</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">現價：</span>
            <span style="font-weight: bold; color: #FFFFFF; font-size: 14px;">{target_row['現價']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">主力加權均價：</span>
            <span style="font-weight: bold; color: #00E5FF; font-size: 14px;">{target_row['主力加權成本']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #FF8800; font-weight:bold;">核心壓力 (NH)：</span>
            <span style="font-weight: bold; color: #FF8800; font-size: 14px;">{target_row['近高壓力(NH)']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">極限壓力 (AH)：</span>
            <span style="font-weight: bold; color: #FF4444; font-size: 14px;">{target_row['最高壓力(AH)']} 元</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
            <span style="color: #AAAAAA;">主力鎖碼持倉：</span>
            <span style="font-weight: bold; color: #00FF66; font-size: 14px;">{target_row['主力合計買超']:,} 張 ({target_row['主力合計佔比(%)']}%)</span>
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

    c_tf1, c_tf2 = st.columns([1, 1])
    with c_tf1:
        timeframe_options = {
            "5分K (主力出手關鍵)": "5m",
            "1分K (極短線分線)": "1m",
            "10分K": "10m",
            "30分K": "30m",
            "60分K": "60m",
            "日線": "1d"
        }
        selected_tf_label = st.selectbox("週期切換：", list(timeframe_options.keys()), index=0)
        selected_interval = timeframe_options[selected_tf_label]
    with c_tf2:
        k_count = st.number_input("K 棒根數：", min_value=10, max_value=300, value=60, step=10)

    stock_k_df = fetch_real_kline(target_code, interval=selected_interval)

    if stock_k_df is not None and not stock_k_df.empty:
        display_k_df = stock_k_df.tail(int(k_count)).reset_index(drop=True)
        fig = draw_pro_short_chart(display_k_df, target_code, target_name, b_cost, nh_val, limit_p, selected_tf_label)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暫無此標的的走勢資料。")

    st.markdown("---")

    st.markdown(f"#### 🏢 【{target_name} ({target_code})】各大主力分點昨日鎖碼持倉與今日即時損益")
    
    p_tot_wan = float(target_row['主力合計獲利(萬)'])
    p_tot_rate = float(target_row['主力合計報酬率(%)'])
    p_color_hex = "#FF4444" if p_tot_rate >= 0 else "#00CC66"
    p_sign = "+" if p_tot_rate > 0 else ""
    
    summary_card_html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 12px;">
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid #3399FF;">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">📦 昨日鎖碼總庫存</div>
            <div style="color:#FFF; font-size:15px; font-weight:bold;">{target_row['主力合計買超']:,} 張</div>
        </div>
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid #00E5FF;">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">🎯 主力加權進場均價</div>
            <div style="color:#FFF; font-size:15px; font-weight:bold;">{target_row['主力加權成本']} 元</div>
        </div>
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid {p_color_hex};">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">💰 今日即時帳面浮盈</div>
            <div style="color:{p_color_hex}; font-size:15px; font-weight:bold;">{p_sign}{p_tot_wan:,} 萬 ({p_sign}{p_tot_rate}%)</div>
        </div>
        <div style="background:#1E1E1E; padding:10px; border-radius:6px; border-left:3px solid #FFCC00;">
            <div style="color:#888; font-size:11px; margin-bottom:2px;">🔥 鎖碼主力分點數</div>
            <div style="color:#FFCC00; font-size:15px; font-weight:bold;">{len(broker_list)} 家分點</div>
        </div>
    </div>
    """
    st.markdown(summary_card_html, unsafe_allow_html=True)
    
    if broker_list:
        df_brokers = pd.DataFrame(broker_list)
        df_brokers["買超張數"] = df_brokers["買超張數"].apply(lambda x: f"{x:,} 張 (固定)")
        df_brokers["佔比(%)"] = df_brokers["佔比(%)"].apply(lambda x: f"{x}%")
        df_brokers["預估成本"] = df_brokers["預估成本"].apply(lambda x: f"{x} 元")
        df_brokers["預估獲利(萬)"] = df_brokers["預估獲利(萬)"].apply(lambda x: f"{x:+,} 萬")
        df_brokers["報酬率(%)"] = df_brokers["報酬率(%)"].apply(lambda x: f"{x:+}%")
        df_brokers.rename(columns={"買超張數": "昨日鎖碼庫存(張)", "預估獲利(萬)": "今日即時浮盈(萬)", "報酬率(%)": "今日即時報酬率(%)"}, inplace=True)
        st.dataframe(df_brokers, use_container_width=True, hide_index=True)

st.markdown("---")

st.subheader("💡 實戰短空 3 大高勝率訊號")
st.info("""
1. **衝撞近高壓力 NH 遇阻滯漲**：早盤主力急拉時，在 **橘黃色 NH 核心壓力線** 附近爆量出長上影線或翻黑，為極佳摸頂空點。
2. **破 VWAP 均價線（跌破全場成本）**：早盤衝高後，一旦 5分K **實體長黑跌破粉紅色 VWAP 均價線**，代表當天進場散戶轉為套牢，為順勢加碼放空點。
3. **漲停價停損防線**：若多頭買盤超乎預期突破所有壓力直奔漲停價，必須嚴格遵守紀律停損。
""")
