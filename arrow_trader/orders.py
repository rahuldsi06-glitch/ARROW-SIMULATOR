from __future__ import annotations
from typing import Dict, Any, List, Optional, Union
from pyarrow_client import (
    Exchange,
    OrderType,
    ProductType,
    TransactionType,
    Variety,
    Retention,
)
from .client_manager import ArrowClientManager


def parse_exchange(ex: Union[str, Exchange]) -> Exchange:
    if isinstance(ex, Exchange):
        return ex
    name = str(ex).strip().upper()
    return getattr(Exchange, name, Exchange.NSE)


def parse_order_type(ot: Union[str, OrderType]) -> OrderType:
    if isinstance(ot, OrderType):
        return ot
    name = str(ot).strip().upper()
    if name in ("MKT", "MARKET"):
        return OrderType.MARKET
    elif name in ("LMT", "LIMIT"):
        return OrderType.LIMIT
    elif name in ("SL", "SL_LMT", "STOP_LOSS_LIMIT"):
        return OrderType.STOP_LOSS_LIMIT
    elif name in ("SL_MKT", "STOP_LOSS_MARKET"):
        return OrderType.STOP_LOSS_MARKET
    return getattr(OrderType, name, OrderType.LIMIT)


def parse_product_type(pt: Union[str, ProductType]) -> ProductType:
    if isinstance(pt, ProductType):
        return pt
    name = str(pt).strip().upper()
    return getattr(ProductType, name, ProductType.CNC)


def parse_transaction_type(tt: Union[str, TransactionType]) -> TransactionType:
    if isinstance(tt, TransactionType):
        return tt
    name = str(tt).strip().upper()
    if name in ("B", "BUY"):
        return TransactionType.BUY
    elif name in ("S", "SELL"):
        return TransactionType.SELL
    return getattr(TransactionType, name, TransactionType.BUY)


def parse_validity(val: Union[str, Retention]) -> Retention:
    if isinstance(val, Retention):
        return val
    name = str(val).strip().upper()
    return getattr(Retention, name, Retention.DAY)


class OrderService:
    def __init__(self, manager: ArrowClientManager = None):
        self.manager = manager or ArrowClientManager.get_instance()

    def get_order_book(self) -> List[Dict[str, Any]]:
        client = self.manager.get_client()
        orders = client.get_order_book()
        if isinstance(orders, list):
            return orders
        elif isinstance(orders, dict):
            return orders.get("data", orders.get("orders", []))
        return []

    def get_trade_book(self) -> List[Dict[str, Any]]:
        client = self.manager.get_client()
        trades = client.get_trade_book()
        if isinstance(trades, list):
            return trades
        elif isinstance(trades, dict):
            return trades.get("data", trades.get("trades", []))
        return []

    def get_order_details(self, order_id: str) -> List[Dict[str, Any]]:
        client = self.manager.get_client()
        return client.get_order_details(order_id=order_id)

    def place_order(
        self,
        symbol: str,
        quantity: int,
        price: float = 0.0,
        exchange: Union[str, Exchange] = Exchange.NSE,
        transaction_type: Union[str, TransactionType] = TransactionType.BUY,
        order_type: Union[str, OrderType] = OrderType.LIMIT,
        product: Union[str, ProductType] = ProductType.CNC,
        disclosed_quantity: int = 0,
        trigger_price: float = 0.0,
        variety: Union[str, Variety] = Variety.REGULAR,
        validity: Union[str, Retention] = Retention.DAY,
        remarks: Optional[str] = None,
        mpp: bool = False,
    ) -> str:
        """
        Places a new order via ArrowClient.
        Returns the created order ID.
        """
        client = self.manager.get_client()
        ex = parse_exchange(exchange)
        tt = parse_transaction_type(transaction_type)
        ot = parse_order_type(order_type)
        pt = parse_product_type(product)
        var = Variety.COVER if str(variety).upper() == "COVER" else Variety.REGULAR
        val = parse_validity(validity)

        kwargs = {
            "exchange": ex,
            "symbol": symbol.strip().upper(),
            "quantity": int(quantity),
            "disclosed_quantity": int(disclosed_quantity),
            "product": pt,
            "order_type": ot,
            "variety": var,
            "transaction_type": tt,
            "price": float(price),
            "validity": val,
        }

        if trigger_price > 0:
            kwargs["trigger_price"] = float(trigger_price)
        if remarks:
            kwargs["remarks"] = str(remarks)[:16]
        if mpp:
            kwargs["mpp"] = True

        return client.place_order(**kwargs)

    def modify_order(
        self,
        order_id: str,
        symbol: str,
        quantity: int,
        price: float,
        exchange: Union[str, Exchange] = Exchange.NSE,
        transaction_type: Union[str, TransactionType] = TransactionType.BUY,
        order_type: Union[str, OrderType] = OrderType.LIMIT,
        product: Union[str, ProductType] = ProductType.CNC,
        disclosed_quantity: int = 0,
        validity: Union[str, Retention] = Retention.DAY,
        trigger_price: float = 0.0,
        remarks: Optional[str] = None,
        mpp: bool = False,
    ) -> str:
        client = self.manager.get_client()
        ex = parse_exchange(exchange)
        tt = parse_transaction_type(transaction_type)
        ot = parse_order_type(order_type)
        pt = parse_product_type(product)
        val = parse_validity(validity)

        kwargs = {
            "order_id": str(order_id),
            "exchange": ex,
            "symbol": symbol.strip().upper(),
            "quantity": int(quantity),
            "price": float(price),
            "disclosed_qty": int(disclosed_quantity),
            "product": pt,
            "transaction_type": tt,
            "order_type": ot,
            "validity": val,
        }
        if trigger_price > 0:
            kwargs["trigger_price"] = float(trigger_price)
        if remarks:
            kwargs["remarks"] = str(remarks)[:16]
        if mpp:
            kwargs["mpp"] = True

        return client.modify_order(**kwargs)

    def cancel_order(self, order_id: str) -> str:
        client = self.manager.get_client()
        return client.cancel_order(order_id=str(order_id))

    def cancel_all_orders(self) -> List[Any]:
        client = self.manager.get_client()
        return client.cancel_all_orders()

    def calculate_margin(
        self,
        symbol: str,
        quantity: int,
        price: float,
        exchange: Union[str, Exchange] = Exchange.NSE,
        transaction_type: Union[str, TransactionType] = TransactionType.BUY,
        order_type: Union[str, OrderType] = OrderType.LIMIT,
        product: Union[str, ProductType] = ProductType.CNC,
        include_positions: bool = False,
    ) -> Dict[str, Any]:
        client = self.manager.get_client()
        return client.order_margin(
            exchange=parse_exchange(exchange),
            symbol=symbol.strip().upper(),
            quantity=int(quantity),
            product=parse_product_type(product),
            order_type=parse_order_type(order_type),
            transaction_type=parse_transaction_type(transaction_type),
            price=float(price),
            include_positions=include_positions,
        )
