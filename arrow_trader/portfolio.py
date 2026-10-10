from __future__ import annotations
from typing import Dict, Any, List
from .client_manager import ArrowClientManager


class PortfolioService:
    def __init__(self, manager: ArrowClientManager = None):
        self.manager = manager or ArrowClientManager.get_instance()

    def get_profile(self) -> Dict[str, Any]:
        client = self.manager.get_client()
        return client.get_user_details()

    def get_limits(self) -> Dict[str, Any]:
        client = self.manager.get_client()
        return client.get_user_limits()

    def get_positions(self) -> List[Dict[str, Any]]:
        client = self.manager.get_client()
        positions = client.get_positions()
        if isinstance(positions, list):
            return positions
        elif isinstance(positions, dict):
            # If wrapped in a data key
            return positions.get("data", positions.get("positions", []))
        return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        client = self.manager.get_client()
        holdings = client.get_holdings()
        if isinstance(holdings, list):
            return holdings
        elif isinstance(holdings, dict):
            return holdings.get("data", holdings.get("holdings", []))
        return []
