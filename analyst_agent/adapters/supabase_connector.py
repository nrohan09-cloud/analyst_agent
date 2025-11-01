"""
Supabase-specific connector with Row-Level Security (RLS) support.

Wraps the standard SQLAlchemy connector so we can inject Supabase JWT claims
on every database connection, ensuring policies execute for the intended user.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import pyarrow as pa
import structlog
from jose import jwt
from sqlalchemy import event

from .sqlalchemy_connector import SQLAlchemyConnector
from .registry import register

logger = structlog.get_logger(__name__)


@register("supabase")
class SupabaseConnector(SQLAlchemyConnector):
    """Supabase Postgres connector that propagates RLS tokens."""

    def __init__(
        self,
        url: str,
        anon_key: str,
        schema: Optional[str] = "public",
        business_tz: str = "Asia/Kolkata",
        **engine_kwargs: Any,
    ):
        self._current_rls_token: Optional[str] = None
        self.anon_key = anon_key

        super().__init__(
            url=url,
            schema=schema,
            business_tz=business_tz,
            dialect="postgres",
            **engine_kwargs,
        )

        # Register listener to inject JWT claims on each connection
        def _set_rls_claims(dbapi_connection, connection_record) -> None:  # pragma: no cover - exercised in integration
            token = self._current_rls_token
            cursor = dbapi_connection.cursor()
            try:
                if not token:
                    cursor.execute("reset role;")
                    cursor.execute(
                        "select set_config('request.jwt.claims', null, true);"
                    )
                    cursor.execute(
                        "select set_config('request.jwt.claim.sub', null, true);"
                    )
                    cursor.execute(
                        "select set_config('request.jwt.claim.role', null, true);"
                    )
                    return

                try:
                    claims = jwt.get_unverified_claims(token)
                except Exception as decode_error:  # pragma: no cover - defensive logging
                    logger.warning(
                        "Failed to decode Supabase RLS token",
                        error=str(decode_error),
                    )
                    cursor.execute("reset role;")
                    cursor.execute(
                        "select set_config('request.jwt.claims', null, true);"
                    )
                    cursor.execute(
                        "select set_config('request.jwt.claim.sub', null, true);"
                    )
                    cursor.execute(
                        "select set_config('request.jwt.claim.role', null, true);"
                    )
                    return

                cursor.execute("set role authenticated;")
                cursor.execute(
                    "select set_config('request.jwt.claims', %s, true);",
                    (json.dumps(claims),),
                )

                sub = claims.get("sub")
                if sub:
                    cursor.execute(
                        "select set_config('request.jwt.claim.sub', %s, true);",
                        (sub,),
                    )
                else:
                    cursor.execute(
                        "select set_config('request.jwt.claim.sub', null, true);"
                    )
                role_claim = claims.get("role")
                if role_claim:
                    cursor.execute(
                        "select set_config('request.jwt.claim.role', %s, true);",
                        (role_claim,),
                    )
                else:
                    cursor.execute(
                        "select set_config('request.jwt.claim.role', null, true);"
                    )
            finally:
                cursor.close()

        def _set_rls_claims_on_checkout(dbapi_connection, connection_record, connection_proxy) -> None:  # pragma: no cover - exercised in integration
            _set_rls_claims(dbapi_connection, connection_record)

        event.listen(self.engine, "connect", _set_rls_claims)
        event.listen(self.engine, "checkout", _set_rls_claims_on_checkout)

    def set_rls_token(self, access_token: str) -> None:
        """Store the current RLS token for upcoming queries."""
        self._current_rls_token = access_token
        logger.debug("Supabase RLS token set")

    def run_sql_with_rls(
        self,
        sql: str,
        *,
        limit: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
        rls_context: Optional[Dict[str, Any]] = None,
    ) -> pa.Table:
        """Execute SQL while ensuring the latest RLS token is applied."""
        if rls_context and rls_context.get("access_token"):
            self.set_rls_token(rls_context["access_token"])

        return super().run_sql(sql, params=params, limit=limit)
