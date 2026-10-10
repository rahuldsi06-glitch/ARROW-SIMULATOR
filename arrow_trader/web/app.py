from __future__ import annotations
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..config import Config
from ..client_manager import ArrowClientManager
from ..portfolio import PortfolioService
from ..orders import OrderService
from ..market import MarketService
from ..stream import StreamManager
from ..algo import AlgoEngine, PriceMomentumStrategy
from ..game.routes import router as game_router

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Arrow.Trade Algo Trading Interface", version="1.0.0")

# Mount game routes
app.include_router(game_router)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")



# Pydantic models for incoming requests
class LoginRequest(BaseModel):
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    user_id: str
    password: str
    totp_secret: str
    save_env: bool = True


class SetTokenRequest(BaseModel):
    token: str


class ConfigRequest(BaseModel):
    app_id: str
    app_secret: Optional[str] = None
    root_url: Optional[str] = None


class OrderPlaceRequest(BaseModel):
    symbol: str
    quantity: int
    price: float = 0.0
    exchange: str = "NSE"
    transaction_type: str = "BUY"
    order_type: str = "LIMIT"
    product: str = "MIS"
    trigger_price: float = 0.0
    remarks: Optional[str] = None


class OrderCancelRequest(BaseModel):
    order_id: str


class MarginCheckRequest(BaseModel):
    symbol: str
    quantity: int
    price: float
    exchange: str = "NSE"
    transaction_type: str = "BUY"
    order_type: str = "LIMIT"
    product: str = "CNC"


# WebSocket connection manager
class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def broadcast_tick(self, tick: Any):
        if not self.active_connections:
            return

        tick_dict = {
            "token": getattr(tick, "token", 0),
            "ltp": getattr(tick, "ltp", 0.0),
            "net_change": getattr(tick, "net_change", 0.0),
            "open": getattr(tick, "open", 0.0),
            "high": getattr(tick, "high", 0.0),
            "low": getattr(tick, "low", 0.0),
            "close": getattr(tick, "close", 0.0),
            "volume": getattr(tick, "volume", 0),
        }
        msg = json.dumps({"type": "tick", "data": tick_dict})

        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_broadcast(msg), self._loop)

    async def _async_broadcast(self, msg: str):
        disconnected = []
        for ws in self.active_connections:
            try:
                await ws.send_text(msg)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


ws_manager = WebSocketManager()


@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    ws_manager.set_loop(loop)
    # Register broadcast listener to stream manager
    StreamManager.get_instance().add_tick_listener(ws_manager.broadcast_tick)
    # Ensure sample strategy is registered in algo engine
    engine = AlgoEngine.get_instance()
    if not engine.strategies:
        engine.register_strategy(PriceMomentumStrategy(paper_trading=True))


@app.get("/")
def get_root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/game")
@app.get("/simulator")
def get_game_page():
    return FileResponse(STATIC_DIR / "game.html")


@app.get("/callback")
@app.get("/arrow/callback")
def oauth_callback(request_token: Optional[str] = None, request: Request = None):
    manager = ArrowClientManager.get_instance()
    # Check query params for request-token (with hyphen or underscore)
    token = request_token
    if not token and request:
        token = (
            request.query_params.get("request-token")
            or request.query_params.get("request_token")
            or request.query_params.get("token")
        )
    if not token:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<h2>Error: No request-token found in URL parameters.</h2>", status_code=400)

    try:
        user_data = manager.complete_web_login(request_token=token)
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            f"""
            <!DOCTYPE html>
            <html>
            <head><title>Arrow Trade - Auth Success</title></head>
            <body style="font-family: -apple-system, sans-serif; background: #0e1117; color: #f0f6fc; display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; margin:0;">
                <div style="background:#161b22; border:1px solid #30363d; border-radius:10px; padding:32px; text-align:center; max-width:400px;">
                    <h1 style="color:#22c55e; margin-bottom:10px;">✓ Logged In!</h1>
                    <p style="color:#8b949e;">Welcome, <strong style="color:#f0f6fc;">{user_data.get('name', 'Trader')}</strong></p>
                    <p style="color:#8b949e; font-size:13px;">User ID: <code style="color:#38bdf8;">{user_data.get('userID', '')}</code></p>
                    <p style="color:#8b949e; font-size:12px; margin-top:16px;">Session token validated and saved for 24 hours.</p>
                    <a href="/" style="display:inline-block; margin-top:20px; padding:10px 20px; background:#38bdf8; color:#000; text-decoration:none; border-radius:6px; font-weight:bold;">Go to Trading Dashboard →</a>
                </div>
            </body>
            </html>
            """
        )
    except Exception as e:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(f"<h2 style='color:red;'>Token Exchange Failed: {e}</h2>", status_code=400)



# ================================================================
# AUTH & CONFIG ENDPOINTS
# ================================================================

@app.get("/api/auth/status")
def get_auth_status():
    manager = ArrowClientManager.get_instance()
    is_auth, user_info, err = manager.is_authenticated()
    return {
        "authenticated": is_auth,
        "app_id": manager.app_id,
        "root_url": manager.root_url,
        "user": user_info,
        "error": err,
    }


@app.post("/api/auth/config")
def update_config(req: ConfigRequest):
    manager = ArrowClientManager.get_instance()
    manager.reconfigure(app_id=req.app_id, app_secret=req.app_secret, root_url=req.root_url)
    return {"status": "success", "message": "Config updated"}


@app.post("/api/auth/login")
def login(req: LoginRequest):
    manager = ArrowClientManager.get_instance()
    if req.app_id:
        manager.reconfigure(app_id=req.app_id, app_secret=req.app_secret)
    try:
        user_data = manager.auto_login(
            user_id=req.user_id,
            password=req.password,
            app_secret=req.app_secret or Config.get_app_secret(),
            totp_secret=req.totp_secret,
        )
        if req.save_env:
            if req.app_id:
                Config.save_env_var("ARROW_APP_ID", req.app_id)
            if req.app_secret:
                Config.save_env_var("ARROW_APP_SECRET", req.app_secret)
            Config.save_env_var("ARROW_USER_ID", req.user_id)
            Config.save_env_var("ARROW_PASSWORD", req.password)
            Config.save_env_var("ARROW_TOTP_SECRET", req.totp_secret)
        return {"status": "success", "user": user_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/set-token")
def set_token(req: SetTokenRequest):
    manager = ArrowClientManager.get_instance()
    try:
        manager.set_token(req.token)
        return {"status": "success", "message": "Token set and verified"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/logout")
def logout():
    manager = ArrowClientManager.get_instance()
    manager.logout()
    return {"status": "success", "message": "Logged out successfully"}


# ================================================================
# PORTFOLIO & ACCOUNT ENDPOINTS
# ================================================================

@app.get("/api/user/limits")
def get_user_limits():
    service = PortfolioService()
    try:
        return service.get_limits()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/portfolio/positions")
def get_positions():
    service = PortfolioService()
    try:
        return service.get_positions()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/portfolio/holdings")
def get_holdings():
    service = PortfolioService()
    try:
        return service.get_holdings()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ================================================================
# ORDERS ENDPOINTS
# ================================================================

@app.get("/api/orders/book")
def get_orders():
    service = OrderService()
    try:
        return service.get_order_book()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/orders/trades")
def get_trades():
    service = OrderService()
    try:
        return service.get_trade_book()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/orders/place")
def place_order(req: OrderPlaceRequest):
    service = OrderService()
    try:
        order_id = service.place_order(
            symbol=req.symbol,
            quantity=req.quantity,
            price=req.price,
            exchange=req.exchange,
            transaction_type=req.transaction_type,
            order_type=req.order_type,
            product=req.product,
            trigger_price=req.trigger_price,
            remarks=req.remarks,
        )
        return {"status": "success", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/orders/cancel")
def cancel_order(req: OrderCancelRequest):
    service = OrderService()
    try:
        res = service.cancel_order(req.order_id)
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/orders/cancel-all")
def cancel_all_orders():
    service = OrderService()
    try:
        res = service.cancel_all_orders()
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/orders/margin")
def check_margin(req: MarginCheckRequest):
    service = OrderService()
    try:
        return service.calculate_margin(
            symbol=req.symbol,
            quantity=req.quantity,
            price=req.price,
            exchange=req.exchange,
            transaction_type=req.transaction_type,
            order_type=req.order_type,
            product=req.product,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ================================================================
# MARKET DATA ENDPOINTS
# ================================================================

@app.get("/api/market/quote")
def get_quote(symbol: str, exchange: str = "NSE", mode: str = "FULL"):
    service = MarketService()
    try:
        return service.get_quote(symbol=symbol, exchange=exchange, mode=mode)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/market/indices")
def get_indices():
    service = MarketService()
    try:
        return service.get_index_list()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/market/candles")
def get_candles(token: str, exchange: str = "NSE", interval: str = "5min", from_time: Optional[str] = None, to_time: Optional[str] = None):
    service = MarketService()
    try:
        return service.get_candles(
            token=token,
            exchange=exchange,
            interval=interval,
            from_time=from_time,
            to_time=to_time,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ================================================================
# ALGO TRADING ENDPOINTS
# ================================================================

@app.get("/api/algo/list")
def list_algos():
    engine = AlgoEngine.get_instance()
    return engine.get_all_strategies()


@app.post("/api/algo/start")
def start_algo(name: str):
    engine = AlgoEngine.get_instance()
    try:
        res = engine.start_strategy(name)
        return {"status": "success", "started": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/algo/stop")
def stop_algo(name: str):
    engine = AlgoEngine.get_instance()
    try:
        res = engine.stop_strategy(name)
        return {"status": "success", "stopped": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ================================================================
# WEBSOCKET STREAM ROUTE
# ================================================================

@app.websocket("/ws/ticks")
async def websocket_ticks(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Receive commands from browser (e.g. subscribe to token)
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                action = data.get("action")
                if action == "subscribe":
                    tokens = data.get("tokens", [])
                    StreamManager.get_instance().subscribe(tokens)
                elif action == "unsubscribe":
                    tokens = data.get("tokens", [])
                    StreamManager.get_instance().unsubscribe(tokens)
            except Exception as e:
                logger.error(f"WebSocket incoming message error: {e}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
