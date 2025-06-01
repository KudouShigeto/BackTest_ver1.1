import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="FX Backtest Tool", layout="wide")

st.title("📈 FXバックテストツール（EMAクロス＋RSI）")

uploaded_file = st.file_uploader("📂 CSVファイルをアップロードしてください（時間足データ）", type="csv")
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # 日付列の整形とインデックス設定
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
    elif 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    st.sidebar.header("🛠 インジケーター設定")
    short_ema = st.sidebar.number_input("短期EMA期間", min_value=1, value=20)
    long_ema = st.sidebar.number_input("長期EMA期間", min_value=2, value=50)
    rsi_period = st.sidebar.number_input("RSI期間", min_value=1, value=14)
    rsi_entry_threshold = st.sidebar.slider("RSI エントリー閾値（以下でロング）", 0, 100, 30)

    # EMAの計算
    df["EMA_short"] = df["Close"].ewm(span=short_ema, adjust=False).mean()
    df["EMA_long"] = df["Close"].ewm(span=long_ema, adjust=False).mean()

    # RSIの計算
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=rsi_period).mean()
    avg_loss = loss.rolling(window=rsi_period).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # 売買シグナルの生成
    df["Signal"] = ""
    position = None
    entry_price = 0
    results = []

    for i in range(1, len(df)):
        if (
            df["EMA_short"].iloc[i] > df["EMA_long"].iloc[i]
            and df["EMA_short"].iloc[i - 1] <= df["EMA_long"].iloc[i - 1]
            and df["RSI"].iloc[i] < rsi_entry_threshold
        ):
            if position is None:
                position = "long"
                entry_price = df["Close"].iloc[i]
                df.at[df.index[i], "Signal"] = "Buy"

        elif position == "long":
            if (
                df["EMA_short"].iloc[i] < df["EMA_long"].iloc[i]
                or df["RSI"].iloc[i] > 70
            ):
                exit_price = df["Close"].iloc[i]
                profit = (exit_price - entry_price) * 10000  # pips計算
                results.append(
                    {
                        "Entry Time": df.index[i],
                        "Entry Price": entry_price,
                        "Exit Price": exit_price,
                        "Profit (pips)": profit,
                    }
                )
                position = None
                df.at[df.index[i], "Signal"] = "Sell"

    results_df = pd.DataFrame(results)

    st.subheader("📊 売買シグナル付きチャート")
    st.line_chart(df[["Close", "EMA_short", "EMA_long"]])

    if not results_df.empty:
        st.subheader("💰 トレード結果")
        st.dataframe(results_df)
        total_pips = results_df["Profit (pips)"].sum()
        st.success(f"総獲得pips: {total_pips:.2f}")
        st.download_button(
            "⬇ 結果をCSVでダウンロード",
            results_df.to_csv(index=False).encode("utf-8"),
            file_name="backtest_results.csv",
            mime="text/csv",
        )
    else:
        st.warning("トレード条件を満たす取引が見つかりませんでした。")
else:
    st.info("上記にCSVファイルをアップロードしてください。")
