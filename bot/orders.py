"""Order placement logic.

Bridges validated ``OrderParams`` and the low-level ``BinanceClient``
to submit MARKET and LIMIT orders with consistent logging.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from bot.client import BinanceClient
from bot.validators import OrderParams

logger = logging.getLogger("bot.orders")


def place_order(client: BinanceClient, params: OrderParams) -> Dict[str, Any]:
    """Build the order payload, submit it, and return the API response.

    Parameters
    ----------
    client : BinanceClient
        Authenticated client instance.
    params : OrderParams
        Validated order parameters.

    Returns
    -------
    dict
        Raw JSON response from Binance.

    Raises
    ------
    bot.client.BinanceAPIError
        On API-level errors.
    requests.RequestException
        On network-level failures.
    """
    payload: Dict[str, Any] = {
        "symbol": params.symbol,
        "side": params.side,
        "type": params.order_type,
        "quantity": str(params.quantity),
        "newOrderRespType": "RESULT",
    }

    if params.order_type == "LIMIT":
        payload["price"] = str(params.price)
        payload["timeInForce"] = "GTC"

    logger.info(
        "Placing %s %s order: symbol=%s qty=%s%s",
        params.side,
        params.order_type,
        params.symbol,
        params.quantity,
        f" price={params.price}" if params.price else "",
    )

    response = client.place_order(**payload)

    logger.info(
        "Order response: orderId=%s status=%s executedQty=%s avgPrice=%s",
        response.get("orderId"),
        response.get("status"),
        response.get("executedQty"),
        response.get("avgPrice"),
    )

    return response
