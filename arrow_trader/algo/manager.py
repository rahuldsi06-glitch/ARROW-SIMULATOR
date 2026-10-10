from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from .base import BaseStrategy
from ..stream import StreamManager

logger = logging.getLogger(__name__)


class AlgoEngine:
    _instance: Optional[AlgoEngine] = None

    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.stream_manager = StreamManager.get_instance()
        self.stream_manager.add_tick_listener(self._handle_tick)
        self.stream_manager.add_order_listener(self._handle_order_update)

    @classmethod
    def get_instance(cls) -> AlgoEngine:
        if cls._instance is None:
            cls._instance = AlgoEngine()
        return cls._instance

    def register_strategy(self, strategy: BaseStrategy) -> None:
        self.strategies[strategy.name] = strategy
        logger.info(f"Registered strategy: {strategy.name}")

    def unregister_strategy(self, name: str) -> None:
        if name in self.strategies:
            if self.strategies[name].is_running:
                self.strategies[name].stop()
            del self.strategies[name]

    def start_strategy(self, name: str) -> bool:
        strategy = self.strategies.get(name)
        if not strategy:
            raise ValueError(f"Strategy '{name}' not found.")

        if not strategy.is_running:
            # Subscribe to tokens if provided
            if strategy.tokens:
                self.stream_manager.subscribe(strategy.tokens)
            strategy.start()
            return True
        return False

    def stop_strategy(self, name: str) -> bool:
        strategy = self.strategies.get(name)
        if not strategy:
            raise ValueError(f"Strategy '{name}' not found.")

        if strategy.is_running:
            strategy.stop()
            return True
        return False

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        return [strat.get_status() for strat in self.strategies.values()]

    def get_strategy_status(self, name: str) -> Optional[Dict[str, Any]]:
        strategy = self.strategies.get(name)
        return strategy.get_status() if strategy else None

    def _handle_tick(self, tick: Any) -> None:
        token = getattr(tick, "token", None)
        for strategy in self.strategies.values():
            if strategy.is_running:
                # If strategy has tokens specified, filter by tokens, else dispatch
                if not strategy.tokens or (token in strategy.tokens):
                    try:
                        strategy.on_tick(tick)
                    except Exception as e:
                        strategy.log(f"Error in on_tick: {e}", level="ERROR")

    def _handle_order_update(self, update: Dict[str, Any]) -> None:
        for strategy in self.strategies.values():
            if strategy.is_running:
                try:
                    strategy.on_order_update(update)
                except Exception as e:
                    strategy.log(f"Error in on_order_update: {e}", level="ERROR")
