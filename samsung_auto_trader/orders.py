"""Order submission (cash buy/sell, limit orders only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import config
from api_client import APIClient
from logger import get_logger

logger = get_logger(__name__)

ORDER_PATH = "/uapi/domestic-stock/v1/trading/order-cash"

# KRX tick size (호가단위): minimum price increment a limit order price must
# be a multiple of, banded by price level. (upper_bound_exclusive, tick_size)
_TICK_BANDS = [
    (2_000, 1),
    (5_000, 5),
    (20_000, 10),
    (50_000, 50),
    (200_000, 100),
    (500_000, 500),
    (float("inf"), 1_000),
]


def _round_to_tick(price: int) -> int:
    """Snap a price to the nearest valid KRX tick (호가단위) for its price band."""
    for upper_bound, tick in _TICK_BANDS:
        if price < upper_bound:
            remainder = price % tick
            if remainder == 0:
                return price
            if remainder * 2 >= tick:
                return price + (tick - remainder)
            return price - remainder
    return price


@dataclass
class OrderResult:
    side: str
    price: int
    quantity: int
    order_no: Optional[str]
    raw: dict[str, Any]


def _submit_order(client: APIClient, side: str, price: int, quantity: int, stock_code: str) -> OrderResult:
    tr_id = config.TR_ID_ORDER_BUY_MOCK if side == "buy" else config.TR_ID_ORDER_SELL_MOCK
    tick_price = _round_to_tick(price)
    if tick_price != price:
        logger.info("Adjusted %s price from %d to %d to match KRX tick size.", side, price, tick_price)
    price = tick_price
    body = {
        "CANO": client.cano,
        "ACNT_PRDT_CD": client.acnt_prdt_cd,
        "PDNO": stock_code,
        "ORD_DVSN": config.ORDER_DIVISION_LIMIT,
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
        "EXCG_ID_DVSN_CD": config.EXCHANGE_ID_DIVISION_CODE,
        "SLL_TYPE": config.SELL_TYPE_NORMAL if side == "sell" else "",
        "CNDT_PRIC": "",
    }
    logger.info("Submitting %s order: qty=%d price=%d stock=%s", side, quantity, price, stock_code)
    data = client.post(ORDER_PATH, tr_id, body)
    output = data.get("output") or {}
    order_no = output.get(config.FIELD_ORDER_NO)
    logger.info("%s order accepted, order_no=%s", side, order_no)
    return OrderResult(side=side, price=price, quantity=quantity, order_no=order_no, raw=data)


def place_buy_order(
    client: APIClient,
    price: int,
    quantity: int = config.ORDER_QUANTITY,
    stock_code: str = config.STOCK_CODE,
) -> OrderResult:
    return _submit_order(client, "buy", price, quantity, stock_code)


def place_sell_order(
    client: APIClient,
    price: int,
    quantity: int = config.ORDER_QUANTITY,
    stock_code: str = config.STOCK_CODE,
) -> OrderResult:
    return _submit_order(client, "sell", price, quantity, stock_code)
