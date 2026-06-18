"""Account balance / holdings lookups."""

from __future__ import annotations

from dataclasses import dataclass

import config
from api_client import APIClient
from logger import get_logger

logger = get_logger(__name__)

BALANCE_PATH = "/uapi/domestic-stock/v1/trading/inquire-balance"


@dataclass
class AccountSnapshot:
    cash_balance_krw: int
    holding_quantity: int  # shares of the target stock currently held
    orderable_quantity: int  # shares actually sellable (excludes ones reserved by pending sell orders)
    avg_purchase_price_krw: int  # average cost per share of the current position (0 if no position)
    profit_loss_krw: int  # unrealized profit/loss in KRW for the current position
    profit_loss_rate_pct: float  # unrealized profit/loss in % for the current position

    def __str__(self) -> str:
        return (
            f"cash={self.cash_balance_krw} KRW, holding_qty={self.holding_quantity}, "
            f"orderable_qty={self.orderable_quantity}, avg_cost={self.avg_purchase_price_krw} KRW, "
            f"unrealized_pnl={self.profit_loss_krw} KRW ({self.profit_loss_rate_pct:+.2f}%)"
        )


def get_account_snapshot(client: APIClient, stock_code: str = config.STOCK_CODE) -> AccountSnapshot:
    """Fetch current cash balance and holding quantity for the target stock."""
    params = {
        "CANO": client.cano,
        "ACNT_PRDT_CD": client.acnt_prdt_cd,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": config.BALANCE_INQUIRY_DIVISION,
        "UNPR_DVSN": config.BALANCE_UNIT_PRICE_DIVISION,
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    data = client.get(BALANCE_PATH, config.TR_ID_BALANCE_MOCK, params)

    holdings = data.get("output1") or []
    holding_qty = 0
    orderable_qty = 0
    avg_purchase_price = 0
    profit_loss = 0
    profit_loss_rate = 0.0
    for item in holdings:
        if item.get(config.FIELD_HOLDING_PRODUCT_CODE) == stock_code:
            holding_qty = int(item.get(config.FIELD_HOLDING_QUANTITY, 0))
            orderable_qty = int(item.get(config.FIELD_ORDERABLE_QUANTITY, 0))
            avg_purchase_price = int(float(item.get(config.FIELD_AVG_PURCHASE_PRICE, 0)))
            profit_loss = int(float(item.get(config.FIELD_PROFIT_LOSS_AMOUNT, 0)))
            profit_loss_rate = float(item.get(config.FIELD_PROFIT_LOSS_RATE, 0))
            break

    summary = data.get("output2") or []
    if isinstance(summary, dict):  # defensive: KIS sometimes returns a single object here
        summary = [summary]
    cash_balance = int(summary[0][config.FIELD_CASH_BALANCE]) if summary else 0

    snapshot = AccountSnapshot(
        cash_balance_krw=cash_balance,
        holding_quantity=holding_qty,
        orderable_quantity=orderable_qty,
        avg_purchase_price_krw=avg_purchase_price,
        profit_loss_krw=profit_loss,
        profit_loss_rate_pct=profit_loss_rate,
    )
    logger.info("Account snapshot: %s", snapshot)
    return snapshot
