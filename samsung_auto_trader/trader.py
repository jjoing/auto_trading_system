"""Trading loop: poll price, place a buy/sell price bracket, then verify execution.

Polling-based only (no websocket). Runs strictly within the configured
trading window and stops automatically once the window ends.
"""

from __future__ import annotations

import time as time_module
from datetime import datetime

import config
from account import get_account_snapshot
from api_client import APIClient
from market_data import get_current_price
from orders import place_buy_order, place_sell_order
from logger import get_logger

logger = get_logger(__name__)


def _within_trading_window(now: datetime) -> bool:
    return config.TRADING_START <= now.time() <= config.TRADING_END


def _seconds_until_start(now: datetime) -> float:
    target = now.replace(
        hour=config.TRADING_START.hour,
        minute=config.TRADING_START.minute,
        second=0,
        microsecond=0,
    )
    return max(0.0, (target - now).total_seconds())


def run_one_cycle(client: APIClient) -> None:
    """Check price, place a buy+sell bracket around it, then verify execution."""
    price = get_current_price(client)

    logger.info("Checking holdings before placing orders.")
    before = get_account_snapshot(client)

    buy_price = price - config.ORDER_PRICE_OFFSET_KRW

    if before.holding_quantity < config.MAX_POSITION_QUANTITY:
        place_buy_order(client, buy_price)
    else:
        logger.info(
            "Skipping buy order: position at cap (%d shares held, max %d).",
            before.holding_quantity,
            config.MAX_POSITION_QUANTITY,
        )

    if before.orderable_quantity >= config.ORDER_QUANTITY:
        # Never quote a sell below cost: take whichever is higher, the usual
        # current-price offset or a guaranteed margin over the average buy price.
        sell_price = max(
            price + config.ORDER_PRICE_OFFSET_KRW,
            before.avg_purchase_price_krw + config.MIN_PROFIT_MARGIN_KRW,
        )
        place_sell_order(client, sell_price)
    else:
        logger.info(
            "Skipping sell order: only %d share(s) sellable (already reserved by pending sell orders), need %d.",
            before.orderable_quantity,
            config.ORDER_QUANTITY,
        )

    logger.info("Waiting %d seconds before re-checking holdings.", config.POST_ORDER_SETTLE_SECONDS)
    time_module.sleep(config.POST_ORDER_SETTLE_SECONDS)

    logger.info("Checking holdings after placing orders.")
    after = get_account_snapshot(client)

    if after.holding_quantity != before.holding_quantity or after.cash_balance_krw != before.cash_balance_krw:
        logger.info("Execution detected: holdings/cash changed since before the orders.")
    else:
        logger.info("No execution detected yet (holdings/cash unchanged).")


def run_trading_loop(client: APIClient) -> None:
    """Run run_one_cycle() repeatedly, only inside the configured trading window."""
    logger.info("Configured trading window: %s - %s", config.TRADING_START, config.TRADING_END)

    now = datetime.now()
    if now.time() > config.TRADING_END:
        logger.info("Current time %s is after the trading window end; nothing to do today.", now.time())
        return

    if now.time() < config.TRADING_START:
        wait_seconds = _seconds_until_start(now)
        logger.info("Waiting %.0f seconds for the trading window to start at %s.", wait_seconds, config.TRADING_START)
        time_module.sleep(wait_seconds)

    logger.info("Trading window started.")
    while _within_trading_window(datetime.now()):
        try:
            run_one_cycle(client)
        except Exception:
            logger.exception("Error during trading cycle; continuing to the next cycle.")
        time_module.sleep(config.POLL_INTERVAL_SECONDS)

    logger.info("Trading window ended at %s. Stopping.", config.TRADING_END)
