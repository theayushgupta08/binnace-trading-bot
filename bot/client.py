"""Low-level Binance Futures Testnet HTTP client.

Handles authentication (HMAC-SHA256 signing), request construction,
response parsing, and error translation.  All outgoing requests and
incoming responses are logged for debugging.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger("bot.client")

# Binance Futures Testnet base URL
BASE_URL = "https://demo-fapi.binance.com"

# HTTP timeout in seconds
REQUEST_TIMEOUT = 15


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, status_code: int, code: int, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"[HTTP {status_code}] Binance error {code}: {message}")


class BinanceClient:
    """Thin wrapper around the Binance Futures Testnet REST API.

    Parameters
    ----------
    api_key : str
        Testnet API key.
    api_secret : str
        Testnet API secret.
    base_url : str, optional
        Override the default testnet base URL.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = BASE_URL,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("API key and secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({
            "X-MBX-APIKEY": self._api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })

    # ------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add ``timestamp`` and ``signature`` to *params*."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    # ------------------------------------------------------------------
    # Generic HTTP helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """Send an HTTP request and return the JSON response.

        Raises
        ------
        BinanceAPIError
            If the API returns a non-2xx status with an error body.
        requests.RequestException
            On network-level failures.
        """
        params = dict(params or {})
        if signed:
            params = self._sign(params)

        url = f"{self._base_url}{path}"
        logger.debug("REQUEST  %s %s params=%s", method.upper(), url, params)

        response = self._session.request(
            method, url, params=params, timeout=REQUEST_TIMEOUT
        )

        # Log raw response
        logger.debug(
            "RESPONSE %s %s status=%s body=%s",
            method.upper(),
            url,
            response.status_code,
            response.text[:2000],
        )

        # Handle API-level errors
        if response.status_code >= 400:
            try:
                body = response.json()
                raise BinanceAPIError(
                    status_code=response.status_code,
                    code=body.get("code", -1),
                    message=body.get("msg", response.text),
                )
            except (ValueError, KeyError):
                raise BinanceAPIError(
                    status_code=response.status_code,
                    code=-1,
                    message=response.text,
                )

        return response.json()

    # ------------------------------------------------------------------
    # Public endpoints
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Test connectivity to the REST API.

        Returns ``True`` if the server responds with ``{}``.
        """
        result = self._request("GET", "/fapi/v1/ping")
        logger.info("Ping successful: %s", result)
        return result == {}

    # ------------------------------------------------------------------
    # Trading endpoints
    # ------------------------------------------------------------------

    def place_order(self, **kwargs: Any) -> Dict[str, Any]:
        """Place a new futures order (POST /fapi/v1/order).

        All keyword arguments are forwarded as request parameters.
        Authentication (timestamp + signature) is handled automatically.

        Returns
        -------
        dict
            The order response from Binance.
        """
        return self._request("POST", "/fapi/v1/order", params=kwargs, signed=True)
