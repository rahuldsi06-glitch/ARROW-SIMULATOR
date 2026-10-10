from __future__ import annotations
import logging
import threading
from typing import Dict, Any, List, Callable, Optional, Set
from pyarrow_client import ArrowStreams, DataMode
from .client_manager import ArrowClientManager

logger = logging.getLogger(__name__)


class StreamManager:
    _instance: Optional[StreamManager] = None

    def __init__(self, manager: ArrowClientManager = None):
        self.manager = manager or ArrowClientManager.get_instance()
        self.streams: Optional[ArrowStreams] = None
        self._is_connected = False
        self._subscribed_tokens: Set[int] = set()
        self._latest_ticks: Dict[int, Any] = {}
        self._tick_listeners: List[Callable[[Any], None]] = []
        self._order_listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> StreamManager:
        if cls._instance is None:
            cls._instance = StreamManager()
        return cls._instance

    def add_tick_listener(self, callback: Callable[[Any], None]) -> None:
        with self._lock:
            if callback not in self._tick_listeners:
                self._tick_listeners.append(callback)

    def remove_tick_listener(self, callback: Callable[[Any], None]) -> None:
        with self._lock:
            if callback in self._tick_listeners:
                self._tick_listeners.remove(callback)

    def add_order_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            if callback not in self._order_listeners:
                self._order_listeners.append(callback)

    def remove_order_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            if callback in self._order_listeners:
                self._order_listeners.remove(callback)

    def _on_tick(self, tick: Any) -> None:
        token = getattr(tick, "token", None)
        if token is not None:
            with self._lock:
                self._latest_ticks[token] = tick

        # Dispatch to listeners
        listeners = list(self._tick_listeners)
        for listener in listeners:
            try:
                listener(tick)
            except Exception as e:
                logger.error(f"Error in tick listener: {e}")

    def _on_order_update(self, order_update: Dict[str, Any]) -> None:
        logger.info(f"Order update received: {order_update}")
        listeners = list(self._order_listeners)
        for listener in listeners:
            try:
                listener(order_update)
            except Exception as e:
                logger.error(f"Error in order listener: {e}")

    def connect(self, debug: bool = False) -> None:
        if self._is_connected and self.streams:
            return

        self.streams = self.manager.create_streams(debug=debug)

        def on_connect():
            self._is_connected = True
            logger.info("Arrow WebSocket stream connected")
            # Resubscribe tokens if any
            with self._lock:
                if self._subscribed_tokens and self.streams:
                    tokens_list = list(self._subscribed_tokens)
                    self.streams.subscribe_market_data(DataMode.QUOTE, tokens_list)

        def on_disconnect():
            self._is_connected = False
            logger.warning("Arrow WebSocket stream disconnected")

        self.streams.data_stream.on_ticks = self._on_tick
        self.streams.data_stream.on_connect = on_connect
        self.streams.data_stream.on_disconnect = on_disconnect
        self.streams.order_stream.on_order_update = self._on_order_update

        # Connect both market data and order stream
        self.streams.connect_all()
        self._is_connected = True

    def disconnect(self) -> None:
        if self.streams:
            try:
                self.streams.disconnect_all()
            except Exception as e:
                logger.warning(f"Error disconnecting streams: {e}")
            self.streams = None
            self._is_connected = False

    def subscribe(self, tokens: List[int], mode: DataMode = DataMode.QUOTE) -> None:
        int_tokens = [int(t) for t in tokens]
        with self._lock:
            self._subscribed_tokens.update(int_tokens)

        if not self._is_connected:
            self.connect()
        elif self.streams:
            self.streams.subscribe_market_data(mode, int_tokens)

    def unsubscribe(self, tokens: List[int], mode: DataMode = DataMode.QUOTE) -> None:
        int_tokens = [int(t) for t in tokens]
        with self._lock:
            for t in int_tokens:
                self._subscribed_tokens.discard(t)

        if self.streams and self._is_connected:
            self.streams.unsubscribe_market_data(mode, int_tokens)

    def get_latest_tick(self, token: int) -> Optional[Any]:
        with self._lock:
            return self._latest_ticks.get(int(token))

    def get_all_latest_ticks(self) -> Dict[int, Any]:
        with self._lock:
            return dict(self._latest_ticks)

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def subscribed_tokens(self) -> List[int]:
        with self._lock:
            return list(self._subscribed_tokens)
