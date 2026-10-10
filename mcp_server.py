#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Server for Arrow Trade Broker (iRage Broking Services LLP).
Exposes tools for historical candle data, strategy backtesting, technical indicators,
real-time market quotes, account funds, positions, and order execution over standard stdio JSON-RPC.
"""

from __future__ import annotations
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from arrow_trader import (
    ArrowClientManager,
    PortfolioService,
    OrderService,
    MarketService,
)
from arrow_trader.backtest import BacktestEngine
from pyarrow_client import QuoteMode, Exchange

# Configure logger to output only to stderr (stdout is reserved exclusively for MCP JSON-RPC protocol)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("arrow_mcp_server")


# =====================================================================
# MCP TOOL DEFINITIONS
# =====================================================================

TOOLS = [
    {
        "name": "get_historical_candles",
        "description": "Fetch historical OHLCV candle data from Arrow Trade broker for backtesting or chart analysis. Returns prices converted to Rupees (₹) and summary stats.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Trading symbol (e.g., 'RELIANCE', 'TCS', 'INFY', 'SBIN'). Suffix '-EQ' is added automatically if omitted."
                },
                "exchange": {
                    "type": "string",
                    "enum": ["NSE", "BSE", "NFO", "BFO", "INDEX"],
                    "default": "NSE",
                    "description": "Exchange segment (default: NSE)."
                },
                "interval": {
                    "type": "string",
                    "enum": ["min", "3min", "5min", "10min", "15min", "30min", "hour", "2hours", "3hours", "4hours", "day", "week", "month"],
                    "default": "day",
                    "description": "Candle timeframe interval (default: 'day')."
                },
                "days_back": {
                    "type": "integer",
                    "default": 30,
                    "description": "Number of days back from today to fetch data for (e.g. 30, 90, 365). Overridden if from_date is set."
                },
                "from_date": {
                    "type": "string",
                    "description": "Optional start date in 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS' format."
                },
                "to_date": {
                    "type": "string",
                    "description": "Optional end date in 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS' format (defaults to current time)."
                },
                "token": {
                    "type": "string",
                    "description": "Optional numeric instrument token. If omitted, resolved automatically from the symbol."
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "backtest_strategy",
        "description": "Run a quantitative backtest of an algorithmic trading strategy on historical Arrow Trade market data. Evaluates performance, win rate, Sharpe ratio, max drawdown, and trade logs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Trading symbol to backtest (e.g., 'RELIANCE', 'TCS', 'INFY')."
                },
                "strategy": {
                    "type": "string",
                    "enum": ["sma_crossover", "ema_crossover", "rsi", "bollinger_bands", "breakout", "orb", "orb_pdh_pdl", "orb_5min"],
                    "default": "sma_crossover",
                    "description": "Strategy type to simulate."
                },
                "parameters": {
                    "type": "object",
                    "description": "Strategy parameters. e.g. for orb_5min: {'target_ratio': 0.5, 'sl_ratio': 1.0}; for orb_pdh_pdl: {'risk_pct': 0.01, 'lot_size': 25}; for orb: {'range_bars': 1, 'target_multiplier': 1.5}."
                },
                "interval": {
                    "type": "string",
                    "enum": ["min", "5min", "15min", "30min", "hour", "day"],
                    "default": "day",
                    "description": "Candle interval (default: 'day')."
                },
                "days_back": {
                    "type": "integer",
                    "default": 60,
                    "description": "Number of days of historical data to simulate."
                },
                "initial_capital": {
                    "type": "number",
                    "default": 100000.0,
                    "description": "Initial capital in Rupees (default: ₹1,00,000)."
                },
                "exchange": {
                    "type": "string",
                    "default": "NSE",
                    "description": "Exchange segment (default: NSE)."
                }
            },
            "required": ["symbol", "strategy"]
        }
    },
    {
        "name": "calculate_technical_indicators",
        "description": "Calculates technical indicators (RSI, SMA, EMA, MACD, Bollinger Bands, ATR) on historical candle data for a symbol and returns latest indicator readings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Trading symbol (e.g., 'RELIANCE', 'TCS')."
                },
                "exchange": {
                    "type": "string",
                    "default": "NSE",
                    "description": "Exchange (default: NSE)."
                },
                "interval": {
                    "type": "string",
                    "default": "day",
                    "description": "Candle interval ('day', 'hour', '15min')."
                },
                "days_back": {
                    "type": "integer",
                    "default": 60,
                    "description": "Lookback period in days."
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_market_quote",
        "description": "Retrieve real-time market quote for a symbol, including Last Traded Price (LTP in ₹), Day Open, High, Low, Close, % Change, Volume, and 5-level Market Depth.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Trading symbol (e.g., 'RELIANCE', 'TCS-EQ', 'NIFTY')."
                },
                "exchange": {
                    "type": "string",
                    "enum": ["NSE", "BSE", "NFO", "BFO", "INDEX"],
                    "default": "NSE",
                    "description": "Exchange segment (default: NSE)."
                },
                "mode": {
                    "type": "string",
                    "enum": ["LTP", "OHLCV", "FULL"],
                    "default": "FULL",
                    "description": "Quote depth mode (default: FULL)."
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_account_funds",
        "description": "Retrieve account balance, available margin, utilized margin, collateral, and cash allocations from Arrow Trade broker.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_open_positions",
        "description": "Fetch all open trading positions, net quantities, average prices, and current mark-to-market P&L.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_demat_holdings",
        "description": "Fetch Demat long-term stock holdings with quantity, average acquisition cost, LTP, current valuation, and overall P&L.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "calculate_order_margin",
        "description": "Calculate required margin for an order before placing it with the broker.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading symbol"},
                "quantity": {"type": "integer", "description": "Number of shares/contracts"},
                "price": {"type": "number", "description": "Order price"},
                "exchange": {"type": "string", "default": "NSE", "description": "Exchange"},
                "transaction_type": {"type": "string", "enum": ["BUY", "SELL"], "default": "BUY"},
                "order_type": {"type": "string", "enum": ["LIMIT", "MARKET"], "default": "LIMIT"},
                "product": {"type": "string", "enum": ["CNC", "MIS", "NRML"], "default": "MIS"}
            },
            "required": ["symbol", "quantity", "price"]
        }
    },
    {
        "name": "place_order",
        "description": "Place a live order with Arrow Trade broker. Supports MIS (Intraday), CNC (Delivery), NRML across NSE, BSE, NFO.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading symbol (e.g. 'RELIANCE-EQ')"},
                "quantity": {"type": "integer", "description": "Number of shares/contracts"},
                "price": {"type": "number", "default": 0.0, "description": "Limit price (0 for market)"},
                "exchange": {"type": "string", "default": "NSE", "description": "Exchange"},
                "transaction_type": {"type": "string", "enum": ["BUY", "SELL"], "default": "BUY"},
                "order_type": {"type": "string", "enum": ["LIMIT", "MARKET", "STOP_LOSS_LIMIT"], "default": "LIMIT"},
                "product": {"type": "string", "enum": ["MIS", "CNC", "NRML"], "default": "MIS"},
                "trigger_price": {"type": "number", "default": 0.0, "description": "Trigger price for stop loss orders"},
                "remarks": {"type": "string", "description": "Optional order tag/remarks (max 16 chars)"}
            },
            "required": ["symbol", "quantity", "transaction_type"]
        }
    },
    {
        "name": "get_order_book",
        "description": "Retrieve today's complete order book with order IDs, quantities, execution status, and fill details.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "cancel_order",
        "description": "Cancel an open or pending order by order ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID to cancel"}
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "cancel_all_orders",
        "description": "Cancel all open/pending orders across all segments.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_option_chain",
        "description": "Fetch option chain for an index or stock underlying with strike prices, option tokens, open interest, and lot sizes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "underlying": {"type": "string", "description": "Underlying symbol e.g. 'NIFTY', 'BANKNIFTY', 'RELIANCE'"},
                "expiry": {"type": "string", "description": "Expiry date in 'DD-MMM-YYYY' format"},
                "count": {"type": "integer", "default": 10, "description": "Number of strikes around ATM"},
                "exchange": {"type": "string", "default": "INDEX", "description": "'INDEX' for index options or 'NSE' for stock options"}
            },
            "required": ["underlying", "expiry"]
        }
    },
    {
        "name": "get_index_list",
        "description": "List all supported market indices (Nifty 50, Nifty Bank, FinNifty, etc.) and their instrument tokens.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "create_game_session",
        "description": "Initialize a trading game simulator session for Index Play (Nifty, Sensex) or Stock Play (Reliance, TCS, etc.) with 5-minute opening candles, option chains, and replay controls.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["index", "stock"], "default": "index", "description": "Mode: 'index' or 'stock'"},
                "symbol": {"type": "string", "description": "Optional symbol (e.g. 'NIFTY', 'SENSEX', 'RELIANCE')"},
                "date": {"type": "string", "description": "Optional YYYY-MM-DD historical trading date"},
                "blind_mode": {"type": "boolean", "default": False, "description": "Hide date/symbol for unbiased practice"}
            }
        }
    }
]


# =====================================================================
# TOOL EXECUTION HANDLERS
# =====================================================================

def handle_get_historical_candles(args: Dict[str, Any]) -> Dict[str, Any]:
    market = MarketService()
    client = market.manager.get_client()

    symbol = args["symbol"].strip().upper()
    exchange = args.get("exchange", "NSE")
    interval = args.get("interval", "day")
    token = args.get("token")

    # Resolve token if not explicitly provided
    if not token:
        try:
            quote = market.get_quote(symbol, exchange, mode="LTP")
            token = quote.get("token")
        except Exception:
            pass

    if not token:
        return {"error": f"Could not resolve instrument token for symbol '{symbol}'. Try providing the numeric token directly."}

    # Resolve dates
    to_date = args.get("to_date")
    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%dT15:30:00")
    elif len(to_date) == 10:
        to_date = f"{to_date}T15:30:00"

    from_date = args.get("from_date")
    if not from_date:
        days = int(args.get("days_back", 30))
        start_dt = datetime.now() - timedelta(days=days)
        from_date = start_dt.strftime("%Y-%m-%dT09:15:00")
    elif len(from_date) == 10:
        from_date = f"{from_date}T09:15:00"

    raw_candles = client.candle_data(
        exchange=exchange,
        token=str(token),
        interval=interval,
        from_timestamp=from_date,
        to_timestamp=to_date,
    )

    df = BacktestEngine.candles_to_dataframe(raw_candles)
    if df.empty:
        return {"message": "No candle data returned for the requested parameters.", "bars": 0}

    # Format return payload
    candles_list = []
    for _, row in df.iterrows():
        candles_list.append({
            "timestamp": str(row["timestamp"]),
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["close"]), 2),
            "volume": int(row["volume"]),
        })

    summary = {
        "symbol": symbol,
        "token": token,
        "exchange": exchange,
        "interval": interval,
        "total_bars": len(df),
        "period_start": str(df.iloc[0]["timestamp"]),
        "period_end": str(df.iloc[-1]["timestamp"]),
        "latest_close": round(float(df.iloc[-1]["close"]), 2),
        "period_high": round(float(df["high"].max()), 2),
        "period_low": round(float(df["low"].min()), 2),
        "candles": candles_list,
    }
    return summary


def handle_backtest_strategy(args: Dict[str, Any]) -> Dict[str, Any]:
    market = MarketService()
    client = market.manager.get_client()

    symbol = args["symbol"].strip().upper()
    exchange = args.get("exchange", "NSE")
    strategy_name = args.get("strategy", "sma_crossover")
    parameters = args.get("parameters", {})
    if strategy_name.lower() in ("orb", "opening_range_breakout"):
        interval = args.get("interval", "15min")
        days_back = int(args.get("days_back", 30))
    elif strategy_name.lower() in ("orb_pdh_pdl", "orb_filter", "orb_advanced"):
        interval = args.get("interval", "15min")
        days_back = int(args.get("days_back", 120))
    elif strategy_name.lower() in ("orb_5min", "orb_5m", "orb_5min_2to1"):
        interval = args.get("interval", "5min")
        days_back = int(args.get("days_back", 180))
    else:
        interval = args.get("interval", "day")
        days_back = int(args.get("days_back", 60))
    initial_capital = float(args.get("initial_capital", 1000000.0 if ("pdh" in strategy_name.lower() or "5min" in strategy_name.lower()) else 100000.0))

    # Resolve token
    try:
        quote = market.get_quote(symbol, exchange, mode="LTP")
        token = quote.get("token")
    except Exception as e:
        return {"error": f"Failed to resolve symbol {symbol}: {e}"}

    if not token:
        return {"error": f"Could not find instrument token for {symbol}."}

    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT09:15:00")
    to_date = datetime.now().strftime("%Y-%m-%dT15:30:00")

    raw_candles = market.get_candles(
        exchange=exchange,
        token=str(token),
        interval=interval,
        from_time=from_date,
        to_time=to_date,
    )

    df = BacktestEngine.candles_to_dataframe(raw_candles)
    if df.empty or len(df) < 5:
        return {"error": f"Insufficient historical data retrieved ({len(df)} bars). Try a longer days_back or smaller interval."}

    backtest_result = BacktestEngine.run_backtest(
        df=df,
        strategy_name=strategy_name,
        parameters=parameters,
        initial_capital=initial_capital,
    )
    backtest_result["symbol"] = symbol
    backtest_result["token"] = token
    return backtest_result


def handle_calculate_technical_indicators(args: Dict[str, Any]) -> Dict[str, Any]:
    market = MarketService()
    client = market.manager.get_client()

    symbol = args["symbol"].strip().upper()
    exchange = args.get("exchange", "NSE")
    interval = args.get("interval", "day")
    days_back = int(args.get("days_back", 60))

    try:
        quote = market.get_quote(symbol, exchange, mode="LTP")
        token = quote.get("token")
    except Exception as e:
        return {"error": f"Failed to get quote for {symbol}: {e}"}

    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT09:15:00")
    to_date = datetime.now().strftime("%Y-%m-%dT15:30:00")

    raw_candles = client.candle_data(
        exchange=exchange,
        token=str(token),
        interval=interval,
        from_timestamp=from_date,
        to_timestamp=to_date,
    )

    df = BacktestEngine.candles_to_dataframe(raw_candles)
    if df.empty or len(df) < 14:
        return {"error": f"Insufficient bars ({len(df)}) to compute 14-period indicators."}

    df_ind = BacktestEngine.compute_indicators(df)
    last = df_ind.iloc[-1]
    prev = df_ind.iloc[-2]

    close_p = round(float(last["close"]), 2)
    rsi = round(float(last["rsi_14"]), 2)
    sma_20 = round(float(last["sma_20"]), 2) if not pd.isna(last["sma_20"]) else None
    sma_50 = round(float(last["sma_50"]), 2) if not pd.isna(last["sma_50"]) else None
    macd = round(float(last["macd"]), 2)
    macd_sig = round(float(last["macd_signal"]), 2)

    # Signal summaries
    rsi_signal = "Oversold (Bullish bias)" if rsi < 30 else ("Overbought (Bearish bias)" if rsi > 70 else "Neutral")
    trend = "Bullish" if (sma_20 and close_p > sma_20) else "Bearish"
    macd_trend = "Bullish Crossover" if (last["macd"] > last["macd_signal"] and prev["macd"] <= prev["macd_signal"]) else ("Bullish" if last["macd"] > last["macd_signal"] else "Bearish")

    return {
        "symbol": symbol,
        "timestamp": str(last["timestamp"]),
        "latest_price": close_p,
        "indicators": {
            "rsi_14": rsi,
            "rsi_status": rsi_signal,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "trend_vs_sma20": trend,
            "macd": macd,
            "macd_signal": macd_sig,
            "macd_trend": macd_trend,
            "bollinger_upper": round(float(last["bb_upper"]), 2) if not pd.isna(last["bb_upper"]) else None,
            "bollinger_lower": round(float(last["bb_lower"]), 2) if not pd.isna(last["bb_lower"]) else None,
            "atr_14": round(float(last["atr_14"]), 2) if not pd.isna(last["atr_14"]) else None,
        }
    }


def handle_get_market_quote(args: Dict[str, Any]) -> Dict[str, Any]:
    market = MarketService()
    symbol = args["symbol"].strip().upper()
    exchange = args.get("exchange", "NSE")
    mode = args.get("mode", "FULL")

    quote = market.get_quote(symbol, exchange, mode=mode)
    if isinstance(quote, dict) and "ltp" in quote:
        # Format paise to Rupees
        ltp = float(quote.get("ltp", 0.0)) / 100.0
        open_p = float(quote.get("open", 0.0)) / 100.0
        high_p = float(quote.get("high", 0.0)) / 100.0
        low_p = float(quote.get("low", 0.0)) / 100.0
        close_p = float(quote.get("close", 0.0)) / 100.0
        vwap = float(quote.get("avgPrice", quote.get("avg_price", 0.0))) / 100.0
        chg = float(quote.get("net_change", quote.get("netChange", 0.0)))

        formatted = {
            "symbol": quote.get("symbol", symbol),
            "exchange": exchange,
            "token": quote.get("token"),
            "ltp_rupees": round(ltp, 2),
            "net_change_pct": round(chg, 2),
            "open_rupees": round(open_p, 2),
            "high_rupees": round(high_p, 2),
            "low_rupees": round(low_p, 2),
            "close_rupees": round(close_p, 2),
            "vwap_rupees": round(vwap, 2),
            "volume": int(quote.get("volume", 0)),
        }
        if "bids" in quote:
            formatted["bids"] = [
                {"price": round(float(b.get("price", 0)) / 100.0, 2), "quantity": b.get("quantity", 0), "orders": b.get("orders", 0)}
                for b in quote.get("bids", []) if b.get("quantity", 0) > 0
            ]
        if "asks" in quote:
            formatted["asks"] = [
                {"price": round(float(a.get("price", 0)) / 100.0, 2), "quantity": a.get("quantity", 0), "orders": a.get("orders", 0)}
                for a in quote.get("asks", []) if a.get("quantity", 0) > 0
            ]
        return formatted
    return quote


def handle_get_account_funds(args: Dict[str, Any]) -> Dict[str, Any]:
    service = PortfolioService()
    limits = service.get_limits()
    margin = limits.get("margin", {})
    return {
        "usable_margin": float(margin.get("usableMargin", margin.get("totalAvailableMargin", 0))),
        "allocated_fo": float(margin.get("allocated", 0)),
        "utilized_margin": float(margin.get("utilized", 0)),
        "cash_available_cnc": float(margin.get("cashAvailableForCNC", 0)),
        "cash_available_option_buy": float(margin.get("cashAvailableForOptionBuy", 0)),
        "collateral_noncash": float(margin.get("totalNoncash", 0)),
        "raw_margin_details": margin,
    }


def handle_get_open_positions(args: Dict[str, Any]) -> List[Dict[str, Any]]:
    service = PortfolioService()
    positions = service.get_positions()
    res = []
    for p in positions:
        res.append({
            "symbol": p.get("symbol", p.get("tradingSymbol")),
            "product": p.get("product"),
            "net_quantity": p.get("netQty", p.get("netqty", 0)),
            "average_price": float(p.get("buyAvgPrice", p.get("avgPrice", 0.0))),
            "ltp": float(p.get("ltp", 0.0)),
            "pnl": float(p.get("pnl", p.get("urmtom", 0.0))),
        })
    return res


def handle_get_demat_holdings(args: Dict[str, Any]) -> List[Dict[str, Any]]:
    service = PortfolioService()
    holdings = service.get_holdings()
    res = []
    for h in holdings:
        qty = int(h.get("quantity", h.get("holdingsQty", 0)))
        cost = float(h.get("averagePrice", h.get("price", 0.0)))
        ltp = float(h.get("ltp", 0.0))
        val = qty * ltp
        pnl = (ltp - cost) * qty
        res.append({
            "symbol": h.get("symbol", h.get("tradingSymbol")),
            "exchange": h.get("exchange", "NSE"),
            "quantity": qty,
            "average_cost": round(cost, 2),
            "ltp": round(ltp, 2),
            "current_value": round(val, 2),
            "pnl": round(pnl, 2),
        })
    return res


def handle_calculate_order_margin(args: Dict[str, Any]) -> Dict[str, Any]:
    service = OrderService()
    return service.calculate_margin(
        symbol=args["symbol"],
        quantity=int(args["quantity"]),
        price=float(args["price"]),
        exchange=args.get("exchange", "NSE"),
        transaction_type=args.get("transaction_type", "BUY"),
        order_type=args.get("order_type", "LIMIT"),
        product=args.get("product", "MIS"),
    )


def handle_place_order(args: Dict[str, Any]) -> Dict[str, Any]:
    service = OrderService()
    order_id = service.place_order(
        symbol=args["symbol"],
        quantity=int(args["quantity"]),
        price=float(args.get("price", 0.0)),
        exchange=args.get("exchange", "NSE"),
        transaction_type=args.get("transaction_type", "BUY"),
        order_type=args.get("order_type", "LIMIT"),
        product=args.get("product", "MIS"),
        trigger_price=float(args.get("trigger_price", 0.0)),
        remarks=args.get("remarks"),
    )
    return {"status": "success", "order_id": order_id}


def handle_get_order_book(args: Dict[str, Any]) -> List[Dict[str, Any]]:
    service = OrderService()
    orders = service.get_order_book()
    res = []
    for o in orders:
        res.append({
            "order_id": o.get("orderNo", o.get("orderId")),
            "symbol": o.get("symbol", o.get("tradingSymbol")),
            "side": o.get("transactionType", o.get("transType")),
            "order_type": o.get("orderType"),
            "product": o.get("product"),
            "quantity": o.get("quantity"),
            "filled_quantity": o.get("filledQuantity", 0),
            "price": float(o.get("price", 0.0)),
            "status": o.get("status", o.get("orderStatus")),
            "order_time": o.get("orderDateTime", o.get("time")),
        })
    return res


def handle_cancel_order(args: Dict[str, Any]) -> Dict[str, Any]:
    service = OrderService()
    res = service.cancel_order(args["order_id"])
    return {"status": "success", "result": res}


def handle_cancel_all_orders(args: Dict[str, Any]) -> Dict[str, Any]:
    service = OrderService()
    res = service.cancel_all_orders()
    return {"status": "success", "result": res}


def handle_get_option_chain(args: Dict[str, Any]) -> Any:
    market = MarketService()
    return market.get_option_chain(
        underlying=args["underlying"],
        expiry=args["expiry"],
        count=int(args.get("count", 10)),
        exchange=args.get("exchange", "INDEX"),
    )


def handle_get_index_list(args: Dict[str, Any]) -> Any:
    market = MarketService()
    return market.get_index_list()


def handle_create_game_session(args: Dict[str, Any]) -> Any:
    from arrow_trader.game.simulator_service import SimulatorService
    sim = SimulatorService()
    return sim.create_session(
        mode=args.get("mode", "index"),
        symbol=args.get("symbol"),
        date=args.get("date"),
        blind_mode=args.get("blind_mode", False)
    )


DISPATCHER = {
    "get_historical_candles": handle_get_historical_candles,
    "backtest_strategy": handle_backtest_strategy,
    "calculate_technical_indicators": handle_calculate_technical_indicators,
    "get_market_quote": handle_get_market_quote,
    "get_account_funds": handle_get_account_funds,
    "get_open_positions": handle_get_open_positions,
    "get_demat_holdings": handle_get_demat_holdings,
    "calculate_order_margin": handle_calculate_order_margin,
    "place_order": handle_place_order,
    "get_order_book": handle_get_order_book,
    "cancel_order": handle_cancel_order,
    "cancel_all_orders": handle_cancel_all_orders,
    "get_option_chain": handle_get_option_chain,
    "get_index_list": handle_get_index_list,
    "create_game_session": handle_create_game_session,
}


# =====================================================================
# JSON-RPC 2.0 PROTOCOL ENGINE
# =====================================================================

def send_response(response: Dict[str, Any]) -> None:
    line = json.dumps(response) + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()


def process_message(msg: Dict[str, Any]) -> None:
    msg_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params", {})

    logger.debug(f"Received method={method}, id={msg_id}")

    # 1. Initialize
    if method == "initialize":
        send_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "arrow-trade-mcp",
                    "version": "1.0.0"
                }
            }
        })

    # 2. Initialized notification
    elif method == "notifications/initialized":
        logger.info("Client completed initialization handshake.")

    # 3. Ping
    elif method == "ping":
        send_response({"jsonrpc": "2.0", "id": msg_id, "result": {}})

    # 4. List Tools
    elif method == "tools/list":
        send_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOLS}
        })

    # 5. Call Tool
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        handler = DISPATCHER.get(tool_name)
        if not handler:
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool '{tool_name}' not found."
                }
            })
            return

        try:
            result_data = handler(tool_args)
            result_text = json.dumps(result_data, indent=2)
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ],
                    "isError": False
                }
            })
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}")
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error executing tool '{tool_name}': {str(e)}"
                        }
                    ],
                    "isError": True
                }
            })

    # Unknown method
    else:
        if msg_id is not None:
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not supported."
                }
            })


def main():
    logger.info("Starting Arrow Trade MCP Server on stdio...")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            process_message(msg)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode incoming JSON: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in loop: {e}")


if __name__ == "__main__":
    main()
