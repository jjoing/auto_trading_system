"""Thin HTTP client wrapping the KIS REST API conventions.

Keeps transport concerns (headers, retries, timeouts, basic error handling,
call throttling) in one place so the higher-level modules (market_data,
account, orders) only deal with KIS-specific parameters and response fields.
"""

from __future__ import annotations

import time as time_module
from typing import Any, Optional

import requests

import config
from auth import TokenManager
from logger import get_logger

logger = get_logger(__name__)


class APIError(RuntimeError):
    """Raised when a KIS API call fails after retries, or returns rt_cd != '0'."""


class APIClient:
    """Sends GET/POST requests to the KIS mock trading server."""

    def __init__(self, credentials: config.Credentials, token_manager: TokenManager):
        self._app_key = credentials.app_key
        self._app_secret = credentials.app_secret
        self.cano = credentials.cano
        self.acnt_prdt_cd = credentials.acnt_prdt_cd
        self._token_manager = token_manager
        self._last_call_time = 0.0

    def _headers(self, tr_id: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._token_manager.get_token()}",
            "appkey": self._app_key,
            "appsecret": self._app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    def _throttle(self) -> None:
        """Enforce a minimum spacing between any two outgoing API calls."""
        elapsed = time_module.monotonic() - self._last_call_time
        wait = config.MIN_SECONDS_BETWEEN_CALLS - elapsed
        if wait > 0:
            time_module.sleep(wait)
        self._last_call_time = time_module.monotonic()

    def _send(
        self,
        method: str,
        path: str,
        tr_id: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        url = config.BASE_URL + path
        last_error: Optional[Exception] = None
        allow_auth_retry = True

        for attempt in range(1, config.MAX_RETRIES + 2):
            self._throttle()
            try:
                response = requests.request(
                    method,
                    url,
                    headers=self._headers(tr_id),
                    params=params,
                    json=json_body,
                    timeout=config.REQUEST_TIMEOUT_SECONDS,
                )
            except requests.RequestException as exc:
                last_error = exc
                logger.warning("Request error on %s %s (attempt %d): %s", method, path, attempt, exc)
                if attempt <= config.MAX_RETRIES:
                    time_module.sleep(config.RETRY_BACKOFF_SECONDS)
                continue

            if response.status_code == 401 and allow_auth_retry:
                logger.warning("Got HTTP 401 from %s; refreshing token and retrying once.", path)
                self._token_manager.invalidate()
                allow_auth_retry = False  # only retry once for an auth failure
                continue

            if response.status_code != 200:
                last_error = APIError(f"HTTP {response.status_code} on {path}: {response.text[:300]}")
                logger.warning(str(last_error))
                if attempt <= config.MAX_RETRIES:
                    time_module.sleep(config.RETRY_BACKOFF_SECONDS)
                continue

            data = response.json()
            rt_cd = data.get("rt_cd")
            if rt_cd != "0":
                msg = data.get("msg1", "unknown error")
                raise APIError(f"KIS API error on {path} (tr_id={tr_id}): rt_cd={rt_cd} msg={msg}")

            return data

        raise APIError(f"Failed to call {path} after retries: {last_error}")

    def get(self, path: str, tr_id: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._send("GET", path, tr_id, params=params)

    def post(self, path: str, tr_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._send("POST", path, tr_id, json_body=body)
