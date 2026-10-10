from __future__ import annotations
from typing import Dict, Any, List, Tuple, Union, Optional
from datetime import datetime, timedelta
from pyarrow_client import (
    Exchange,
    QuoteMode,
)
from .client_manager import ArrowClientManager
from .orders import parse_exchange


def parse_quote_mode(mode: Union[str, QuoteMode]) -> QuoteMode:
    if isinstance(mode, QuoteMode):
        return mode
    m = str(mode).strip().upper()
    if m == "FULL":
        return QuoteMode.FULL
    elif m in ("OHLC", "OHLCV"):
        return QuoteMode.OHLCV
    return QuoteMode.LTP


class MarketService:
    def __init__(self, manager: ArrowClientManager = None):
        self.manager = manager or ArrowClientManager.get_instance()

    def get_quote(
        self,
        symbol: str,
        exchange: Union[str, Exchange] = Exchange.NSE,
        mode: Union[str, QuoteMode] = QuoteMode.FULL,
    ) -> Dict[str, Any]:
        client = self.manager.get_client()
        clean_sym = symbol.strip().upper()
        ex = parse_exchange(exchange)
        q_mode = parse_quote_mode(mode)

        try:
            res = client.get_quote(mode=q_mode, symbol=clean_sym, exchange=ex)
            if isinstance(res, dict) and "ltp" in res:
                return res
        except Exception:
            pass

        # If plain symbol failed on NSE/BSE and has no hyphen, try with -EQ suffix
        if ex in (Exchange.NSE, Exchange.BSE) and not clean_sym.endswith("-EQ") and "-" not in clean_sym:
            try:
                res = client.get_quote(mode=q_mode, symbol=f"{clean_sym}-EQ", exchange=ex)
                if isinstance(res, dict) and "ltp" in res:
                    return res
            except Exception:
                pass

        # Final direct attempt to surface any specific API error
        return client.get_quote(
            mode=q_mode,
            symbol=clean_sym,
            exchange=ex,
        )

    def get_quotes(
        self,
        symbols_with_exchange: List[Tuple[str, Union[str, Exchange]]],
        mode: Union[str, QuoteMode] = QuoteMode.LTP,
    ) -> List[Dict[str, Any]]:
        client = self.manager.get_client()
        formatted = [(s.strip().upper(), parse_exchange(ex)) for s, ex in symbols_with_exchange]
        return client.get_quotes(
            mode=parse_quote_mode(mode),
            symbols=formatted,
        )

    def get_candles(
        self,
        token: str,
        exchange: Union[str, Exchange] = Exchange.NSE,
        interval: str = "5min",
        from_time: Optional[Union[str, datetime]] = None,
        to_time: Optional[Union[str, datetime]] = None,
        oi: bool = False,
    ) -> List[Any]:
        """
        Intervals: min, 3min, 5min, 10min, 15min, 30min, hour, 2hours, 3hours, 4hours, day, week, month
        Timestamps: ISO string 'YYYY-MM-DDTHH:MM:SS'
        """
        client = self.manager.get_client()

        if to_time is None:
            now = datetime.now()
            to_iso = now.strftime("%Y-%m-%dT%H:%M:%S")
        elif isinstance(to_time, datetime):
            to_iso = to_time.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            to_iso = str(to_time)

        if from_time is None:
            # Default to 7 days ago or today morning
            start = datetime.now() - timedelta(days=5)
            from_iso = start.strftime("%Y-%m-%dT09:15:00")
        elif isinstance(from_time, datetime):
            from_iso = from_time.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            from_iso = str(from_time)

        # Calculate duration in days to auto-chunk if > 45 days for intraday
        try:
            start_dt = datetime.fromisoformat(from_iso.replace("Z", "+00:00")[:19])
            end_dt = datetime.fromisoformat(to_iso.replace("Z", "+00:00")[:19])
            total_days = (end_dt - start_dt).days
        except Exception:
            total_days = 10

        ex_parsed = parse_exchange(exchange)
        # Note: Index tokens (like 26000 for NIFTY) are queried on NSE exchange in Arrow Historical API
        if ex_parsed == Exchange.INDEX:
            ex_parsed = Exchange.NSE

        if total_days > 45 and interval not in ("day", "week", "month"):
            # Chunk in 30-day slices
            all_bars = []
            curr_start = start_dt
            while curr_start < end_dt:
                curr_end = min(curr_start + timedelta(days=30), end_dt)
                sub_from = curr_start.strftime("%Y-%m-%dT09:15:00")
                sub_to = curr_end.strftime("%Y-%m-%dT15:30:00")
                try:
                    bars = client.candle_data(
                        exchange=ex_parsed,
                        token=str(token),
                        interval=interval,
                        from_timestamp=sub_from,
                        to_timestamp=sub_to,
                        oi=oi,
                    )
                    if bars:
                        all_bars.extend(bars)
                except Exception:
                    pass
                curr_start = curr_end
            return all_bars

        return client.candle_data(
            exchange=ex_parsed,
            token=str(token),
            interval=interval,
            from_timestamp=from_iso,
            to_timestamp=to_iso,
            oi=oi,
        )

    def get_index_list(self) -> List[Dict[str, Any]]:
        client = self.manager.get_client()
        return client.get_index_list()

    def get_holidays(self) -> Dict[str, Any]:
        client = self.manager.get_client()
        return client.get_holidays()

    def get_option_chain_symbols(self) -> Any:
        client = self.manager.get_client()
        return client.get_option_chain_symbols()

    def get_option_chain(
        self,
        underlying: str,
        expiry: str,
        count: int = 10,
        exchange: Union[str, Exchange] = Exchange.INDEX,
    ) -> List[Dict[str, Any]]:
        client = self.manager.get_client()
        return client.get_option_chain(
            underlying=underlying.strip().upper(),
            exchange=parse_exchange(exchange),
            count=count,
            expiry=expiry,
        )

    def get_greeks(self, tokens: List[str]) -> Any:
        client = self.manager.get_client()
        return client.get_greeks(tokens=[str(t) for t in tokens])

    def get_expiry_dates(self, symbol: str, year: int) -> Any:
        client = self.manager.get_client()
        return client.get_expiry_dates(symbol=symbol, year=year)
