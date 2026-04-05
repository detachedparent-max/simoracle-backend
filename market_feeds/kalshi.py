"""
Kalshi API client for real-time market feed and trading
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
from config import KALSHI_API_KEY, KALSHI_USERNAME, KALSHI_PASSWORD

logger = logging.getLogger(__name__)


class KalshiClient:
    """Async HTTP client for Kalshi API"""

    BASE_URL = "https://api.kalshi.com/v1"

    def __init__(self, api_key: str = "", username: str = "", password: str = ""):
        self.api_key = api_key or KALSHI_API_KEY
        self.username = username or KALSHI_USERNAME
        self.password = password or KALSHI_PASSWORD
        self.client = httpx.AsyncClient(timeout=10.0)
        self.auth_token = None

    async def authenticate(self) -> bool:
        """Authenticate and get auth token"""
        try:
            response = await self.client.post(
                f"{self.BASE_URL}/login",
                json={
                    "username": self.username,
                    "password": self.password,
                }
            )
            response.raise_for_status()
            data = response.json()
            self.auth_token = data.get("token")
            return bool(self.auth_token)
        except Exception as e:
            logger.error(f"Kalshi auth failed: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            "Content-Type": "application/json",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def get_markets(self, status: str = "open") -> List[Dict[str, Any]]:
        """
        Get list of markets
        status: 'open', 'closed', 'all'
        """
        try:
            params = {"status": status}
            response = await self.client.get(
                f"{self.BASE_URL}/markets",
                headers=self._get_headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("markets", [])
        except Exception as e:
            logger.error(f"Get markets failed: {e}")
            return []

    async def get_market(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific market"""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/markets/{market_id}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json().get("market")
        except Exception as e:
            logger.error(f"Get market {market_id} failed: {e}")
            return None

    async def get_orderbook(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get orderbook for a market"""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/markets/{market_id}/orderbook",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json().get("orderbook")
        except Exception as e:
            logger.error(f"Get orderbook {market_id} failed: {e}")
            return None

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get user's current positions"""
        if not self.auth_token:
            logger.warning("Not authenticated, cannot fetch positions")
            return []

        try:
            response = await self.client.get(
                f"{self.BASE_URL}/portfolio/positions",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json().get("positions", [])
        except Exception as e:
            logger.error(f"Get positions failed: {e}")
            return []

    async def place_order(
        self,
        market_id: str,
        side: str,  # 'BUY' or 'SELL'
        quantity: int,
        yes_price: Optional[float] = None,
        no_price: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Place an order
        side: 'BUY_YES', 'BUY_NO', 'SELL_YES', 'SELL_NO'
        """
        if not self.auth_token:
            logger.warning("Not authenticated, cannot place order")
            return None

        try:
            payload = {
                "market_id": market_id,
                "side": side,
                "quantity": quantity,
            }

            if yes_price is not None:
                payload["yes_price"] = yes_price
            if no_price is not None:
                payload["no_price"] = no_price

            response = await self.client.post(
                f"{self.BASE_URL}/orders",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json().get("order")
        except Exception as e:
            logger.error(f"Place order failed: {e}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        if not self.auth_token:
            logger.warning("Not authenticated, cannot cancel order")
            return False

        try:
            response = await self.client.delete(
                f"{self.BASE_URL}/orders/{order_id}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Cancel order failed: {e}")
            return False

    async def get_order_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get user's order history"""
        if not self.auth_token:
            logger.warning("Not authenticated, cannot fetch order history")
            return []

        try:
            params = {"limit": limit}
            response = await self.client.get(
                f"{self.BASE_URL}/orders",
                headers=self._get_headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json().get("orders", [])
        except Exception as e:
            logger.error(f"Get order history failed: {e}")
            return []

    async def stream_market_updates(self, market_ids: List[str]) -> None:
        """Stream market price updates (WebSocket preferred, polling fallback)"""
        # For MVP, use polling. In production, use WebSocket
        while True:
            for market_id in market_ids:
                market = await self.get_market(market_id)
                if market:
                    logger.info(f"Market {market_id}: YES=${market.get('yes_price'):.2f} NO=${market.get('no_price'):.2f}")

            await asyncio.sleep(5)  # Poll every 5 seconds

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Singleton for easy access
_kalshi_client = None


async def get_kalshi_client() -> KalshiClient:
    """Get or create Kalshi client"""
    global _kalshi_client
    if _kalshi_client is None:
        _kalshi_client = KalshiClient()
        if not await _kalshi_client.authenticate():
            logger.warning("Kalshi authentication failed - read-only mode")
    return _kalshi_client
