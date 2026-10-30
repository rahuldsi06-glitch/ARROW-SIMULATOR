from __future__ import annotations
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .simulator_service import SimulatorService
from .instruments import (
    INSTRUMENTS,
    INDEX_SYMBOLS,
    STOCK_SYMBOLS,
    US_FUTURES_SYMBOLS,
    get_instrument_config
)
from .options_math import black_scholes_price, calculate_time_to_expiry, estimate_option_bar_extremes

router = APIRouter(prefix="/api/game", tags=["game"])
simulator = SimulatorService()


class SessionCreateRequest(BaseModel):
    mode: str = "index"  # 'index', 'stock', or 'us_futures'
    market: Optional[str] = "IN"  # 'IN' or 'US'
    symbol: Optional[str] = None
    date: Optional[str] = None
    blind_mode: bool = False


class OptionChainRequest(BaseModel):
    symbol: str
    spot_price: float
    bar_index: int = 0
    expiry_type: str = "weekly"


class SaveTradeRequest(BaseModel):
    trade_id: str
    symbol: str
    market: Optional[str] = "IN"  # 'IN' or 'US'
    currency: Optional[str] = "INR"  # 'INR' or 'USD'
    instrument_type: Optional[str] = "options"  # 'options' or 'futures'
    strike: Optional[float] = 0.0
    option_type: Optional[str] = "CE"  # 'CE', 'PE', 'FUT_LONG', 'FUT_SHORT'
    expiry_type: Optional[str] = "weekly"
    lot_size: int
    lots: int
    quantity: int
    entry_bar: int
    exit_bar: int
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    pnl: float
    pnl_pct: float
    exit_reason: str  # 'TARGET_HIT', 'STOP_LOSS_HIT', 'MANUAL_EXIT', 'EOD_SQUAREOFF'


class ResetAccountRequest(BaseModel):
    starting_balance: float = 1000000.0
    market: Optional[str] = "IN"  # 'IN' or 'US'


class PropFirmSetupRequest(BaseModel):
    account_size: float = 50000.0
    drawdown_type: str = "eod_trailing"  # 'static' or 'eod_trailing'
    max_drawdown_pct: float = 5.0
    daily_loss_limit_enabled: bool = True
    daily_loss_limit_pct: Optional[float] = 3.0
    profit_target_pct: float = 6.0
    min_trading_days: int = 2


class PropFirmEODRequest(BaseModel):
    date: Optional[str] = ""
    day_pnl: float = 0.0
    trades_count: int = 1
    prop_firm: Optional[Dict[str, Any]] = None


class PropFirmFundedRequest(BaseModel):
    consistency_rule_pct: float = 40.0


class PropFirmPayoutRequest(BaseModel):
    amount: float


@router.get("/config")
def get_game_config() -> Dict[str, Any]:
    """Retrieve game configuration, instruments, and saved player state."""
    state = simulator.load_game_state()
    return {
        "status": "success",
        "state": state,
        "indices": [INSTRUMENTS[s] for s in INDEX_SYMBOLS],
        "stocks": [INSTRUMENTS[s] for s in STOCK_SYMBOLS],
        "us_futures": [INSTRUMENTS[s] for s in US_FUTURES_SYMBOLS],
    }


@router.post("/session")
def create_game_session(req: SessionCreateRequest) -> Dict[str, Any]:
    """Initialize a new trading game session with random day historical data."""
    try:
        session = simulator.create_session(
            mode=req.mode,
            symbol=req.symbol,
            date=req.date,
            blind_mode=req.blind_mode,
            market=req.market
        )
        return {
            "status": "success",
            "session": session
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/option-chain")
def get_live_option_chain(req: OptionChainRequest) -> Dict[str, Any]:
    """Calculates dynamic Black-Scholes option chain for given spot & bar index."""
    try:
        chain = simulator.get_option_chain(
            symbol=req.symbol,
            spot_price=req.spot_price,
            bar_index=req.bar_index,
            expiry_type=req.expiry_type
        )
        return {
            "status": "success",
            "chain": chain
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trade")
def record_completed_trade(req: SaveTradeRequest) -> Dict[str, Any]:
    """Records a completed trade, awards XP, updates player statistics & balance."""
    state = simulator.load_game_state()
    trade_data = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    
    is_us = req.market == "US" or req.currency == "USD"
    if is_us:
        state["usd_current_balance"] = round(state.get("usd_current_balance", 50000.0) + req.pnl, 2)
        state["current_balance"] = state["usd_current_balance"]
        if "prop_firm" in state and isinstance(state["prop_firm"], dict):
            pf = state["prop_firm"]
            pf["current_equity"] = state["usd_current_balance"]
            pf["total_pnl"] = round(pf["current_equity"] - pf["account_size"], 2)
            # Intraday MDD breach check
            if pf["current_equity"] <= pf.get("drawdown_floor", 0):
                pf["status"] = "failed"
                pf["failure_reason"] = f"Max Drawdown Breached: Intraday equity ${pf['current_equity']:,.2f} touched floor ${pf['drawdown_floor']:,.2f}"
    else:
        state["inr_current_balance"] = round(state.get("inr_current_balance", 1000000.0) + req.pnl, 2)
        state["current_balance"] = state["inr_current_balance"]

    state["all_time_pnl"] = round(state["all_time_pnl"] + req.pnl, 2)
    state["trades_count"] += 1
    
    if req.pnl > 0:
        state["wins"] += 1
        xp_gain = int(max(50, req.pnl / (10 if is_us else 100)))
    else:
        state["losses"] += 1
        xp_gain = 10
    
    state["xp"] += xp_gain

    # Rank calculation
    xp = state["xp"]
    if xp < 500:
        state["rank"] = "Floor Trader"
    elif xp < 1500:
        state["rank"] = "Prop Trader"
    elif xp < 3500:
        state["rank"] = "Senior Scalper"
    elif xp < 7500:
        state["rank"] = "Hedge Fund PM"
    else:
        state["rank"] = "Market Maker Titan"

    history = state.get("trade_history", [])
    history.append(trade_data)
    # Keep last 50 trades
    state["trade_history"] = history[-50:]
    
    simulator.save_game_state(state)
    return {
        "status": "success",
        "market": "US" if is_us else "IN",
        "currency": "USD" if is_us else "INR",
        "xp_gained": xp_gain,
        "new_balance": state["current_balance"],
        "rank": state["rank"],
        "state": state
    }


@router.post("/reset-account")
def reset_account(req: ResetAccountRequest) -> Dict[str, Any]:
    """Resets virtual starting capital and performance history."""
    state = simulator.load_game_state()
    is_us = req.market == "US"
    bal = max(1000.0 if is_us else 10000.0, req.starting_balance)

    if is_us:
        state["usd_starting_balance"] = bal
        state["usd_current_balance"] = bal
        state["current_balance"] = bal
        msg = f"US Prop Firm Account reset with ${bal:,.2f} starting capital"
    else:
        state["inr_starting_balance"] = bal
        state["inr_current_balance"] = bal
        state["current_balance"] = bal
        msg = f"India Market Account reset with ₹{bal:,.2f} starting capital"

    state["starting_balance"] = bal
    state["all_time_pnl"] = 0.0
    state["xp"] = 0
    state["rank"] = "Floor Trader"
    state["trades_count"] = 0
    state["wins"] = 0
    state["losses"] = 0
    state["trade_history"] = []

    simulator.save_game_state(state)
    return {
        "status": "success",
        "message": msg,
        "state": state
    }


@router.post("/propfirm/setup")
def setup_propfirm(req: PropFirmSetupRequest) -> Dict[str, Any]:
    """Configures a new Prop Firm Evaluation Challenge."""
    try:
        pf = simulator.setup_prop_firm(
            account_size=req.account_size,
            drawdown_type=req.drawdown_type,
            max_dd_pct=req.max_drawdown_pct,
            dll_pct=req.daily_loss_limit_pct if req.daily_loss_limit_enabled else 0.0,
            target_pct=req.profit_target_pct,
            min_days=req.min_trading_days,
            daily_loss_limit_enabled=req.daily_loss_limit_enabled
        )
        return {
            "status": "success",
            "message": f"Prop Firm Challenge configured for ${req.account_size:,.2f} ({req.drawdown_type.upper()})",
            "prop_firm": pf
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/propfirm/eod")
def process_propfirm_eod(req: PropFirmEODRequest) -> Dict[str, Any]:
    """Completes simulated trading day, recalculates EOD trailing floor & evaluation progress."""
    try:
        pf = simulator.process_prop_firm_eod(
            date_str=req.date or "",
            day_pnl=req.day_pnl,
            trades_count=req.trades_count,
            client_prop_firm=req.prop_firm
        )
        return {
            "status": "success",
            "prop_firm": pf
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/propfirm/activate-funded")
def activate_funded(req: PropFirmFundedRequest) -> Dict[str, Any]:
    """Transitions a cleared evaluation into an active Funded Account with chosen consistency rule."""
    try:
        pf = simulator.activate_funded_account(consistency_rule_pct=req.consistency_rule_pct)
        return {
            "status": "success",
            "message": f"Funded Account activated with {req.consistency_rule_pct}% consistency rule!",
            "prop_firm": pf
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/propfirm/payout")
def request_payout(req: PropFirmPayoutRequest) -> Dict[str, Any]:
    """Processes simulated payout request from funded account profits."""
    try:
        res = simulator.request_simulated_payout(amount=req.amount)
        return {
            "status": "success",
            "message": f"Simulated payout of ${req.amount:,.2f} approved and deducted from funded balance!",
            "payout": res["payout"],
            "prop_firm": res["prop_firm"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/propfirm/reset")
def reset_propfirm() -> Dict[str, Any]:
    """Resets the Prop Firm Challenge back to default starting evaluation."""
    pf = simulator.setup_prop_firm(
        account_size=50000.0,
        drawdown_type="eod_trailing",
        max_dd_pct=5.0,
        dll_pct=3.0,
        target_pct=6.0,
        min_days=2
    )
    return {
        "status": "success",
        "message": "Prop firm challenge reset to default $50,000 evaluation.",
        "prop_firm": pf
    }
