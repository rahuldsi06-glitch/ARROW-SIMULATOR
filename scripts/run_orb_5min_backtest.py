#!/usr/bin/env python3
"""
Executes the 6-month 5-Minute ORB (2:1 Risk-to-Reward) backtest on NIFTY 50
using Arrow Trade historical data.
"""

from __future__ import annotations
import json
import math
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from arrow_trader import MarketService
from arrow_trader.backtest import BacktestEngine

def fetch_6m_5min_candles(client, exchange="NSE", token="26000", days_back=180):
    all_candles = []
    chunk_size = 30
    num_chunks = math.ceil(days_back / chunk_size)

    for i in range(num_chunks):
        t_end = datetime.now() - timedelta(days=i * chunk_size)
        t_start = datetime.now() - timedelta(days=(i + 1) * chunk_size)
        from_iso = t_start.strftime("%Y-%m-%dT09:15:00")
        to_iso = t_end.strftime("%Y-%m-%dT15:30:00")
        try:
            bars = client.candle_data(
                exchange=exchange,
                token=token,
                interval="5min",
                from_timestamp=from_iso,
                to_timestamp=to_iso
            )
            if bars:
                all_candles.extend(bars)
        except Exception as e:
            print(f"Error fetching chunk {i}: {e}")

    df = BacktestEngine.candles_to_dataframe(all_candles)
    if not df.empty:
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df


def execute_orb_5min():
    market = MarketService()
    client = market.manager.get_client()

    print("Fetching 180 days (6 months) of 5-min candles for NIFTY 50...")
    df = fetch_6m_5min_candles(client, exchange="NSE", token="26000", days_back=180)
    print(f"Fetched {len(df)} 5-min candles across {df['timestamp'].dt.date.nunique()} trading days.")

    res = BacktestEngine._run_orb_5min_2to1_backtest(
        df=df,
        params={
            "target_ratio": 0.5,
            "sl_ratio": 1.0,
            "lot_size": 25,
            "fixed_risk": 10000.0
        },
        initial_capital=1000000.0
    )

    print("\n================ BACKTEST RESULTS ================")
    print(json.dumps(res["period"], indent=2))
    print(json.dumps(res["target_statistics"], indent=2))
    print(json.dumps(res["performance"], indent=2))

    # Monthly breakdown
    trades_df = pd.DataFrame(res["recent_trades"])
    if not trades_df.empty:
        trades_df["month"] = pd.to_datetime(trades_df["date"]).dt.to_period("M")
        monthly = trades_df.groupby("month").agg(
            trades=("date", "count"),
            target_hits=("exit_reason", lambda x: (x == "Target Hit (50% Range)").sum()),
            sl_hits=("exit_reason", lambda x: (x == "Stop Loss Hit (Full Candle)").sum()),
            eod_exits=("exit_reason", lambda x: (x == "EOD Square-off").sum()),
            net_points=("points_pnl", "sum"),
            net_pnl=("pnl_rupees", "sum")
        ).reset_index()
        monthly["target_hit_rate"] = (monthly["target_hits"] / monthly["trades"] * 100).round(1)
        print("\n================ MONTHLY BREAKDOWN ================")
        print(monthly.to_string(index=False))

    with open("/Users/rahul/Documents/Arrow_Algo_trader/orb_5min_results.json", "w") as f:
        json.dump(res, f, indent=2)

    return res

if __name__ == "__main__":
    execute_orb_5min()
