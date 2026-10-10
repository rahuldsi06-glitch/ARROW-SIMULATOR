from __future__ import annotations
import math
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


class BacktestEngine:
    """
    Backtesting engine for Arrow Trade historical candle data.
    """

    @staticmethod
    def candles_to_dataframe(candles: List[List[Any]]) -> pd.DataFrame:
        """
        Converts Arrow candle rows [timestamp, open, high, low, close, volume, (oi)]
        into a pandas DataFrame with prices converted from paise to Rupees.
        """
        if not candles:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        df = pd.DataFrame(candles)
        cols = ["timestamp", "open", "high", "low", "close", "volume"]
        if df.shape[1] > 6:
            cols.append("oi")
        df.columns = cols[: df.shape[1]]

        # Convert prices from paise to Rupees
        for price_col in ["open", "high", "low", "close"]:
            if price_col in df.columns:
                df[price_col] = df[price_col].astype(float) / 100.0

        df["volume"] = df["volume"].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    @staticmethod
    def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates key technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR).
        """
        df = df.copy()
        close = df["close"]

        # SMAs & EMAs
        df["sma_9"] = close.rolling(window=9).mean()
        df["sma_20"] = close.rolling(window=20).mean()
        df["sma_50"] = close.rolling(window=50).mean()
        df["sma_200"] = close.rolling(window=200).mean()

        df["ema_9"] = close.ewm(span=9, adjust=False).mean()
        df["ema_21"] = close.ewm(span=21, adjust=False).mean()

        # RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss.replace(0, np.nan))
        df["rsi_14"] = 100 - (100 / (1 + rs))
        df["rsi_14"] = df["rsi_14"].fillna(50)

        # MACD (12, 26, 9)
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # Bollinger Bands (20, 2)
        rolling_std = close.rolling(window=20).std()
        df["bb_middle"] = df["sma_20"]
        df["bb_upper"] = df["bb_middle"] + (rolling_std * 2)
        df["bb_lower"] = df["bb_middle"] - (rolling_std * 2)

        # ATR (14)
        high = df["high"]
        low = df["low"]
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["atr_14"] = tr.rolling(window=14).mean()

        return df

    @classmethod
    def run_backtest(
        cls,
        df: pd.DataFrame,
        strategy_name: str = "sma_crossover",
        parameters: Optional[Dict[str, Any]] = None,
        initial_capital: float = 100000.0,
    ) -> Dict[str, Any]:
        """
        Executes a backtest on candle DataFrame and returns performance metrics.
        """
        if df.empty or len(df) < 5:
            return {"error": "Insufficient candle data for backtesting (minimum 5 bars required)."}

        params = parameters or {}
        df = df.copy()

        # Generate signals based on selected strategy
        strat = strategy_name.lower().strip()
        if strat in ("orb", "opening_range_breakout"):
            return cls._run_orb_backtest(df, params, initial_capital)

        if strat in ("orb_pdh_pdl", "orb_filter", "orb_advanced"):
            return cls._run_orb_pdh_pdl_backtest(df, params, initial_capital)

        signals = pd.Series(0, index=df.index)  # 1: Long, -1: Flat/Exit

        if strat in ("sma_crossover", "ema_crossover"):
            fast_p = int(params.get("fast_period", 9))
            slow_p = int(params.get("slow_period", 21))
            is_ema = "ema" in strat

            if is_ema:
                fast = df["close"].ewm(span=fast_p, adjust=False).mean()
                slow = df["close"].ewm(span=slow_p, adjust=False).mean()
            else:
                fast = df["close"].rolling(window=fast_p).mean()
                slow = df["close"].rolling(window=slow_p).mean()

            signals = np.where(fast > slow, 1, 0)

        elif strat == "rsi":
            period = int(params.get("period", 14))
            oversold = float(params.get("oversold", 30))
            overbought = float(params.get("overbought", 70))

            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / (loss.replace(0, np.nan))
            rsi = 100 - (100 / (1 + rs))

            # Enter when RSI crosses above oversold, exit when above overbought
            pos = 0
            sig = []
            for val in rsi:
                if val <= oversold:
                    pos = 1
                elif val >= overbought:
                    pos = 0
                sig.append(pos)
            signals = np.array(sig)

        elif strat == "bollinger_bands":
            period = int(params.get("period", 20))
            num_std = float(params.get("std", 2.0))
            ma = df["close"].rolling(window=period).mean()
            std = df["close"].rolling(window=period).std()
            lower = ma - (std * num_std)
            upper = ma + (std * num_std)

            # Buy when dipping below lower band, exit when reaching upper band
            pos = 0
            sig = []
            for c, l, u in zip(df["close"], lower, upper):
                if c <= l:
                    pos = 1
                elif c >= u:
                    pos = 0
                sig.append(pos)
            signals = np.array(sig)

        elif strat == "breakout":
            lookback = int(params.get("lookback", 20))
            highest_high = df["high"].rolling(window=lookback).max().shift(1)
            lowest_low = df["low"].rolling(window=lookback).min().shift(1)

            pos = 0
            sig = []
            for c, h, l in zip(df["close"], highest_high, lowest_low):
                if c > h:
                    pos = 1
                elif c < l:
                    pos = 0
                sig.append(pos)
            signals = np.array(sig)

        else:
            # Default momentum strategy
            ret = df["close"].pct_change(5)
            signals = np.where(ret > 0, 1, 0)

        # Simulation loop
        capital = initial_capital
        position = 0  # number of shares
        entry_price = 0.0
        entry_time = None
        trades: List[Dict[str, Any]] = []
        equity_curve: List[float] = [capital]

        for i in range(1, len(df)):
            curr_signal = signals[i]
            prev_signal = signals[i - 1]
            price = df.loc[i, "close"]
            timestamp = df.loc[i, "timestamp"]

            # Buy Signal: transition from 0 -> 1
            if curr_signal == 1 and position == 0:
                shares = math.floor(capital / price)
                if shares > 0:
                    position = shares
                    entry_price = price
                    entry_time = timestamp
                    capital -= shares * price

            # Sell Signal: transition from 1 -> 0
            elif curr_signal == 0 and position > 0:
                revenue = position * price
                capital += revenue
                pnl = (price - entry_price) * position
                pnl_pct = ((price - entry_price) / entry_price) * 100
                trades.append({
                    "entry_time": str(entry_time),
                    "exit_time": str(timestamp),
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(price, 2),
                    "shares": position,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                })
                position = 0
                entry_price = 0.0

            # Mark to market equity
            current_equity = capital + (position * price)
            equity_curve.append(current_equity)

        # Close position at the end of data if still open
        if position > 0:
            final_price = df.iloc[-1]["close"]
            capital += position * final_price
            pnl = (final_price - entry_price) * position
            pnl_pct = ((final_price - entry_price) / entry_price) * 100
            trades.append({
                "entry_time": str(entry_time),
                "exit_time": str(df.iloc[-1]["timestamp"]),
                "entry_price": round(entry_price, 2),
                "exit_price": round(final_price, 2),
                "shares": position,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
            })

        # Calculate performance statistics
        ending_capital = capital
        total_pnl = ending_capital - initial_capital
        total_return_pct = (total_pnl / initial_capital) * 100

        # Benchmark Buy & Hold
        first_close = df.iloc[0]["close"]
        last_close = df.iloc[-1]["close"]
        buy_hold_return_pct = ((last_close - first_close) / first_close) * 100

        # Max Drawdown
        equity_series = pd.Series(equity_curve)
        peak = equity_series.cummax()
        drawdown = (equity_series - peak) / peak
        max_drawdown_pct = abs(float(drawdown.min())) * 100

        # Trade metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t["pnl"] > 0]
        losing_trades = [t for t in trades if t["pnl"] <= 0]
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0

        gross_profit = sum(t["pnl"] for t in winning_trades)
        gross_loss = abs(sum(t["pnl"] for t in losing_trades))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        # Sharpe ratio approximation
        returns = equity_series.pct_change().dropna()
        sharpe = round(float(np.sqrt(252) * (returns.mean() / returns.std())), 2) if returns.std() > 0 else 0.0

        return {
            "strategy": strategy_name,
            "parameters": params,
            "period": {
                "start": str(df.iloc[0]["timestamp"]),
                "end": str(df.iloc[-1]["timestamp"]),
                "bars": len(df),
            },
            "performance": {
                "initial_capital": round(initial_capital, 2),
                "ending_capital": round(ending_capital, 2),
                "net_profit": round(total_pnl, 2),
                "total_return_pct": round(total_return_pct, 2),
                "buy_and_hold_return_pct": round(buy_hold_return_pct, 2),
                "max_drawdown_pct": round(max_drawdown_pct, 2),
                "sharpe_ratio": sharpe,
                "profit_factor": profit_factor,
            },
            "trades_summary": {
                "total_trades": total_trades,
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate_pct": round(win_rate, 2),
                "avg_trade_pnl": round(total_pnl / total_trades, 2) if total_trades > 0 else 0.0,
            },
            "recent_trades": trades[-10:],
        }

    @classmethod
    def _run_orb_backtest(
        cls,
        df: pd.DataFrame,
        params: Dict[str, Any],
        initial_capital: float = 100000.0,
    ) -> Dict[str, Any]:
        """
        Opening Range Breakout (ORB) intraday backtest.
        Group candles by date, determine opening range from first N bars (default 1 bar of 15min).
        Triggers breakout trade when high > range_high (or low < range_low for short).
        """
        range_bars = int(params.get("range_bars", 1))
        target_multiplier = float(params.get("target_multiplier", 1.5))
        direction = str(params.get("direction", "both")).lower()  # "both", "long_only", "short_only"

        df = df.copy()
        df["date"] = df["timestamp"].dt.date

        capital = initial_capital
        trades: List[Dict[str, Any]] = []
        equity_curve: List[float] = [capital]

        for date, group in df.groupby("date", sort=True):
            group = group.sort_values("timestamp").reset_index(drop=True)
            if len(group) <= range_bars:
                continue

            # 1. Opening range
            opening_slice = group.iloc[:range_bars]
            orb_high = float(opening_slice["high"].max())
            orb_low = float(opening_slice["low"].min())
            range_size = orb_high - orb_low

            if range_size <= 0:
                continue

            pos = 0  # +1 for Long, -1 for Short
            entry_price = 0.0
            entry_time = None
            stop_loss = 0.0
            target = 0.0
            shares = 0

            # 2. Intraday trading loop for the remaining bars of the day
            for i in range(range_bars, len(group)):
                bar = group.iloc[i]
                c_high = float(bar["high"])
                c_low = float(bar["low"])
                c_open = float(bar["open"])
                c_close = float(bar["close"])
                ts = bar["timestamp"]

                # If no position open yet today
                if pos == 0:
                    # Long breakout
                    if direction in ("long_only", "both") and c_high > orb_high:
                        entry_price = max(c_open, orb_high)
                        stop_loss = orb_low
                        target = entry_price + (range_size * target_multiplier) if target_multiplier > 0 else 0.0
                        shares = max(1, math.floor(capital / entry_price))
                        if capital >= shares * entry_price:
                            pos = 1
                            entry_time = ts
                            capital -= shares * entry_price

                    # Short breakout
                    elif direction in ("short_only", "both") and c_low < orb_low:
                        entry_price = min(c_open, orb_low)
                        stop_loss = orb_high
                        target = entry_price - (range_size * target_multiplier) if target_multiplier > 0 else 0.0
                        shares = max(1, math.floor(capital / entry_price))
                        if capital >= shares * entry_price:
                            pos = -1
                            entry_time = ts
                            capital -= shares * entry_price

                # If position active, check exits
                elif pos == 1:
                    is_last_bar = (i == len(group) - 1) or (ts.hour == 15 and ts.minute >= 15)
                    # Check Target
                    if target > 0 and c_high >= target:
                        exit_price = max(c_open, target)
                        exit_reason = "Target Hit"
                    # Check Stop Loss
                    elif c_low <= stop_loss:
                        exit_price = min(c_open, stop_loss)
                        exit_reason = "Stop Loss Hit"
                    # EOD Exit
                    elif is_last_bar:
                        exit_price = c_close
                        exit_reason = "Square-off (EOD)"
                    else:
                        exit_price = None

                    if exit_price is not None:
                        revenue = shares * exit_price
                        capital += revenue
                        pnl = (exit_price - entry_price) * shares
                        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                        trades.append({
                            "date": str(date),
                            "type": "BUY",
                            "entry_time": str(entry_time),
                            "exit_time": str(ts),
                            "entry_price": round(entry_price, 2),
                            "exit_price": round(exit_price, 2),
                            "shares": shares,
                            "pnl": round(pnl, 2),
                            "pnl_pct": round(pnl_pct, 2),
                            "reason": exit_reason,
                        })
                        pos = 0
                        equity_curve.append(capital)
                        break  # Max 1 trade per day

                elif pos == -1:
                    is_last_bar = (i == len(group) - 1) or (ts.hour == 15 and ts.minute >= 15)
                    # Check Target
                    if target > 0 and c_low <= target:
                        exit_price = min(c_open, target)
                        exit_reason = "Target Hit"
                    # Check Stop Loss
                    elif c_high >= stop_loss:
                        exit_price = max(c_open, stop_loss)
                        exit_reason = "Stop Loss Hit"
                    # EOD Exit
                    elif is_last_bar:
                        exit_price = c_close
                        exit_reason = "Square-off (EOD)"
                    else:
                        exit_price = None

                    if exit_price is not None:
                        pnl = (entry_price - exit_price) * shares
                        revenue = (shares * entry_price) + pnl
                        capital += revenue
                        pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                        trades.append({
                            "date": str(date),
                            "type": "SELL (SHORT)",
                            "entry_time": str(entry_time),
                            "exit_time": str(ts),
                            "entry_price": round(entry_price, 2),
                            "exit_price": round(exit_price, 2),
                            "shares": shares,
                            "pnl": round(pnl, 2),
                            "pnl_pct": round(pnl_pct, 2),
                            "reason": exit_reason,
                        })
                        pos = 0
                        equity_curve.append(capital)
                        break  # Max 1 trade per day

            # If still open at end of day, force square-off
            if pos != 0:
                final_bar = group.iloc[-1]
                exit_price = float(final_bar["close"])
                if pos == 1:
                    pnl = (exit_price - entry_price) * shares
                    capital += shares * exit_price
                    trade_type = "BUY"
                else:
                    pnl = (entry_price - exit_price) * shares
                    capital += (shares * entry_price) + pnl
                    trade_type = "SELL (SHORT)"

                pnl_pct = (pnl / (shares * entry_price)) * 100
                trades.append({
                    "date": str(date),
                    "type": trade_type,
                    "entry_time": str(entry_time),
                    "exit_time": str(final_bar["timestamp"]),
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(exit_price, 2),
                    "shares": shares,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "reason": "Force Square-off (EOD)",
                })
                pos = 0
                equity_curve.append(capital)

        # Performance summary
        ending_capital = capital
        total_pnl = ending_capital - initial_capital
        total_return_pct = (total_pnl / initial_capital) * 100

        first_close = df.iloc[0]["close"]
        last_close = df.iloc[-1]["close"]
        buy_hold_return_pct = ((last_close - first_close) / first_close) * 100

        equity_series = pd.Series(equity_curve)
        peak = equity_series.cummax()
        drawdown = (equity_series - peak) / peak
        max_drawdown_pct = abs(float(drawdown.min())) * 100

        total_trades = len(trades)
        winning_trades = [t for t in trades if t["pnl"] > 0]
        losing_trades = [t for t in trades if t["pnl"] <= 0]
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0

        gross_profit = sum(t["pnl"] for t in winning_trades)
        gross_loss = abs(sum(t["pnl"] for t in losing_trades))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        returns = equity_series.pct_change().dropna()
        sharpe = round(float(np.sqrt(252) * (returns.mean() / returns.std())), 2) if (len(returns) > 1 and returns.std() > 0) else 0.0

        return {
            "strategy": "Opening Range Breakout (ORB)",
            "parameters": {
                "range_bars": range_bars,
                "target_multiplier": target_multiplier,
                "direction": direction,
            },
            "period": {
                "start": str(df.iloc[0]["timestamp"]),
                "end": str(df.iloc[-1]["timestamp"]),
                "bars": len(df),
            },
            "performance": {
                "initial_capital": round(initial_capital, 2),
                "ending_capital": round(ending_capital, 2),
                "net_profit": round(total_pnl, 2),
                "total_return_pct": round(total_return_pct, 2),
                "buy_and_hold_return_pct": round(buy_hold_return_pct, 2),
                "max_drawdown_pct": round(max_drawdown_pct, 2),
                "sharpe_ratio": sharpe,
                "profit_factor": profit_factor,
            },
            "trades_summary": {
                "total_trades": total_trades,
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate_pct": round(win_rate, 2),
                "avg_trade_pnl": round(total_pnl / total_trades, 2) if total_trades > 0 else 0.0,
            },
            "recent_trades": trades,
        }

    @classmethod
    def _run_orb_pdh_pdl_backtest(
        cls,
        df: pd.DataFrame,
        params: Dict[str, Any],
        initial_capital: float = 1000000.0,
    ) -> Dict[str, Any]:
        """
        Advanced ORB strategy with PDH/PDL filter, 50% pullback entry,
        and 4-stage target scaling (3R/5R/8R/10R + runner) with Breakeven/Trailing stops.
        """
        risk_pct = float(params.get("risk_pct", 0.01))
        lot_size = int(params.get("lot_size", 25))
        option_delta = float(params.get("option_delta", 0.5))

        df = df.copy()
        df["date"] = df["timestamp"].dt.date
        unique_dates = sorted(df["date"].unique())

        account_capital = initial_capital
        risk_amount = initial_capital * risk_pct
        trades = []
        daily_stats = []
        equity_curve = [{"timestamp": str(df.iloc[0]["timestamp"]), "equity": account_capital}]

        for day_idx in range(1, len(unique_dates)):
            prev_date = unique_dates[day_idx - 1]
            curr_date = unique_dates[day_idx]

            prev_day_bars = df[df["date"] == prev_date]
            curr_day_bars = df[df["date"] == curr_date].sort_values("timestamp").reset_index(drop=True)

            if curr_day_bars.empty or prev_day_bars.empty:
                continue

            pdh = float(prev_day_bars["high"].max())
            pdl = float(prev_day_bars["low"].min())

            # 1. Setup: First 15-minute candle
            first_bar = curr_day_bars.iloc[0]
            or_high = float(first_bar["high"])
            or_low = float(first_bar["low"])

            # 2. Filter: Break either PDH or PDL
            breaks_pdh = or_high > pdh
            breaks_pdl = or_low < pdl

            if not (breaks_pdh or breaks_pdl):
                daily_stats.append({
                    "date": str(curr_date),
                    "status": "SKIPPED_INSIDE_DAY",
                    "reason": "First 15m candle inside PDH-PDL range"
                })
                continue

            filter_reason = "Broke PDH" if breaks_pdh else "Broke PDL"

            # 3. Entry & Stop Loss (09:30 AM – 01:30 PM)
            trade_state = "SCANNING_BREAKOUT"
            pos_type = None
            entry_time = None
            actual_entry_price = None
            breakout_type = None
            breakout_candle = None
            pullback_price = None
            stop_loss = None
            risk_R = None

            total_lots = 0
            rem_lots = 0
            current_sl = None
            peak_gain_R = 0.0
            trade_legs = []

            for i in range(1, len(curr_day_bars)):
                bar = curr_day_bars.iloc[i]
                ts = bar["timestamp"]
                b_open = float(bar["open"])
                b_high = float(bar["high"])
                b_low = float(bar["low"])
                b_close = float(bar["close"])

                is_entry_cutoff = ts.hour > 13 or (ts.hour == 13 and ts.minute > 30)
                is_hard_exit = ts.hour > 14 or (ts.hour == 14 and ts.minute >= 55)

                if trade_state == "SCANNING_BREAKOUT":
                    if is_entry_cutoff:
                        trade_state = "NO_TRADE"
                        break

                    if b_close > or_high:
                        breakout_type = "CE"
                        breakout_candle = bar
                        pullback_price = (breakout_candle["high"] + breakout_candle["low"]) / 2.0
                        stop_loss = float(breakout_candle["low"])
                        risk_R = pullback_price - stop_loss
                        if risk_R > 0:
                            trade_state = "WAITING_PULLBACK"
                        continue

                    elif b_close < or_low:
                        breakout_type = "PE"
                        breakout_candle = bar
                        pullback_price = (breakout_candle["high"] + breakout_candle["low"]) / 2.0
                        stop_loss = float(breakout_candle["high"])
                        risk_R = stop_loss - pullback_price
                        if risk_R > 0:
                            trade_state = "WAITING_PULLBACK"
                        continue

                elif trade_state == "WAITING_PULLBACK":
                    if is_entry_cutoff:
                        trade_state = "NO_TRADE"
                        break

                    if breakout_type == "CE":
                        if b_low < stop_loss:
                            trade_state = "INVALIDATED"
                            break

                        if b_low <= pullback_price:
                            trade_state = "IN_TRADE"
                            pos_type = "CE"
                            entry_time = ts
                            actual_entry_price = pullback_price
                            current_sl = stop_loss

                            option_risk_per_unit = option_delta * risk_R
                            risk_per_lot = option_risk_per_unit * lot_size
                            total_lots = max(10, math.floor(risk_amount / risk_per_lot))
                            rem_lots = total_lots

                            lot_t1 = max(1, round(total_lots * 0.30))
                            lot_t2 = max(1, round(total_lots * 0.30))
                            lot_t3 = max(1, round(total_lots * 0.20))
                            lot_t4 = max(1, round(total_lots * 0.10))
                            lot_runner = max(1, total_lots - (lot_t1 + lot_t2 + lot_t3 + lot_t4))

                            t1_price = actual_entry_price + (3 * risk_R)
                            t2_price = actual_entry_price + (5 * risk_R)
                            t3_price = actual_entry_price + (8 * risk_R)
                            t4_price = actual_entry_price + (10 * risk_R)

                            t1_hit = False
                            t2_hit = False
                            t3_hit = False
                            t4_hit = False

                    elif breakout_type == "PE":
                        if b_high > stop_loss:
                            trade_state = "INVALIDATED"
                            break

                        if b_high >= pullback_price:
                            trade_state = "IN_TRADE"
                            pos_type = "PE"
                            entry_time = ts
                            actual_entry_price = pullback_price
                            current_sl = stop_loss

                            option_risk_per_unit = option_delta * risk_R
                            risk_per_lot = option_risk_per_unit * lot_size
                            total_lots = max(10, math.floor(risk_amount / risk_per_lot))
                            rem_lots = total_lots

                            lot_t1 = max(1, round(total_lots * 0.30))
                            lot_t2 = max(1, round(total_lots * 0.30))
                            lot_t3 = max(1, round(total_lots * 0.20))
                            lot_t4 = max(1, round(total_lots * 0.10))
                            lot_runner = max(1, total_lots - (lot_t1 + lot_t2 + lot_t3 + lot_t4))

                            t1_price = actual_entry_price - (3 * risk_R)
                            t2_price = actual_entry_price - (5 * risk_R)
                            t3_price = actual_entry_price - (8 * risk_R)
                            t4_price = actual_entry_price - (10 * risk_R)

                            t1_hit = False
                            t2_hit = False
                            t3_hit = False
                            t4_hit = False

                elif trade_state == "IN_TRADE":
                    if is_hard_exit:
                        exit_price = b_close
                        gain_pts = (exit_price - actual_entry_price) if pos_type == "CE" else (actual_entry_price - exit_price)
                        gain_R = gain_pts / risk_R
                        pnl_rupees = gain_R * (risk_amount * (rem_lots / total_lots))
                        trade_legs.append({
                            "exit_time": str(ts),
                            "lots": rem_lots,
                            "exit_price": round(exit_price, 2),
                            "gain_R": round(gain_R, 2),
                            "pnl_rupees": round(pnl_rupees, 2),
                            "reason": "Hard Exit (2:55 PM)"
                        })
                        rem_lots = 0
                        trade_state = "EXITED"
                        break

                    if pos_type == "CE":
                        if b_low <= current_sl:
                            exit_price = current_sl
                            gain_pts = exit_price - actual_entry_price
                            gain_R = gain_pts / risk_R
                            pnl_rupees = gain_R * (risk_amount * (rem_lots / total_lots))
                            reason = "Stop Loss Hit" if current_sl == stop_loss else ("Breakeven SL Hit" if current_sl == actual_entry_price else f"Trailing SL Hit ({round(gain_R, 1)}R)")
                            trade_legs.append({
                                "exit_time": str(ts),
                                "lots": rem_lots,
                                "exit_price": round(exit_price, 2),
                                "gain_R": round(gain_R, 2),
                                "pnl_rupees": round(pnl_rupees, 2),
                                "reason": reason
                            })
                            rem_lots = 0
                            trade_state = "EXITED"
                            break

                        if not t1_hit and b_high >= t1_price and rem_lots > 0:
                            t1_hit = True
                            pnl_rupees = 3.0 * (risk_amount * (lot_t1 / total_lots))
                            trade_legs.append({
                                "exit_time": str(ts),
                                "lots": lot_t1,
                                "exit_price": round(t1_price, 2),
                                "gain_R": 3.0,
                                "pnl_rupees": round(pnl_rupees, 2),
                                "reason": "Target 1 (+3R) Hit"
                            })
                            rem_lots -= lot_t1
                            current_sl = actual_entry_price

                        if t1_hit and not t2_hit and b_high >= t2_price and rem_lots > 0:
                            t2_hit = True
                            pnl_rupees = 5.0 * (risk_amount * (lot_t2 / total_lots))
                            trade_legs.append({
                                "exit_time": str(ts),
                                "lots": lot_t2,
                                "exit_price": round(t2_price, 2),
                                "gain_R": 5.0,
                                "pnl_rupees": round(pnl_rupees, 2),
                                "reason": "Target 2 (+5R) Hit"
                            })
                            rem_lots -= lot_t2
                            current_sl = actual_entry_price + (3 * risk_R)

                        if t2_hit and not t3_hit and b_high >= t3_price and rem_lots > 0:
                            t3_hit = True
                            pnl_rupees = 8.0 * (risk_amount * (lot_t3 / total_lots))
                            trade_legs.append({
                                "exit_time": str(ts),
                                "lots": lot_t3,
                                "exit_price": round(t3_price, 2),
                                "gain_R": 8.0,
                                "pnl_rupees": round(pnl_rupees, 2),
                                "reason": "Target 3 (+8R) Hit"
                            })
                            rem_lots -= lot_t3
                            current_sl = actual_entry_price + (5 * risk_R)

                        if t3_hit and not t4_hit and b_high >= t4_price and rem_lots > 0:
                            t4_hit = True
                            pnl_rupees = 10.0 * (risk_amount * (lot_t4 / total_lots))
                            trade_legs.append({
                                "exit_time": str(ts),
                                "lots": lot_t4,
                                "exit_price": round(t4_price, 2),
                                "gain_R": 10.0,
                                "pnl_rupees": round(pnl_rupees, 2),
                                "reason": "Target 4 (+10R) Hit"
                            })
                            rem_lots -= lot_t4

                        curr_gain_R = (b_high - actual_entry_price) / risk_R
                        if t4_hit and curr_gain_R > peak_gain_R:
                            peak_gain_R = curr_gain_R
                            trail_R = peak_gain_R * 0.50
                            trail_sl = actual_entry_price + (trail_R * risk_R)
                            if trail_sl > current_sl:
                                current_sl = trail_sl

                    elif pos_type == "PE":
                        if b_high >= current_sl:
                            exit_price = current_sl
                            gain_pts = actual_entry_price - exit_price
                            gain_R = gain_pts / risk_R
                            pnl_rupees = gain_R * (risk_amount * (rem_lots / total_lots))
                            reason = "Stop Loss Hit" if current_sl == stop_loss else ("Breakeven SL Hit" if current_sl == actual_entry_price else f"Trailing SL Hit ({round(gain_R, 1)}R)")
                            trade_legs.append({
                                "exit_time": str(ts),
                                "lots": rem_lots,
                                "exit_price": round(exit_price, 2),
                                "gain_R": round(gain_R, 2),
                                "pnl_rupees": round(pnl_rupees, 2),
                                "reason": reason
                            })
                            rem_lots = 0
                            trade_state = "EXITED"
                            break

                        if not t1_hit and b_low <= t1_price and rem_lots > 0:
                            t1_hit = True
                            pnl_rupees = 3.0 * (risk_amount * (lot_t1 / total_lots))
                            trade_legs.append({
                                "exit_time": str(ts),
                                "lots": lot_t1,
                                "exit_price": round(t1_price, 2),
                                "gain_R": 3.0,
                                "pnl_rupees": round(pnl_rupees, 2),
                                "reason": "Target 1 (+3R) Hit"
                            })
                            rem_lots -= lot_t1
                            current_sl = actual_entry_price

                        if t1_hit and not t2_hit and b_low <= t2_price and rem_lots > 0:
                            t2_hit = True
                            pnl_rupees = 5.0 * (risk_amount * (lot_t2 / total_lots))
                            trade_legs.append({
                                "exit_time": str(ts),
                                "lots": lot_t2,
                                "exit_price": round(t2_price, 2),
                                "gain_R": 5.0,
                                "pnl_rupees": round(pnl_rupees, 2),
                                "reason": "Target 2 (+5R) Hit"
                            })
                            rem_lots -= lot_t2
                            current_sl = actual_entry_price - (3 * risk_R)

                        if t2_hit and not t3_hit and b_low <= t3_price and rem_lots > 0:
                            t3_hit = True
                            pnl_rupees = 8.0 * (risk_amount * (lot_t3 / total_lots))
                            trade_legs.append({
                                "exit_time": str(ts),
                                "lots": lot_t3,
                                "exit_price": round(t3_price, 2),
                                "gain_R": 8.0,
                                "pnl_rupees": round(pnl_rupees, 2),
                                "reason": "Target 3 (+8R) Hit"
                            })
                            rem_lots -= lot_t3
                            current_sl = actual_entry_price - (5 * risk_R)

                        if t3_hit and not t4_hit and b_low <= t4_price and rem_lots > 0:
                            t4_hit = True
                            pnl_rupees = 10.0 * (risk_amount * (lot_t4 / total_lots))
                            trade_legs.append({
                                "exit_time": str(ts),
                                "lots": lot_t4,
                                "exit_price": round(t4_price, 2),
                                "gain_R": 10.0,
                                "pnl_rupees": round(pnl_rupees, 2),
                                "reason": "Target 4 (+10R) Hit"
                            })
                            rem_lots -= lot_t4

                        curr_gain_R = (actual_entry_price - b_low) / risk_R
                        if t4_hit and curr_gain_R > peak_gain_R:
                            peak_gain_R = curr_gain_R
                            trail_R = peak_gain_R * 0.50
                            trail_sl = actual_entry_price - (trail_R * risk_R)
                            if trail_sl < current_sl:
                                current_sl = trail_sl

            if trade_legs:
                total_trade_pnl = sum(leg["pnl_rupees"] for leg in trade_legs)
                account_capital += total_trade_pnl
                trades.append({
                    "date": str(curr_date),
                    "type": pos_type,
                    "filter": filter_reason,
                    "pdh": pdh,
                    "pdl": pdl,
                    "or_high": or_high,
                    "or_low": or_low,
                    "entry_time": str(entry_time),
                    "entry_price": round(actual_entry_price, 2),
                    "initial_sl": round(stop_loss, 2),
                    "risk_points": round(risk_R, 2),
                    "total_lots": total_lots,
                    "legs": trade_legs,
                    "total_pnl": round(total_trade_pnl, 2),
                    "account_capital": round(account_capital, 2),
                })
                equity_curve.append({"timestamp": str(curr_date), "equity": account_capital})

        total_trades = len(trades)
        winning_trades = [t for t in trades if t["total_pnl"] > 0]
        losing_trades = [t for t in trades if t["total_pnl"] < 0]
        net_profit = account_capital - initial_capital
        total_return_pct = (net_profit / initial_capital) * 100

        gross_profit = sum(t["total_pnl"] for t in winning_trades)
        gross_loss = abs(sum(t["total_pnl"] for t in losing_trades))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        eq_series = pd.Series([e["equity"] for e in equity_curve])
        peak = eq_series.cummax()
        dd = (eq_series - peak) / peak
        max_dd_pct = abs(float(dd.min())) * 100

        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0

        returns = eq_series.pct_change().dropna()
        sharpe = round(float(np.sqrt(252) * (returns.mean() / returns.std())), 2) if (len(returns) > 1 and returns.std() > 0) else 0.0

        return {
            "strategy": "ORB with PDH/PDL Filter & Partial Scaling (3R/5R/8R/10R)",
            "parameters": params,
            "period": {
                "start": str(unique_dates[1]),
                "end": str(unique_dates[-1]),
                "total_trading_days": len(unique_dates) - 1,
                "days_traded": total_trades,
                "days_skipped_inside": len([d for d in daily_stats if d.get("status") == "SKIPPED_INSIDE_DAY"]),
            },
            "performance": {
                "initial_capital": round(initial_capital, 2),
                "ending_capital": round(account_capital, 2),
                "net_profit": round(net_profit, 2),
                "total_return_pct": round(total_return_pct, 2),
                "max_drawdown_pct": round(max_dd_pct, 2),
                "sharpe_ratio": sharpe,
                "profit_factor": profit_factor,
            },
            "trades_summary": {
                "total_trades": total_trades,
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate_pct": round(win_rate, 2),
                "avg_trade_pnl": round(net_profit / total_trades, 2) if total_trades > 0 else 0.0,
                "largest_win": round(max([t["total_pnl"] for t in trades]), 2) if trades else 0.0,
                "largest_loss": round(min([t["total_pnl"] for t in trades]), 2) if trades else 0.0,
            },
            "recent_trades": trades,
        }
