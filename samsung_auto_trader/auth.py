"""Access-token issuance and same-day caching for the KIS Open API.

KIS issues tokens valid for roughly 24 hours and explicitly discourages
re-issuing a new token shortly after the previous one. We cache the token
to disk and reuse it for the rest of the day; a new token is only requested
when there is no valid cached token left.
"""

from __future__ import annotations

import json
import time as time_module
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

import config
from logger import get_logger

logger = get_logger(__name__)

TOKEN_URL_PATH = "/oauth2/tokenP"
# KIS returns the expiry timestamp as "%Y-%m-%d %H:%M:%S" in this field.
EXPIRY_FIELD = "access_token_token_expired"
TOKEN_FIELD = "access_token"


@dataclass
class CachedToken:
    access_token: str
    expires_at: datetime


def _read_cache(path: Path) -> Optional[CachedToken]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return CachedToken(
            access_token=data["access_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        logger.warning("Token cache file is unreadable/corrupt; ignoring it.")
        return None


def _write_cache(path: Path, token: CachedToken) -> None:
    path.write_text(
        json.dumps({"access_token": token.access_token, "expires_at": token.expires_at.isoformat()}),
        encoding="utf-8",
    )


def _request_new_token(app_key: str, app_secret: str) -> CachedToken:
    url = config.BASE_URL + TOKEN_URL_PATH
    body = {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}
    headers = {"Content-Type": "application/json"}

    last_error: Exception | None = None
    for attempt in range(1, config.MAX_RETRIES + 2):
        try:
            response = requests.post(url, json=body, headers=headers, timeout=config.REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()
            expires_at = datetime.strptime(data[EXPIRY_FIELD], "%Y-%m-%d %H:%M:%S")
            logger.info("Issued new KIS access token (mock trading), valid until %s.", expires_at)
            return CachedToken(access_token=data[TOKEN_FIELD], expires_at=expires_at)
        except (requests.RequestException, KeyError, ValueError) as exc:
            last_error = exc
            logger.warning("Token request failed (attempt %d/%d): %s", attempt, config.MAX_RETRIES + 1, exc)
            if attempt <= config.MAX_RETRIES:
                time_module.sleep(config.RETRY_BACKOFF_SECONDS)

    raise RuntimeError(f"Could not obtain KIS access token: {last_error}")


class TokenManager:
    """Supplies a valid access token, reusing the cached one whenever possible."""

    def __init__(self, app_key: str, app_secret: str, cache_path: Path = config.TOKEN_CACHE_PATH):
        self._app_key = app_key
        self._app_secret = app_secret
        self._cache_path = cache_path
        self._token: Optional[CachedToken] = None

    def get_token(self) -> str:
        if self._token is None:
            self._token = _read_cache(self._cache_path)
            if self._token is not None:
                logger.info("Reusing cached access token from disk, valid until %s.", self._token.expires_at)

        margin = timedelta(seconds=config.TOKEN_REFRESH_SAFETY_MARGIN_SECONDS)
        if self._token is None or datetime.now() >= self._token.expires_at - margin:
            if self._token is not None:
                logger.info("Cached token expired or near expiry; requesting a new one.")
            self._token = _request_new_token(self._app_key, self._app_secret)
            _write_cache(self._cache_path, self._token)

        return self._token.access_token

    def invalidate(self) -> None:
        """Force the next get_token() call to fetch a fresh token."""
        logger.warning("Invalidating current token due to an API auth error.")
        self._token = None
        if self._cache_path.exists():
            self._cache_path.unlink()
