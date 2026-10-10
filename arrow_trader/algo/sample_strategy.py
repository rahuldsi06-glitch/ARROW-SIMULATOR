from __future__ import annotations
from typing import Dict, Any, List, Optional
from .base import BaseStrategy


class PriceMomentumStrategy(BaseStrategy):
    """
    Sample Momentum Strategy:
    Monitors LTP changes. If price moves upwards by `threshold_pct`, signals a buy.
    Supports paper_trading mode (simulation without firing actual broker orders)
    or live trading mode.
    """

    def __init__(
        self,
        name: str = "Momentum_Demo",
        symbols: Optional[List[str]] = None,
        tokens: Optional[List[int]] = None,
        threshold_pct: float = 0.5,
        target_profit_pct: float = 1.0,
        stop_loss_pct: float = 0.5,
        quantity: int = 1,
        paper_trading: bool = True,
    ):
        symbols = symbols or ["RELIANCE-EQ"]
        super().__init__(
            name=name,
            symbols=symbols,
            tokens=tokens,
            exchange="NSE",
            params={
                "threshold_pct": threshold_pct,
                "target_profit_pct": target_profit_pct,
                "stop_loss_pct": stop_loss_pct,
                "quantity": quantity,
                "paper_trading": paper_trading,
            },
        )
        self.entry_price: Optional[float] = None
        self.last_ltp: Optional[float] = None
        self.position: int = 0
        self.orders_history: List[Dict[str, Any]] = []

    def on_start(self) -> None:
        mode = "PAPER TRADING (Simulated)" if self.params.get("paper_trading") else "LIVE BROKER"
        self.log(f"Initialized in {mode} mode for {self.symbols}")

    def on_tick(self, tick: Any) -> None:
        ltp = getattr(tick, "ltp", None)
        if not ltp or ltp <= 0:
            return

        self.last_ltp = ltp

        # If flat (no open position), check for entry condition
        if self.position == 0:
            net_change = getattr(tick, "net_change", 0.0)
            threshold = self.params.get("threshold_pct", 0.5)

            if net_change >= threshold:
                qty = self.params.get("quantity", 1)
                self.log(f"Momentum trigger: Net change {net_change:.2f}% >= {threshold}%. Buying {qty} shares @ ₹{ltp}")
                self.position = qty
                self.entry_price = ltp

                if not self.params.get("paper_trading"):
                    try:
                        order_id = self.buy(self.symbols[0], qty, ltp, order_type="LIMIT", product="MIS")
                        self.log(f"Live order placed: ID {order_id}")
                    except Exception as e:
                        self.log(f"Failed to place live order: {e}", level="ERROR")
                        self.position = 0
                        self.entry_price = None

        # If in position, check for Target Profit or Stop Loss
        elif self.position > 0 and self.entry_price:
            pnl_pct = ((ltp - self.entry_price) / self.entry_price) * 100
            target = self.params.get("target_profit_pct", 1.0)
            sl = self.params.get("stop_loss_pct", 0.5)

            if pnl_pct >= target:
                self.log(f"Target profit hit (+{pnl_pct:.2f}%). Closing position @ ₹{ltp}")
                self._close_position(ltp)
            elif pnl_pct <= -sl:
                self.log(f"Stop loss hit ({pnl_pct:.2f}%). Closing position @ ₹{ltp}")
                self._close_position(ltp)

    def _close_position(self, current_price: float) -> None:
        qty = self.position
        if not self.params.get("paper_trading"):
            try:
                order_id = self.sell(self.symbols[0], qty, current_price, order_type="LIMIT", product="MIS")
                self.log(f"Live exit order placed: ID {order_id}")
            except Exception as e:
                self.log(f"Failed to place exit order: {e}", level="ERROR")
        self.position = 0
        self.entry_price = None

    def on_stop(self) -> None:
        self.log(f"Strategy stopped. Final position: {self.position}, Last LTP: ₹{self.last_ltp}")
