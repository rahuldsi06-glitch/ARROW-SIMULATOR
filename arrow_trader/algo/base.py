from __future__ import annotations
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..orders import OrderService
from ..market import MarketService

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    Base class for algorithmic trading strategies.
    Subclasses should implement on_tick(), on_start(), and on_stop().
    """

    def __init__(
        self,
        name: str,
        symbols: List[str],
        tokens: Optional[List[int]] = None,
        exchange: str = "NSE",
        params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.symbols = [s.upper() for s in symbols]
        self.tokens = tokens or []
        self.exchange = exchange
        self.params = params or {}
        self.is_running = False
        self.logs: List[Dict[str, Any]] = []

        self.orders = OrderService()
        self.market = MarketService()

    def log(self, message: str, level: str = "INFO") -> None:
        entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
        }
        self.logs.append(entry)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]
        logger.info(f"[{self.name}] {message}")

    def start(self) -> None:
        self.is_running = True
        self.log(f"Strategy '{self.name}' started.")
        self.on_start()

    def stop(self) -> None:
        self.is_running = False
        self.on_stop()
        self.log(f"Strategy '{self.name}' stopped.")

    def buy(
        self,
        symbol: str,
        quantity: int,
        price: float = 0.0,
        order_type: str = "LIMIT",
        product: str = "MIS",
    ) -> str:
        self.log(f"Placing BUY order: {quantity} x {symbol} @ {price} ({order_type}, {product})")
        return self.orders.place_order(
            symbol=symbol,
            quantity=quantity,
            price=price,
            exchange=self.exchange,
            transaction_type="BUY",
            order_type=order_type,
            product=product,
            remarks=f"algo-{self.name[:10]}",
        )

    def sell(
        self,
        symbol: str,
        quantity: int,
        price: float = 0.0,
        order_type: str = "LIMIT",
        product: str = "MIS",
    ) -> str:
        self.log(f"Placing SELL order: {quantity} x {symbol} @ {price} ({order_type}, {product})")
        return self.orders.place_order(
            symbol=symbol,
            quantity=quantity,
            price=price,
            exchange=self.exchange,
            transaction_type="SELL",
            order_type=order_type,
            product=product,
            remarks=f"algo-{self.name[:10]}",
        )

    def cancel(self, order_id: str) -> str:
        self.log(f"Cancelling order {order_id}")
        return self.orders.cancel_order(order_id)

    @abstractmethod
    def on_start(self) -> None:
        pass

    @abstractmethod
    def on_tick(self, tick: Any) -> None:
        pass

    def on_order_update(self, update: Dict[str, Any]) -> None:
        self.log(f"Order update: {update}")

    @abstractmethod
    def on_stop(self) -> None:
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "symbols": self.symbols,
            "tokens": self.tokens,
            "exchange": self.exchange,
            "is_running": self.is_running,
            "params": self.params,
            "recent_logs": self.logs[-20:],
        }
