"""Current price lookup for a single domestic stock."""

from __future__ import annotations

import config
from api_client import APIClient
from logger import get_logger

logger = get_logger(__name__)

PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"


def get_current_price(client: APIClient, stock_code: str = config.STOCK_CODE) -> int:
    """Return the current market price (KRW) for the given stock code."""
    params = {
        "FID_COND_MRKT_DIV_CODE": config.MARKET_DIV_CODE,
        "FID_INPUT_ISCD": stock_code,
    }
    data = client.get(PRICE_PATH, config.TR_ID_CURRENT_PRICE, params)
    price = int(data["output"][config.FIELD_CURRENT_PRICE])
    logger.info("Current price for %s: %s KRW", stock_code, price)
    return price
