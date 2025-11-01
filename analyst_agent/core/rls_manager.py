"""
Utilities for managing Row-Level Security (RLS) authentication lifecycle.

Currently tailored for Supabase JWT handling, providing proactive refresh
of access tokens to ensure long-running analysis jobs complete successfully.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

import httpx
import structlog
from jose import jwt

logger = structlog.get_logger(__name__)


class RLSTokenManager:
    """Handle Supabase RLS token validation and refresh."""

    def __init__(
        self,
        supabase_url: str,
        anon_key: str,
        refresh_threshold_seconds: int = 300,
    ) -> None:
        """
        Args:
            supabase_url: Base Supabase project URL (e.g. https://xyz.supabase.co)
            anon_key: Supabase anon key used for auth API calls
            refresh_threshold_seconds: Seconds before expiry to trigger refresh
        """
        self.supabase_url = supabase_url.rstrip("/")
        self.anon_key = anon_key
        self.refresh_threshold_seconds = refresh_threshold_seconds

    def is_token_expired(self, access_token: str) -> bool:
        """Return True if the token is expired or close to expiring."""
        try:
            claims = jwt.get_unverified_claims(access_token)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to parse RLS access token", error=str(exc))
            return True

        exp = claims.get("exp")
        if exp is None:
            logger.warning("Supabase access token missing exp claim")
            return True

        remaining = exp - time.time()
        return remaining < self.refresh_threshold_seconds

    def refresh_token_if_needed(
        self,
        access_token: str,
        refresh_token: Optional[str],
    ) -> Tuple[str, Optional[str]]:
        """
        Refresh the Supabase token pair if the access token is near expiry.

        Returns the (possibly new) access token and refresh token.
        """
        if not access_token:
            raise ValueError("Access token required for refresh check")

        if not self.is_token_expired(access_token):
            return access_token, refresh_token

        if not refresh_token:
            raise ValueError("Access token expired and no refresh token provided")

        endpoint = f"{self.supabase_url}/auth/v1/token?grant_type=refresh_token"
        payload = {"refresh_token": refresh_token}
        headers = {
            "apikey": self.anon_key,
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(endpoint, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise ValueError(f"Token refresh request failed: {exc}") from exc

        if response.status_code != 200:
            logger.error(
                "Supabase token refresh failed",
                status_code=response.status_code,
                detail=response.text[:200],
            )
            raise ValueError(f"Token refresh failed: {response.text}")

        data = response.json()
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token", refresh_token)

        if not new_access:
            raise ValueError("Token refresh response missing access_token")

        logger.info("Supabase access token refreshed")
        return new_access, new_refresh
