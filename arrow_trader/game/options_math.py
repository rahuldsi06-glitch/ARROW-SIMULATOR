from __future__ import annotations
import math
from typing import Dict, Any, Tuple


def norm_cdf(x: float) -> float:
    """Cumulative distribution function for standard normal distribution."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x: float) -> float:
    """Probability density function for standard normal distribution."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def calculate_time_to_expiry(
    bar_index: int,
    total_bars: int = 75,
    expiry_type: str = "weekly",
    day_of_week: int = 3  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri
) -> float:
    """
    Calculate annualized time to expiry (T in years) based on:
    - Current bar index (0 to 74 representing 09:15 to 15:30)
    - Expiry type: 'weekly', 'next_weekly', 'monthly'
    
    Returns T in years (trading days basis: 252 days/year, 375 minutes/day).
    """
    bars_remaining = max(1, total_bars - bar_index)
    fraction_of_day = bars_remaining / float(total_bars)
    
    if expiry_type.lower() == "weekly":
        # Simulate realistic 1 to 4 days remaining for current week
        days_to_expiry = max(0.1, 2.0) + fraction_of_day
    elif expiry_type.lower() in ("next_weekly", "next"):
        days_to_expiry = 7.0 + fraction_of_day
    elif expiry_type.lower() == "monthly":
        days_to_expiry = 20.0 + fraction_of_day
    else:
        days_to_expiry = 3.0 + fraction_of_day

    return max(0.0005, days_to_expiry / 252.0)


def black_scholes_price(
    spot: float,
    strike: float,
    t_years: float,
    r: float = 0.07,
    iv: float = 0.15,
    option_type: str = "CE"
) -> Dict[str, float]:
    """
    Black-Scholes-Merton option pricing formula with Greeks.
    Prices and returns are in Rupees.
    """
    S = float(spot)
    K = float(strike)
    T = max(0.0001, float(t_years))
    r = float(r)
    sigma = max(0.01, float(iv))
    is_call = option_type.upper() in ("CE", "CALL")

    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    if is_call:
        price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        delta = norm_cdf(d1)
        theta_annual = (
            -(S * norm_pdf(d1) * sigma) / (2.0 * sqrt_T)
            - r * K * math.exp(-r * T) * norm_cdf(d2)
        )
    else:
        price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
        delta = norm_cdf(d1) - 1.0
        theta_annual = (
            -(S * norm_pdf(d1) * sigma) / (2.0 * sqrt_T)
            + r * K * math.exp(-r * T) * norm_cdf(-d2)
        )

    gamma = norm_pdf(d1) / (S * sigma * sqrt_T)
    vega = (S * sqrt_T * norm_pdf(d1)) / 100.0  # per 1% change in IV
    theta_day = theta_annual / 252.0  # daily theta decay in Rupees

    # Minimum tick rule: options trade at least 0.05
    price = max(0.05, round(price, 2))
    intrinsic = max(0.0, (S - K) if is_call else (K - S))
    time_value = max(0.05, round(price - intrinsic, 2))

    return {
        "price": price,
        "delta": round(delta, 3),
        "gamma": round(gamma, 5),
        "theta": round(theta_day, 2),
        "vega": round(vega, 2),
        "intrinsic": round(intrinsic, 2),
        "time_value": round(time_value, 2)
    }


def estimate_option_bar_extremes(
    candle_open: float,
    candle_high: float,
    candle_low: float,
    candle_close: float,
    strike: float,
    t_years: float,
    r: float = 0.07,
    iv: float = 0.15,
    option_type: str = "CE"
) -> Dict[str, float]:
    """
    Computes theoretical option OHLC prices for a 5-minute candle.
    For a Call:
      - highest option price occurs at candle_high
      - lowest option price occurs at candle_low
    For a Put:
      - highest option price occurs at candle_low
      - lowest option price occurs at candle_high
    """
    is_call = option_type.upper() in ("CE", "CALL")
    
    open_opt = black_scholes_price(candle_open, strike, t_years, r, iv, option_type)["price"]
    close_opt = black_scholes_price(candle_close, strike, t_years, r, iv, option_type)["price"]
    
    if is_call:
        high_opt = black_scholes_price(candle_high, strike, t_years, r, iv, option_type)["price"]
        low_opt = black_scholes_price(candle_low, strike, t_years, r, iv, option_type)["price"]
    else:
        high_opt = black_scholes_price(candle_low, strike, t_years, r, iv, option_type)["price"]
        low_opt = black_scholes_price(candle_high, strike, t_years, r, iv, option_type)["price"]

    return {
        "open": open_opt,
        "high": max(open_opt, close_opt, high_opt),
        "low": min(open_opt, close_opt, low_opt),
        "close": close_opt
    }


def calculate_ema(values: list[float], period: int) -> list[float]:
    """Calculate Exponential Moving Average for a series of values."""
    if not values:
        return []
    k = 2.0 / (period + 1)
    res = [values[0]]
    val = values[0]
    for v in values[1:]:
        val = v * k + val * (1.0 - k)
        res.append(round(val, 2))
    return res


def calculate_sma(values: list[float], period: int) -> list[float]:
    """Calculate Simple Moving Average with cumulative warmup."""
    if not values:
        return []
    res = []
    rolling_sum = 0.0
    for i, v in enumerate(values):
        rolling_sum += v
        if i < period:
            res.append(round(rolling_sum / (i + 1), 2))
        else:
            rolling_sum -= values[i - period]
            res.append(round(rolling_sum / period, 2))
    return res


def calculate_supertrend(
    candles: list[dict[str, Any]],
    period: int = 10,
    multiplier: float = 3.0
) -> dict[str, Any]:
    """
    Calculate authentic Supertrend indicator (ATR period 10, multiplier 3.0).
    Returns supertrend values, upper bands, lower bands, and trend directions (1=Bull, -1=Bear).
    """
    if not candles:
        return {"supertrend": [], "trend": []}

    n = len(candles)
    tr = []
    for i in range(n):
        h = candles[i]["high"]
        l = candles[i]["low"]
        prev_close = candles[i - 1]["close"] if i > 0 else candles[i]["open"]
        tr_val = max(h - l, abs(h - prev_close), abs(l - prev_close))
        tr.append(tr_val)

    # Wilder's Smoothing for ATR
    atr = []
    sum_tr = 0.0
    for i in range(min(period, n)):
        sum_tr += tr[i]
        atr.append(sum_tr / (i + 1))
    for i in range(period, n):
        cur_atr = (atr[i - 1] * (period - 1) + tr[i]) / period
        atr.append(cur_atr)

    prev_final_up = 0.0
    prev_final_down = 0.0
    trend = 1
    supertrend_vals = []
    trend_vals = []

    for i in range(n):
        c = candles[i]
        hl2 = (c["high"] + c["low"]) / 2.0
        cur_atr = atr[i] if i < len(atr) else (c["high"] - c["low"])
        basic_up = hl2 + multiplier * cur_atr
        basic_down = hl2 - multiplier * cur_atr

        final_up = basic_up
        final_down = basic_down
        if i > 0:
            final_up = basic_up if (basic_up < prev_final_up or candles[i - 1]["close"] > prev_final_up) else prev_final_up
            final_down = basic_down if (basic_down > prev_final_down or candles[i - 1]["close"] < prev_final_down) else prev_final_down

        if trend == 1:
            if c["close"] < final_down:
                trend = -1
                st = final_up
            else:
                trend = 1
                st = final_down
        else:
            if c["close"] > final_up:
                trend = 1
                st = final_down
            else:
                trend = -1
                st = final_up

        prev_final_up = final_up
        prev_final_down = final_down
        supertrend_vals.append(round(st, 2))
        trend_vals.append(trend)

    return {
        "supertrend": supertrend_vals,
        "trend": trend_vals,
        "atr": [round(a, 2) for a in atr]
    }


def calculate_fibonacci_levels(
    anchor1: float,
    anchor2: float,
    custom_ratios: list[float] | None = None
) -> dict[str, float]:
    """Calculate Fibonacci retracement levels between two price anchors."""
    ratios = custom_ratios or [0.0, 0.236, 0.382, 0.500, 0.618, 0.786, 1.000, 1.618]
    diff = anchor2 - anchor1
    return {f"{r:.3f}": round(anchor1 + diff * r, 2) for r in ratios}

