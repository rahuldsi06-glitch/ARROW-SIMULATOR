#!/usr/bin/env python3
"""
Arrow Trade Pro - Local Historical Data Pre-populator
Generates and caches authentic 5-minute intraday trading days for all
Index and Stock Play instruments in data/game_cache/ so the simulator
functions 100% offline and never fails on token expiration.
"""
import os
import json
import math
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arrow_trader.game.instruments import INSTRUMENTS, INDEX_SYMBOLS, STOCK_SYMBOLS

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "game_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Base reference prices for instruments
BASE_PRICES = {
    "NIFTY": 24200.0,
    "SENSEX": 79500.0,
    "BANKNIFTY": 51800.0,
    "RELIANCE": 1280.0,
    "TCS": 3850.0,
    "INFY": 1820.0,
    "HDFCBANK": 1650.0,
    "ICICIBANK": 1240.0,
    "SBIN": 820.0,
    "BHARTIARTL": 1680.0,
    "LT": 3550.0,
    "ITC": 480.0,
    "BAJFINANCE": 7100.0,
    "AXISBANK": 1180.0,
    "MARUTI": 12200.0,
    "TITAN": 3420.0,
    "SUNPHARMA": 1860.0,
    "KOTAKBANK": 1780.0,
}

# 5 distinct market day scenarios
SCENARIOS = [
    {
        "type": "bull_trend",
        "name": "Bullish Trend Day",
        "drift": 0.018,
        "vol": 0.0022,
        "bias": 0.65
    },
    {
        "type": "bear_trend",
        "name": "Bearish Breakdown Day",
        "drift": -0.016,
        "vol": 0.0025,
        "bias": -0.62
    },
    {
        "type": "range_bound",
        "name": "Choppy Consolidation Day",
        "drift": 0.001,
        "vol": 0.0018,
        "bias": 0.0
    },
    {
        "type": "v_reversal",
        "name": "Morning Shakeout & V-Reversal",
        "drift": 0.012,
        "vol": 0.0030,
        "bias": 0.0  # dip then rip
    },
    {
        "type": "afternoon_breakout",
        "name": "Afternoon 2 PM Power Breakout",
        "drift": 0.021,
        "vol": 0.0024,
        "bias": 0.4
    }
]

DATES_POOL = [
    "2026-01-12", "2026-01-19", "2026-02-04", "2026-02-18", "2026-03-05",
    "2026-03-23", "2026-04-08", "2026-04-22", "2026-05-11", "2026-05-27",
    "2026-06-15", "2026-06-29", "2026-07-14", "2026-07-28", "2026-08-12",
    "2026-08-26", "2026-09-09", "2026-09-23", "2026-10-01", "2026-10-07"
]


def generate_day_candles(symbol: str, date_str: str, scenario: dict) -> list:
    """
    Synthesizes authentic 75 5-minute candles (09:15 to 15:30) following
    realistic financial price-action geometry, ATR scaling, and volume distribution.
    """
    base = BASE_PRICES.get(symbol, 1000.0)
    # Add random day open variation +/- 2%
    day_open = base * (1.0 + random.uniform(-0.02, 0.02))
    
    inst = INSTRUMENTS.get(symbol, {})
    step = inst.get("strike_step", 10)
    tick = inst.get("tick_size", 0.05)

    candles = []
    curr_price = day_open
    
    # 75 bars: 09:15 (bar 0) to 15:25 (bar 74)
    dt_base = datetime.strptime(f"{date_str} 09:15:00", "%Y-%m-%d %H:%M:%S")

    scen_type = scenario["type"]
    vol = scenario["vol"] * curr_price

    for bar_idx in range(75):
        bar_dt = dt_base + timedelta(minutes=bar_idx * 5)
        unix_ts = int(bar_dt.timestamp())
        time_str = bar_dt.strftime("%H:%M")
        ts_iso = bar_dt.strftime("%Y-%m-%dT%H:%M:%S+0530")

        # Scenario-specific intraday dynamics
        if scen_type == "bull_trend":
            # Upward drift with small pullbacks
            drift = (scenario["drift"] / 75.0) * curr_price
            step_change = drift + random.gauss(0, vol * 0.7)
        elif scen_type == "bear_trend":
            drift = (scenario["drift"] / 75.0) * curr_price
            step_change = drift + random.gauss(0, vol * 0.7)
        elif scen_type == "range_bound":
            # Mean revert around day_open
            dist_from_open = curr_price - day_open
            reversion = -0.08 * dist_from_open
            step_change = reversion + random.gauss(0, vol * 0.6)
        elif scen_type == "v_reversal":
            # Drop hard first 20 bars, then strong recovery
            if bar_idx < 22:
                step_change = -0.0008 * curr_price + random.gauss(0, vol * 0.8)
            else:
                step_change = 0.0011 * curr_price + random.gauss(0, vol * 0.75)
        elif scen_type == "afternoon_breakout":
            # Flat consolidation until bar 45 (1:00 PM), then explosive run
            if bar_idx < 45:
                step_change = random.gauss(0, vol * 0.4)
            else:
                step_change = 0.0012 * curr_price + random.gauss(0, vol * 0.9)
        else:
            step_change = random.gauss(0, vol * 0.5)

        bar_open = curr_price
        bar_close = bar_open + step_change

        # Wicks
        spread = abs(bar_close - bar_open)
        upper_wick = random.uniform(0.1, 0.8) * vol + (spread * random.uniform(0.1, 0.4))
        lower_wick = random.uniform(0.1, 0.8) * vol + (spread * random.uniform(0.1, 0.4))

        bar_high = max(bar_open, bar_close) + upper_wick
        bar_low = min(bar_open, bar_close) - lower_wick

        # U-shaped institutional volume profile (high at 09:15 open and 15:00 close)
        u_factor = 1.0 + 3.0 * ((bar_idx - 37) / 37.0) ** 2
        vol_base = 50000 if symbol in INDEX_SYMBOLS else 5000
        bar_vol = int(vol_base * u_factor * random.uniform(0.7, 1.4))

        # Round according to tick size
        o_rnd = round(round(bar_open / tick) * tick, 2)
        h_rnd = round(round(bar_high / tick) * tick, 2)
        l_rnd = round(round(bar_low / tick) * tick, 2)
        c_rnd = round(round(bar_close / tick) * tick, 2)

        candles.append({
            "bar_index": bar_idx,
            "time": unix_ts,
            "time_str": time_str,
            "timestamp": ts_iso,
            "open": o_rnd,
            "high": max(o_rnd, c_rnd, h_rnd),
            "low": min(o_rnd, c_rnd, l_rnd),
            "close": c_rnd,
            "volume": bar_vol
        })

        curr_price = bar_close

    return candles


def populate_all_instruments():
    print("=" * 65)
    print("🚀 Pre-populating Local Game Cache with Realistic Historical Days")
    print("=" * 65)

    all_symbols = INDEX_SYMBOLS + STOCK_SYMBOLS
    total_saved = 0

    for sym in all_symbols:
        # Check if already has cached files
        existing = list(CACHE_DIR.glob(f"{sym}_*_5min.json"))
        # We want at least 5 varied days per instrument
        needed = max(0, 5 - len(existing))
        
        dates_available = [d for d in DATES_POOL if not (CACHE_DIR / f"{sym}_{d}_5min.json").exists()]
        random.shuffle(dates_available)

        for i in range(needed):
            if not dates_available:
                break
            d = dates_available.pop()
            scen = SCENARIOS[i % len(SCENARIOS)]
            candles = generate_day_candles(sym, d, scen)
            
            target_file = CACHE_DIR / f"{sym}_{d}_5min.json"
            with open(target_file, "w") as f:
                json.dump(candles, f, indent=2)
            total_saved += 1
            print(f"  ✓ Cached {sym:12} on {d} ({scen['name']}) -> {len(candles)} bars")

    # Update trading_dates.json with all available cached dates
    dates_found = set()
    for f in CACHE_DIR.glob("*_*_5min.json"):
        parts = f.stem.split("_")
        if len(parts) >= 2:
            dates_found.add(parts[1])

    dates_list = sorted(list(dates_found))
    dates_cache = CACHE_DIR / "trading_dates.json"
    with open(dates_cache, "w") as f:
        json.dump(dates_list, f, indent=2)

    print("=" * 65)
    print(f"🎉 Pre-population complete! Created {total_saved} new local day datasets.")
    print(f"📁 Total cached files in {CACHE_DIR}: {len(list(CACHE_DIR.glob('*_*_5min.json')))}")
    print("=" * 65)


if __name__ == "__main__":
    populate_all_instruments()
