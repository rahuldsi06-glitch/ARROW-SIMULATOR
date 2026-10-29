from __future__ import annotations
import os
import json
import random
import uuid
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .instruments import (
    INSTRUMENTS,
    INDEX_SYMBOLS,
    STOCK_SYMBOLS,
    US_FUTURES_SYMBOLS,
    get_instrument_config
)
from .options_math import black_scholes_price, calculate_time_to_expiry, estimate_option_bar_extremes
from ..market import MarketService

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "game_cache"
if not CACHE_DIR.exists():
    CACHE_DIR = Path.cwd() / "data" / "game_cache"
try:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
DATES_CACHE_FILE = CACHE_DIR / "trading_dates.json"
GAME_STATE_FILE = CACHE_DIR / "game_state.json"

# Base reference prices for realistic local simulation fallbacks
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
    # US CME Micro & Mini Futures
    "MES": 5860.0,
    "MNQ": 20650.0,
    "ES": 5860.0,
    "NQ": 20650.0,
}


class SimulatorService:
    """
    High-performance game simulator service connecting Arrow Trade historical
    market data to interactive gamified trading sessions.
    
    Resilient offline architecture:
    Prioritizes local disk cache in data/game_cache/. Falls back to local datasets
    gracefully if broker token expires, ensuring 100% uninterrupted gameplay.
    """

    def __init__(self, market_service: Optional[MarketService] = None):
        self.market = market_service or MarketService()
        self._trading_dates: List[str] = []

    def get_available_local_days(self, symbol: str) -> List[str]:
        """Returns list of all dates saved on local disk for a given symbol."""
        sym_clean = symbol.strip().upper()
        pattern = f"{sym_clean}_*_5min.json"
        found = []
        for p in CACHE_DIR.glob(pattern):
            parts = p.stem.split("_")
            if len(parts) >= 3 and parts[0] == sym_clean:
                # parts: [SYMBOL, DATE, "5min"]
                found.append(parts[1])
        found.sort()
        return found

    def get_trading_dates(self, force_refresh: bool = False) -> List[str]:
        """
        Retrieves list of valid historical trading dates (YYYY-MM-DD).
        Prioritizes locally saved trading dates.
        """
        if not force_refresh and DATES_CACHE_FILE.exists():
            try:
                with open(DATES_CACHE_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        self._trading_dates = data
                        return self._trading_dates
            except Exception:
                pass

        # Check all locally cached 5min files to build dates list
        local_dates = set()
        for f in CACHE_DIR.glob("*_*_5min.json"):
            parts = f.stem.split("_")
            if len(parts) >= 2:
                local_dates.add(parts[1])

        if local_dates:
            self._trading_dates = sorted(list(local_dates))
            try:
                with open(DATES_CACHE_FILE, "w") as f:
                    json.dump(self._trading_dates, f, indent=2)
            except Exception:
                pass
            return self._trading_dates

        # Fallback date pool
        fallback_dates = [
            "2026-01-12", "2026-01-19", "2026-02-04", "2026-02-18", "2026-03-05",
            "2026-03-23", "2026-04-08", "2026-04-22", "2026-05-11", "2026-05-27",
            "2026-06-15", "2026-06-29", "2026-07-14", "2026-07-28", "2026-08-12",
            "2026-08-26", "2026-09-09", "2026-09-23", "2026-10-01", "2026-10-07"
        ]
        self._trading_dates = fallback_dates
        return self._trading_dates

    def get_us_trading_dates(self) -> List[str]:
        """
        Returns a rich list of valid US market weekdays (Mon-Fri) across 2025-2026,
        excluding standard CME/NYSE trading holidays.
        """
        holidays = {
            "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26", "2025-06-19",
            "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
            "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19",
            "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25"
        }
        dates = []
        start_dt = datetime(2025, 1, 6)
        end_dt = datetime(2026, 10, 23)
        curr = start_dt
        while curr <= end_dt:
            if curr.weekday() < 5:  # Monday to Friday
                d_str = curr.strftime("%Y-%m-%d")
                if d_str not in holidays:
                    dates.append(d_str)
            curr += timedelta(days=1)
        return dates

    def parse_iso_timestamp(self, ts_str: str) -> int:
        """Parse Arrow ISO timestamp into Unix seconds timestamp."""
        clean = str(ts_str)
        if len(clean) >= 24 and clean[-5] in ("+", "-") and clean[-3] != ":":
            clean = clean[:-2] + ":" + clean[-2:]
        try:
            dt = datetime.fromisoformat(clean)
            return int(dt.timestamp())
        except Exception:
            return int(datetime.utcnow().timestamp())

    def _generate_synthetic_day(self, symbol: str, date_str: str) -> List[Dict[str, Any]]:
        """
        Synthesizes an authentic 75 5-minute candle session for a symbol
        with realistic volatility, ATR-based price action, and volume profile.
        Supports both Indian Equity/Indices (09:15-15:30 IST) and US Futures (09:30-15:45 EDT).
        """
        inst = get_instrument_config(symbol)
        is_us = inst.get("market") == "US"
        tick = inst.get("tick_size", 0.25 if is_us else 0.05)
        base = BASE_PRICES.get(symbol, 5000.0 if is_us else 1000.0)
        day_open = base * (1.0 + random.uniform(-0.012, 0.012))

        # 5 distinct market archetypes: bull trend, bear breakdown, range, v-reversal, breakout
        scenarios = ["bull", "bear", "range", "v_rev", "breakout"]
        scen = random.choice(scenarios)

        if is_us:
            vol = (0.0016 if "S&P" in inst.get("display_name", "") else 0.0028) * day_open
        else:
            vol = 0.0022 * day_open

        candles = []
        curr_price = day_open
        time_start = "09:30:00" if is_us else "09:15:00"
        dt_base = datetime.strptime(f"{date_str} {time_start}", "%Y-%m-%d %H:%M:%S") if len(date_str) == 10 else datetime.now().replace(hour=9, minute=30 if is_us else 15)
        tz_offset = "-0400" if is_us else "+0530"

        for bar_idx in range(75):
            bar_dt = dt_base + timedelta(minutes=bar_idx * 5)
            unix_ts = int(bar_dt.timestamp())
            time_str = bar_dt.strftime("%H:%M")
            ts_iso = bar_dt.strftime(f"%Y-%m-%dT%H:%M:%S{tz_offset}")

            if scen == "bull":
                drift = (0.018 / 75.0) * curr_price
                step = drift + random.gauss(0, vol * 0.7)
            elif scen == "bear":
                drift = (-0.016 / 75.0) * curr_price
                step = drift + random.gauss(0, vol * 0.7)
            elif scen == "range":
                dist = curr_price - day_open
                step = -0.08 * dist + random.gauss(0, vol * 0.6)
            elif scen == "v_rev":
                step = (-0.0007 * curr_price if bar_idx < 22 else 0.001 * curr_price) + random.gauss(0, vol * 0.75)
            else:
                step = (random.gauss(0, vol * 0.35) if bar_idx < 42 else 0.0011 * curr_price + random.gauss(0, vol * 0.85))

            bar_open = curr_price
            bar_close = bar_open + step
            spread = abs(bar_close - bar_open)
            uw = random.uniform(0.1, 0.7) * vol + (spread * 0.2)
            lw = random.uniform(0.1, 0.7) * vol + (spread * 0.2)
            bar_high = max(bar_open, bar_close) + uw
            bar_low = min(bar_open, bar_close) - lw

            # Institutional volume curve
            u = 1.0 + 3.0 * ((bar_idx - 37) / 37.0) ** 2
            if is_us:
                v_base = 12000
            elif symbol in INDEX_SYMBOLS:
                v_base = 50000
            else:
                v_base = 5000
            bar_vol = int(v_base * u * random.uniform(0.7, 1.4))

            o_r = round(round(bar_open / tick) * tick, 2)
            h_r = round(round(bar_high / tick) * tick, 2)
            l_r = round(round(bar_low / tick) * tick, 2)
            c_r = round(round(bar_close / tick) * tick, 2)

            candles.append({
                "bar_index": bar_idx,
                "time": unix_ts,
                "time_str": time_str,
                "timestamp": ts_iso,
                "open": o_r,
                "high": max(o_r, c_r, h_r),
                "low": min(o_r, c_r, l_r),
                "close": c_r,
                "volume": bar_vol
            })
            curr_price = bar_close

        return candles

    def fetch_day_candles(
        self,
        symbol: str,
        date_str: str,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetches full 75 five-minute intraday candles (09:15 to 15:30) for a symbol and date.
        Prioritizes local disk cache. If remote API token is expired or unavailable,
        gracefully falls back to local data so gameplay never interrupts.
        """
        inst = get_instrument_config(symbol)

        # For US CME Futures, generate fresh high-fidelity US market session directly
        if inst.get("market") == "US":
            return self._generate_synthetic_day(symbol, date_str)

        cache_path = CACHE_DIR / f"{symbol.upper()}_{date_str}_5min.json"

        # 1. Check local disk cache first (for Indian instruments)
        if not force_refresh and cache_path.exists():
            try:
                with open(cache_path, "r") as f:
                    cached_data = json.load(f)
                    if isinstance(cached_data, list) and len(cached_data) >= 20:
                        return cached_data
            except Exception as e:
                logger.warning(f"Error reading local cache {cache_path}: {e}")

        # 2. Try remote Arrow API if token is valid
        formatted_candles: List[Dict[str, Any]] = []
        token = str(inst.get("token"))
        exchange = inst.get("exchange", "NSE")

        if token:
            from_ts = f"{date_str}T09:15:00"
            to_ts = f"{date_str}T15:30:00"
            try:
                raw_bars = self.market.get_candles(
                    token=token,
                    exchange=exchange,
                    interval="5min",
                    from_time=from_ts,
                    to_time=to_ts
                )
                if raw_bars and len(raw_bars) >= 20:
                    for idx, bar in enumerate(raw_bars):
                        ts_raw = str(bar[0])
                        unix_ts = self.parse_iso_timestamp(ts_raw)
                        o = round(float(bar[1]) / 100.0, 2)
                        h = round(float(bar[2]) / 100.0, 2)
                        l = round(float(bar[3]) / 100.0, 2)
                        c = round(float(bar[4]) / 100.0, 2)
                        v = int(bar[5]) if len(bar) > 5 else 0
                        time_part = ts_raw[11:16] if len(ts_raw) >= 16 else f"Bar {idx+1}"

                        formatted_candles.append({
                            "bar_index": idx,
                            "time": unix_ts,
                            "time_str": time_part,
                            "timestamp": ts_raw,
                            "open": o,
                            "high": h,
                            "low": l,
                            "close": c,
                            "volume": v
                        })

                    if formatted_candles:
                        with open(cache_path, "w") as f:
                            json.dump(formatted_candles, f, indent=2)
                        return formatted_candles
            except Exception as api_err:
                logger.warning(f"Arrow API fetch error ({api_err}). Falling back to local offline cache.")

        # 3. Fallback: Check if any other cached day exists for this symbol
        local_days = self.get_available_local_days(symbol)
        if local_days:
            # Pick a local day that exists
            alt_date = random.choice(local_days)
            alt_path = CACHE_DIR / f"{symbol.upper()}_{alt_date}_5min.json"
            try:
                with open(alt_path, "r") as f:
                    alt_data = json.load(f)
                    if isinstance(alt_data, list) and len(alt_data) >= 20:
                        return alt_data
            except Exception:
                pass

        # 4. Final safety guarantee: Synthesize authentic day and save locally
        synthetic_bars = self._generate_synthetic_day(symbol, date_str)
        try:
            with open(cache_path, "w") as f:
                json.dump(synthetic_bars, f, indent=2)
        except Exception:
            pass
        return synthetic_bars

    def create_session(
        self,
        mode: str = "index",
        symbol: Optional[str] = None,
        date: Optional[str] = None,
        blind_mode: bool = False,
        market: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates and initializes a new gameplay session:
        - Mode: 'index' (NIFTY, SENSEX, BANKNIFTY), 'stock' (Liquid FNO stocks), or 'us_futures' (MES, MNQ, ES, NQ)
        - Selects a historical day from locally saved dataset library or authentic synthesis
        - Returns 5-minute candles, opening bar & initial option chain
        """
        mode = mode.lower()
        if market == "US" or mode == "us_futures" or (symbol and symbol.upper() in US_FUTURES_SYMBOLS):
            mode = "us_futures"
            if not symbol or symbol.upper() not in US_FUTURES_SYMBOLS:
                symbol = "MES"
            else:
                symbol = symbol.upper()
        elif mode == "stock":
            if not symbol or symbol.upper() not in INSTRUMENTS:
                symbol = random.choice(STOCK_SYMBOLS)
            else:
                symbol = symbol.upper()
        else:
            mode = "index"
            if not symbol or symbol.upper() not in ["NIFTY", "SENSEX", "BANKNIFTY"]:
                symbol = random.choice(["NIFTY", "SENSEX"])
            else:
                symbol = symbol.upper()

        inst = get_instrument_config(symbol)
        is_us = (inst.get("market") == "US") or (mode == "us_futures")

        if is_us:
            if date and len(date) == 10:
                chosen_date = date
            else:
                us_dates = self.get_us_trading_dates()
                chosen_date = random.choice(us_dates) if us_dates else "2026-09-15"
        else:
            # Prioritize locally saved dates for this symbol so replay is instantaneous
            local_days = self.get_available_local_days(symbol)
            if date and (date in local_days or len(date) == 10):
                chosen_date = date
            elif local_days:
                chosen_date = random.choice(local_days)
            else:
                valid_dates = self.get_trading_dates()
                chosen_date = random.choice(valid_dates) if valid_dates else "2026-03-23"

        # Fetch candles (with guaranteed local fallback)
        candles = self.fetch_day_candles(symbol, chosen_date)

        first_candle = candles[0]
        spot_open = first_candle["open"]

        # Build initial option chain around opening spot price
        initial_chain = self.get_option_chain(
            symbol=symbol,
            spot_price=spot_open,
            bar_index=0,
            expiry_type="weekly"
        )

        session_id = str(uuid.uuid4())[:8]

        # Pretty date string (e.g. "Monday, 23 Mar 2026")
        try:
            dt = datetime.strptime(chosen_date, "%Y-%m-%d")
            pretty_date = dt.strftime("%A, %d %b %Y")
        except Exception:
            pretty_date = chosen_date

        return {
            "session_id": session_id,
            "mode": mode,
            "market": inst.get("market", "IN"),
            "currency": inst.get("currency", "INR"),
            "currency_symbol": inst.get("currency_symbol", "₹"),
            "point_value": inst.get("point_value", 1.0),
            "margin_per_contract": inst.get("margin_per_contract", None),
            "symbol": symbol,
            "display_name": inst["display_name"],
            "description": inst["description"],
            "badge": inst["badge"],
            "date": chosen_date,
            "pretty_date": pretty_date,
            "blind_mode": blind_mode,
            "lot_size": inst["lot_size"],
            "strike_step": inst["strike_step"],
            "tick_size": inst["tick_size"],
            "default_iv": inst["default_iv"],
            "total_bars": len(candles),
            "candles": candles,
            "initial_candle": first_candle,
            "initial_chain": initial_chain,
            "available_indices": [INSTRUMENTS[s] for s in INDEX_SYMBOLS],
            "available_stocks": [INSTRUMENTS[s] for s in STOCK_SYMBOLS],
            "available_us_futures": [INSTRUMENTS[s] for s in US_FUTURES_SYMBOLS]
        }

    def get_option_chain(
        self,
        symbol: str,
        spot_price: float,
        bar_index: int = 0,
        expiry_type: str = "weekly"
    ) -> Dict[str, Any]:
        """
        Builds a rich strike ladder around the current spot price with
        Black-Scholes Call and Put prices, Greeks, Moneyness labels, and lot values.
        """
        inst = get_instrument_config(symbol)
        step = inst["strike_step"]
        lot = inst["lot_size"]
        iv = inst["default_iv"]

        # ATM Strike
        atm_strike = round(spot_price / step) * step
        t_years = calculate_time_to_expiry(bar_index, total_bars=75, expiry_type=expiry_type)

        strikes_list = []
        offsets = [-3, -2, -1, 0, 1, 2, 3]

        for off in offsets:
            k = atm_strike + (off * step)
            call_label = "ATM" if off == 0 else (f"ITM {abs(off)}" if off < 0 else f"OTM {off}")
            put_label = "ATM" if off == 0 else (f"ITM {off}" if off > 0 else f"OTM {abs(off)}")

            ce_stats = black_scholes_price(spot_price, k, t_years, r=0.07, iv=iv, option_type="CE")
            pe_stats = black_scholes_price(spot_price, k, t_years, r=0.07, iv=iv, option_type="PE")

            ce_cost = round(ce_stats["price"] * lot, 2)
            pe_cost = round(pe_stats["price"] * lot, 2)

            strikes_list.append({
                "strike": k,
                "is_atm": (off == 0),
                "offset": off,
                "call": {
                    "price": ce_stats["price"],
                    "lot_cost": ce_cost,
                    "delta": ce_stats["delta"],
                    "gamma": ce_stats["gamma"],
                    "theta": ce_stats["theta"],
                    "vega": ce_stats["vega"],
                    "label": call_label,
                    "moneyness": "ATM" if off == 0 else ("ITM" if off < 0 else "OTM")
                },
                "put": {
                    "price": pe_stats["price"],
                    "lot_cost": pe_cost,
                    "delta": pe_stats["delta"],
                    "gamma": pe_stats["gamma"],
                    "theta": pe_stats["theta"],
                    "vega": pe_stats["vega"],
                    "label": put_label,
                    "moneyness": "ATM" if off == 0 else ("ITM" if off > 0 else "OTM")
                }
            })

        return {
            "symbol": symbol,
            "spot_price": spot_price,
            "bar_index": bar_index,
            "atm_strike": atm_strike,
            "strike_step": step,
            "lot_size": lot,
            "expiry_type": expiry_type,
            "time_to_expiry_years": round(t_years, 5),
            "strikes": strikes_list
        }

    def get_default_prop_firm_state(
        self,
        account_size: float = 50000.0,
        drawdown_type: str = "eod_trailing",
        max_dd_pct: float = 5.0,
        dll_pct: Optional[float] = 3.0,
        target_pct: float = 6.0,
        min_days: int = 2
    ) -> Dict[str, Any]:
        """Returns standard evaluation configuration and live tracking state for Prop Firm mode."""
        max_dd_amount = round(account_size * (max_dd_pct / 100.0), 2)
        dll_amount = round(account_size * (dll_pct / 100.0), 2) if dll_pct and dll_pct > 0 else 0.0
        profit_target_amount = round(account_size * (target_pct / 100.0), 2)
        floor = round(account_size - max_dd_amount, 2)

        return {
            "enabled": True,
            "phase": "evaluation",                  # "evaluation" or "funded"
            "status": "active",                     # "active", "passed", "failed"
            "account_size": account_size,
            "current_equity": account_size,
            "drawdown_type": drawdown_type,         # "static" or "eod_trailing"
            "max_drawdown_pct": max_dd_pct,
            "max_drawdown_amount": max_dd_amount,
            "daily_loss_limit_pct": dll_pct or 0.0,
            "daily_loss_limit_amount": dll_amount,
            "profit_target_pct": target_pct,
            "profit_target_amount": profit_target_amount,
            "min_trading_days": min_days,
            "high_water_mark": account_size,
            "drawdown_floor": floor,
            "day_start_equity": account_size,
            "daily_loss_locked": False,
            "days_traded": 0,
            "trading_days_count": 0,
            "daily_history": [],                    # List of day records
            "total_pnl": 0.0,
            "consistency_rule_pct": 40.0,
            "highest_day_pnl": 0.0,
            "highest_day_pct": 0.0,
            "lifetime_payouts": 0.0,
            "payout_history": [],
            "failure_reason": None,
            "pass_date": None
        }

    def load_game_state(self) -> Dict[str, Any]:
        """Loads saved player profile, balance, high score, and badges."""
        if GAME_STATE_FILE.exists():
            try:
                with open(GAME_STATE_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data.setdefault("market", "IN")
                        data.setdefault("inr_starting_balance", 1000000.0)
                        data.setdefault("inr_current_balance", data.get("current_balance", 1000000.0))
                        data.setdefault("usd_starting_balance", 50000.0)
                        data.setdefault("usd_current_balance", 50000.0)
                        if "prop_firm" not in data or not isinstance(data["prop_firm"], dict):
                            data["prop_firm"] = self.get_default_prop_firm_state()
                        return data
            except Exception:
                pass
        default_state = {
            "market": "IN",
            "starting_balance": 1000000.0,
            "current_balance": 1000000.0,
            "inr_starting_balance": 1000000.0,
            "inr_current_balance": 1000000.0,
            "usd_starting_balance": 50000.0,
            "usd_current_balance": 50000.0,
            "all_time_pnl": 0.0,
            "xp": 0,
            "rank": "Floor Trader",
            "trades_count": 0,
            "wins": 0,
            "losses": 0,
            "sound_enabled": True,
            "blind_mode": False,
            "trade_history": [],
            "prop_firm": self.get_default_prop_firm_state()
        }
        self.save_game_state(default_state)
        return default_state

    def setup_prop_firm(
        self,
        account_size: float = 50000.0,
        drawdown_type: str = "eod_trailing",
        max_dd_pct: float = 5.0,
        dll_pct: Optional[float] = 3.0,
        target_pct: float = 6.0,
        min_days: int = 2
    ) -> Dict[str, Any]:
        """Configures or restarts a Prop Firm Evaluation Challenge."""
        state = self.load_game_state()
        state["prop_firm"] = self.get_default_prop_firm_state(
            account_size=account_size,
            drawdown_type=drawdown_type,
            max_dd_pct=max_dd_pct,
            dll_pct=dll_pct,
            target_pct=target_pct,
            min_days=min_days
        )
        state["usd_starting_balance"] = account_size
        state["usd_current_balance"] = account_size
        if state.get("market") == "US":
            state["starting_balance"] = account_size
            state["current_balance"] = account_size
        self.save_game_state(state)
        return state["prop_firm"]

    def process_prop_firm_eod(
        self,
        date_str: str,
        day_pnl: float,
        trades_count: int
    ) -> Dict[str, Any]:
        """Processes end of simulated day, updates EOD trailing floor, history, and checks rules."""
        state = self.load_game_state()
        pf = state.get("prop_firm", self.get_default_prop_firm_state())

        equity = round(pf["current_equity"] + day_pnl, 2)
        pf["current_equity"] = equity
        state["usd_current_balance"] = equity
        if state.get("market") == "US":
            state["current_balance"] = equity

        pf["total_pnl"] = round(equity - pf["account_size"], 2)
        if trades_count > 0:
            pf["days_traded"] += 1
            pf["trading_days_count"] = pf["days_traded"]

        # Update High-Water Mark and Trailing Floor
        if pf["drawdown_type"] == "eod_trailing":
            if equity > pf["high_water_mark"]:
                pf["high_water_mark"] = equity
                raw_floor = round(pf["high_water_mark"] - pf["max_drawdown_amount"], 2)
                # Standard prop firm lock: once floor reaches initial balance, lock it and do not trail higher
                pf["drawdown_floor"] = min(pf["account_size"], raw_floor)
        else:
            # Static floor stays fixed at account_size - max_drawdown_amount
            pf["drawdown_floor"] = round(pf["account_size"] - pf["max_drawdown_amount"], 2)

        # Check MDD Breach
        if equity <= pf["drawdown_floor"]:
            pf["status"] = "failed"
            pf["failure_reason"] = f"Max Drawdown Breached: Equity (${equity:,.2f}) hit floor (${pf['drawdown_floor']:,.2f})"

        # Check Evaluation Target (if active and not breached)
        if pf["phase"] == "evaluation" and pf["status"] == "active":
            if pf["total_pnl"] >= pf["profit_target_amount"] and pf["days_traded"] >= pf["min_trading_days"]:
                pf["status"] = "passed"
                pf["pass_date"] = date_str

        # Update consistency calculation for funded accounts or evaluation tracking
        history = pf.setdefault("daily_history", [])
        history.append({
            "day_num": len(history) + 1,
            "date": date_str,
            "pnl": round(day_pnl, 2),
            "trades": trades_count,
            "close_equity": equity,
            "floor": pf["drawdown_floor"],
            "high_water_mark": pf["high_water_mark"]
        })

        profitable_days = [d["pnl"] for d in history if d["pnl"] > 0]
        tot_profit = sum(profitable_days)
        if tot_profit > 0 and profitable_days:
            max_day = max(profitable_days)
            pf["highest_day_pnl"] = max_day
            pf["highest_day_pct"] = round((max_day / tot_profit) * 100, 1)

        # Reset day starting baseline for next day
        pf["day_start_equity"] = equity
        pf["daily_loss_locked"] = False

        state["prop_firm"] = pf
        self.save_game_state(state)
        return pf

    def activate_funded_account(self, consistency_rule_pct: float = 40.0) -> Dict[str, Any]:
        """Promotes trader from cleared Evaluation to live Funded Account simulation."""
        state = self.load_game_state()
        pf = state.get("prop_firm", self.get_default_prop_firm_state())

        account_size = pf["account_size"]
        max_dd_amount = pf["max_drawdown_amount"]

        pf["phase"] = "funded"
        pf["status"] = "active"
        pf["consistency_rule_pct"] = consistency_rule_pct
        pf["current_equity"] = account_size
        pf["day_start_equity"] = account_size
        pf["high_water_mark"] = account_size
        pf["drawdown_floor"] = round(account_size - max_dd_amount, 2)
        pf["total_pnl"] = 0.0
        pf["days_traded"] = 0
        pf["daily_history"] = []
        pf["daily_loss_locked"] = False
        pf["highest_day_pnl"] = 0.0
        pf["highest_day_pct"] = 0.0
        pf["failure_reason"] = None

        state["usd_starting_balance"] = account_size
        state["usd_current_balance"] = account_size
        if state.get("market") == "US":
            state["starting_balance"] = account_size
            state["current_balance"] = account_size

        state["prop_firm"] = pf
        self.save_game_state(state)
        return pf

    def request_simulated_payout(self, amount: float) -> Dict[str, Any]:
        """Simulates requesting a prop firm payout from accumulated funded profits."""
        state = self.load_game_state()
        pf = state.get("prop_firm")
        if not pf or pf.get("phase") != "funded" or pf.get("status") != "active":
            raise ValueError("Payouts are only available on active Funded accounts.")

        account_size = pf["account_size"]
        current_equity = pf["current_equity"]
        profit_available = current_equity - account_size

        if amount <= 0:
            raise ValueError("Payout amount must be greater than $0.")
        if amount > profit_available:
            raise ValueError(f"Requested payout ${amount:,.2f} exceeds available funded profit ${profit_available:,.2f}.")

        # Deduct payout
        new_equity = round(current_equity - amount, 2)
        pf["current_equity"] = new_equity
        pf["total_pnl"] = round(new_equity - account_size, 2)
        pf["lifetime_payouts"] = round(pf.get("lifetime_payouts", 0.0) + amount, 2)

        payout_record = {
            "amount": amount,
            "remaining_equity": new_equity,
            "timestamp": int(datetime.utcnow().timestamp())
        }
        pf.setdefault("payout_history", []).append(payout_record)

        state["usd_current_balance"] = new_equity
        if state.get("market") == "US":
            state["current_balance"] = new_equity

        state["prop_firm"] = pf
        self.save_game_state(state)
        return {
            "payout": payout_record,
            "prop_firm": pf
        }

    def save_game_state(self, state: Dict[str, Any]) -> None:
        """Persists player profile and statistics."""
        try:
            with open(GAME_STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass
