"""Entry point: load config/credentials, authenticate, run the trading loop."""

from __future__ import annotations

import sys

import config
from api_client import APIClient
from auth import TokenManager
from logger import get_logger, setup_logging
from trader import run_trading_loop

logger = get_logger(__name__)


def main() -> int:
    setup_logging()

    try:
        credentials = config.load_credentials()
    except config.ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        return 1

    token_manager = TokenManager(credentials.app_key, credentials.app_secret)
    client = APIClient(credentials, token_manager)

    try:
        run_trading_loop(client)
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Shutting down.")
    except Exception:
        logger.exception("Unhandled error in trading loop.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
