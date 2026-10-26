from __future__ import annotations
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .simulator_service import SimulatorService
from .instruments import INSTRUMENTS, INDEX_SYMBOLS, STOCK_SYMBOLS, get_instrument_config
from .options_math import black_scholes_price, calculate_time_to_expiry, estimate_option_bar_extremes

router = APIRouter(prefix="/api/game", tags=["game"])
simulator = SimulatorService()


class SessionCreateRequest(BaseModel):
    mode: str = "index"  # 'index' or 'stock'
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


@router.get("/config")
def get_game_config() -> Dict[str, Any]:
    """Retrieve game configuration, instruments, and saved player state."""
    state = simulator.load_game_state()
    return {
        "status": "success",
        "state": state,
        "indices": [INSTRUMENTS[s] for s in INDEX_SYMBOLS],
        "stocks": [INSTRUMENTS[s] for s in STOCK_SYMBOLS],
    }


@router.post("/session")
def create_game_session(req: SessionCreateRequest) -> Dict[str, Any]:
    """Initialize a new trading game session with random day historical data."""
    try:
        session = simulator.create_session(
            mode=req.mode,
            symbol=req.symbol,
            date=req.date,
            blind_mode=req.blind_mode
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
    
    # Update balance
    state["current_balance"] = round(state["current_balance"] + req.pnl, 2)
    state["all_time_pnl"] = round(state["all_time_pnl"] + req.pnl, 2)
    state["trades_count"] += 1
    
    if req.pnl > 0:
        state["wins"] += 1
        xp_gain = int(max(50, req.pnl / 100))
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
        "xp_gained": xp_gain,
        "new_balance": state["current_balance"],
        "rank": state["rank"],
        "state": state
    }


@router.post("/reset-account")
def reset_account(req: ResetAccountRequest) -> Dict[str, Any]:
    """Resets virtual starting capital and performance history."""
    bal = max(10000.0, req.starting_balance)
    state = {
        "starting_balance": bal,
        "current_balance": bal,
        "all_time_pnl": 0.0,
        "xp": 0,
        "rank": "Floor Trader",
        "trades_count": 0,
        "wins": 0,
        "losses": 0,
        "sound_enabled": True,
        "blind_mode": False,
        "trade_history": []
    }
    simulator.save_game_state(state)
    return {
        "status": "success",
        "message": f"Account reset with ₹{bal:,.2f} starting capital",
        "state": state
    }
