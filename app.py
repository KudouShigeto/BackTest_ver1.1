import streamlit as st
import pandas as pd
import numpy as np

import pandas_ta as ta

st.title("📊 FXバックテスト：EMAクロス + RSI条件")

uploaded_file = st.file_uploader("✅ TrueFX形式のCSVファイルをアップロード", type=["csv"])

# インジケーターのパラメータ設定
st.sidebar.header("📐 インジケーター設定")
ema_short_period = st.sidebar.number_input("EMA短期期間", min_value=2, max_value=100, value=50)
ema_long_period = st.sidebar.number_input("EMA長期期間", min_value=2, max_value=200, value=100)
rsi_period = st.sidebar.number_input("RSI期間", min_value=2, max_value=50, value=14)
rsi_buy_level = st.sidebar.number_input("RSI買われすぎ（売りの閾値）", min_value=50, max_value=100, value=70)
rsi_sell_level = st.sidebar.number_input("RSI売られすぎ（買いの閾値）", min_value=0, max_value=50, value=30)

if uploaded_file:
    df = pd.read_csv(uploaded_file, skiprows=1)
    df.columns = ["Date", "BidOpen", "BidHigh", "BidLow", "BidClose", "AskOpen", "AskHigh", "AskLow", "AskClose"]
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    df["Close"] = df["BidClose"]

    # インジケーター計算
    df["EMA_short"] = df["Close"].ewm(span=ema_short_period).mean()
    df["EMA_long"] = df["Close"].ewm(span=ema_long_period).mean()
    df["RSI"] = ta.rsi(df["Close"], length=rsi_period)

    # シグナル計算
    df["Signal"] = 0
    df["Signal"] = np.where(
        (df["EMA_short"] > df["EMA_long"]) & (df["EMA_short"].shift(1) <= df["EMA_long"].shift(1)) & (df["RSI"] < rsi_sell_level),
        1,
        np.where(
            (df["EMA_short"] < df["EMA_long"]) & (df["EMA_short"].shift(1) >= df["EMA_long"].shift(1)) & (df["RSI"] > rsi_buy_level),
            -1,
            0
        )
    )

    # バックテストロジック
    trades = []
    position = None
    entry_price = None
    entry_time = None

    for i in range(1, len(df)):
        row = df.iloc[i]
        if position is None:
            if row["Signal"] == 1:
                position = "long"
                entry_price = row["Close"]
                entry_time = row.name
            elif row["Signal"] == -1:
                position = "short"
                entry_price = row["Close"]
                entry_time = row.name

        elif position == "long" and row["Signal"] == -1:
            exit_price = row["Close"]
            exit_time = row.name
            pnl = (exit_price - entry_price) * 10000
            trades.append([entry_time, exit_time, "long", entry_price, exit_price, pnl])
            position = "short"
            entry_price = row["Close"]
            entry_time = row.name

        elif position == "short" and row["Signal"] == 1:
            exit_price = row["Close"]
            exit_time = row.name
            pnl = (entry_price - exit_price) * 10000
            trades.append([entry_time, exit_time, "short", entry_price, exit_price, pnl])
            position = "long"
            entry_price = row["Close"]
            entry_time = row.name

    result_df = pd.DataFrame(trades, columns=["Entry Time", "Exit Time", "Direction", "Entry Price", "Exit Price", "PnL (pips)"])

    st.success(f"💹 トレード数：{len(result_df)}件")
    st.dataframe(result_df)

    # CSVダウンロード
    csv = result_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ 結果CSVをダウンロード", csv, "backtest_results.csv", "text/csv")
