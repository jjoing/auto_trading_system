"""Configuration and environment loading for the Samsung Electronics auto trader.

All values that depend on Korea Investment & Securities (KIS) API conventions
(tr_id codes, division codes, response field names) are isolated here as
named constants so they are easy to find and edit if KIS changes them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when required configuration/environment variables are missing or invalid."""


PROJECT_DIR = Path(__file__).resolve().parent

# Load GH_ACCOUNT / GH_APPKEY / GH_APPSECRET from a local .env file if present.
# .env is gitignored — see .env.example for the expected format. Real OS
# environment variables (if already set) always take priority over .env.
load_dotenv(PROJECT_DIR / ".env")

# ---------------------------------------------------------------------------
# KIS server — MOCK (virtual) TRADING ONLY. Do not point this at the real
# trading domain; this project assumes mock trading throughout.
# ---------------------------------------------------------------------------
BASE_URL = "https://openapivts.koreainvestment.com:29443"

# ---------------------------------------------------------------------------
# Trading target
# ---------------------------------------------------------------------------
STOCK_CODE = "005930"  # Samsung Electronics
MARKET_DIV_CODE = "J"  # FID_COND_MRKT_DIV_CODE: J = KRX

# ---------------------------------------------------------------------------
# Order sizing / pricing — easy to tune without touching trading logic
# ---------------------------------------------------------------------------
ORDER_PRICE_OFFSET_KRW = 1000  # buy = current_price - offset, sell = current_price + offset
ORDER_QUANTITY = 1  # shares per order — placeholder, adjust as needed

# ---------------------------------------------------------------------------
# Trading window (local time)
# ---------------------------------------------------------------------------
TRADING_START = time(9, 10)
TRADING_END = time(15, 30)

# ---------------------------------------------------------------------------
# Polling / networking — conservative on purpose (mock env has strict limits)
# ---------------------------------------------------------------------------
POLL_INTERVAL_SECONDS = 60  # time between full check -> order -> verify cycles
POST_ORDER_SETTLE_SECONDS = 3  # wait before re-checking holdings after an order
REQUEST_TIMEOUT_SECONDS = 15
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2
MIN_SECONDS_BETWEEN_CALLS = 0.5  # minimum spacing between any two API calls

# ---------------------------------------------------------------------------
# Token cache (reused for the rest of the same day; see auth.py)
# ---------------------------------------------------------------------------
TOKEN_CACHE_PATH = PROJECT_DIR / "token_cache.json"
TOKEN_REFRESH_SAFETY_MARGIN_SECONDS = 300  # refresh slightly before actual expiry

# ---------------------------------------------------------------------------
# KIS API tr_id / division codes — MOCK TRADING.
# Verified against the official koreainvestment/open-trading-api examples
# (examples_user/domestic_stock/domestic_stock_functions.py) on 2026-06-18.
# If KIS changes these, this is the only place that needs editing.
# ---------------------------------------------------------------------------
TR_ID_CURRENT_PRICE = "FHKST01010100"  # same id for real and mock
TR_ID_BALANCE_MOCK = "VTTC8434R"  # 주식잔고조회 (모의투자)
TR_ID_ORDER_BUY_MOCK = "VTTC0012U"  # 주식 현금 매수 주문 (모의투자)
TR_ID_ORDER_SELL_MOCK = "VTTC0011U"  # 주식 현금 매도 주문 (모의투자)

ORDER_DIVISION_LIMIT = "00"  # ORD_DVSN: 00 = 지정가 (limit order)
EXCHANGE_ID_DIVISION_CODE = "KRX"  # EXCG_ID_DVSN_CD
SELL_TYPE_NORMAL = "01"  # SLL_TYPE: 01 = 일반매도 (used only for sell orders)
BALANCE_INQUIRY_DIVISION = "02"  # INQR_DVSN: 02 = 종목별
BALANCE_UNIT_PRICE_DIVISION = "01"  # UNPR_DVSN

# ---------------------------------------------------------------------------
# KIS response field names. stck_prpr and ODNO are directly confirmed in the
# official repo's examples. hldg_qty / pdno / dnca_tot_amt are standard KIS
# field names from the public 주식잔고조회 spec but were NOT directly
# grep-confirmed in the local repo — if balance parsing looks wrong, check
# these against the latest KIS API docs and edit only here.
# ---------------------------------------------------------------------------
FIELD_CURRENT_PRICE = "stck_prpr"  # confirmed
FIELD_ORDER_NO = "ODNO"  # confirmed
FIELD_HOLDING_PRODUCT_CODE = "pdno"  # placeholder — verify if needed
FIELD_HOLDING_QUANTITY = "hldg_qty"  # placeholder — verify if needed
FIELD_ORDERABLE_QUANTITY = "ord_psbl_qty"  # 주문가능수량 — sellable qty, excludes shares already reserved by pending sell orders
FIELD_CASH_BALANCE = "dnca_tot_amt"  # placeholder — verify if needed
FIELD_AVG_PURCHASE_PRICE = "pchs_avg_pric"  # 매입평균가격 — average cost per share, placeholder — verify if needed
FIELD_PROFIT_LOSS_AMOUNT = "evlu_pfls_amt"  # 평가손익금액 — unrealized P&L in KRW, placeholder — verify if needed
FIELD_PROFIT_LOSS_RATE = "evlu_pfls_rt"  # 평가손익율 — unrealized P&L in %, placeholder — verify if needed


@dataclass(frozen=True)
class Credentials:
    app_key: str
    app_secret: str
    cano: str  # 종합계좌번호 앞 8자리
    acnt_prdt_cd: str  # 계좌상품코드 뒤 2자리


def _parse_account(raw: str) -> tuple[str, str]:
    """Split GH_ACCOUNT into (CANO, ACNT_PRDT_CD).

    Accepts "12345678-01", "1234567801" (10 digits), or a bare 8-digit
    account number (product code then defaults to "01").
    """
    value = raw.strip()
    if "-" in value:
        cano, prdt = value.split("-", 1)
    elif len(value) == 10:
        cano, prdt = value[:8], value[8:]
    elif len(value) == 8:
        cano, prdt = value, "01"
    else:
        raise ConfigError(
            f"GH_ACCOUNT must be 8 digits, 10 digits, or '12345678-01' format, got: {raw!r}"
        )
    if not (cano.isdigit() and prdt.isdigit() and len(cano) == 8 and len(prdt) == 2):
        raise ConfigError(f"Could not parse GH_ACCOUNT into CANO/ACNT_PRDT_CD: {raw!r}")
    return cano, prdt


def load_credentials() -> Credentials:
    """Load and validate required credentials from environment variables."""
    account = os.environ.get("GH_ACCOUNT")
    app_key = os.environ.get("GH_APPKEY")
    app_secret = os.environ.get("GH_APPSECRET")

    missing = [
        name
        for name, value in (
            ("GH_ACCOUNT", account),
            ("GH_APPKEY", app_key),
            ("GH_APPSECRET", app_secret),
        )
        if not value
    ]
    if missing:
        raise ConfigError("Missing required environment variable(s): " + ", ".join(missing))

    cano, acnt_prdt_cd = _parse_account(account)
    return Credentials(app_key=app_key, app_secret=app_secret, cano=cano, acnt_prdt_cd=acnt_prdt_cd)
