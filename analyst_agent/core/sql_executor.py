"""
SQL execution wrapper with error handling and budget tracking.

Provides a centralized system for executing SQL queries with proper
error handling, budget consumption, and result formatting.
"""

import time
import json
import hashlib
from typing import Dict, Any, Optional, List
import structlog
from jose import jwt
from .llm_factory import create_llm
from analyst_agent.settings import settings

from .state import AnalystState, consume_budget, add_execution_step
from .rls_manager import RLSTokenManager
from .dialect_caps import (
    build_sql_prompt,
    build_diagnostic_prompt,
    build_refinement_prompt
)

logger = structlog.get_logger(__name__)


def try_execute_sql(
    state: AnalystState, 
    sql: str, 
    row_cap: int = 100000,
    timeout_seconds: int = 30
) -> Dict[str, Any]:
    """
    Execute SQL query with error handling and budget tracking.
    
    Args:
        state: Current analysis state
        sql: SQL query to execute
        row_cap: Maximum number of rows to return
        timeout_seconds: Query timeout in seconds
        
    Returns:
        Dictionary with execution results
    """
    connector = state["ctx"]["connector"]
    dialect = state["ctx"]["dialect"]
    rls_context = state.get("rls_context")
    if rls_context is None:
        rls_context = state.get("ctx", {}).get("rls_context")
        if rls_context is not None:
            # Keep top-level state in sync for downstream nodes
            state["rls_context"] = rls_context
    
    start_time = time.perf_counter()
    
    try:
        # Ensure row limit is applied
        sql_final = ensure_limit(sql, dialect, row_cap)
        
        # Refresh RLS token if required before execution
        effective_rls_context = rls_context
        if effective_rls_context and effective_rls_context.get("access_token"):
            auto_refresh = effective_rls_context.get("auto_refresh")
            if auto_refresh is None:
                auto_refresh = effective_rls_context.get("autoRefresh")
            if auto_refresh:
                supabase_url = state["ctx"].get("supabase_url")
                anon_key = state["ctx"].get("supabase_anon_key")
                refresh_token = (
                    effective_rls_context.get("refresh_token")
                    or effective_rls_context.get("refreshToken")
                )
                if supabase_url and anon_key:
                    manager: Optional[RLSTokenManager] = state["ctx"].get("_rls_token_manager")
                    if manager is None:
                        manager = RLSTokenManager(supabase_url=supabase_url, anon_key=anon_key)
                        state["ctx"]["_rls_token_manager"] = manager
                    new_access, new_refresh = manager.refresh_token_if_needed(
                        effective_rls_context["access_token"],
                        refresh_token,
                    )
                    if new_access != effective_rls_context["access_token"]:
                        effective_rls_context["access_token"] = new_access
                    if new_refresh and new_refresh != refresh_token:
                        effective_rls_context["refresh_token"] = new_refresh
                else:
                    logger.warning(
                        "RLS auto-refresh requested but configuration missing",
                        has_supabase_url=bool(supabase_url),
                        has_anon_key=bool(anon_key),
                    )
            # Update ctx reference to reflect any token changes
            state["ctx"]["rls_context"] = effective_rls_context
            state["rls_context"] = effective_rls_context

        # Execute query through connector, preferring RLS-aware code paths when available
        if effective_rls_context and effective_rls_context.get("access_token"):
            access_token = effective_rls_context["access_token"]
            token_hash = hashlib.sha256(access_token.encode("utf-8")).hexdigest()
            safe_claims: Optional[Dict[str, Any]] = None
            try:
                decoded_claims = jwt.get_unverified_claims(access_token)
                safe_claims = {k: decoded_claims.get(k) for k in ("sub", "role", "aud", "iss", "exp")}
            except Exception as decode_error:  # pragma: no cover - defensive logging
                logger.warning(
                    "Failed to decode RLS access token",
                    job_id=state.get("job_id"),
                    error=str(decode_error),
                )
            logger.info(
                "Executing SQL with RLS context",
                job_id=state.get("job_id"),
                supabase_url=state["ctx"].get("supabase_url"),
                supabase_project_ref=state["ctx"].get("supabase_project_ref"),
                access_token_hash=token_hash,
                rls_claims=safe_claims,
            )

        rls_context_for_execution = state.get("rls_context")
        if rls_context_for_execution and hasattr(connector, "run_sql_with_rls"):
            table = connector.run_sql_with_rls(
                sql_final,
                limit=row_cap,
                rls_context=rls_context_for_execution,
            )
        else:
            if rls_context_for_execution:
                logger.debug(
                    "Connector lacks RLS execution hook; falling back to run_sql",
                    connector_type=type(connector).__name__
                )
            table = connector.run_sql(sql_final, limit=row_cap)
        
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Update budget
        consume_budget(state, queries=1, seconds=duration_ms / 1000)
        
        # Add execution step
        add_execution_step(
            state,
            step_name="sql_execution",
            status="completed",
            duration_ms=duration_ms,
            sql=sql_final,
            row_count=table.num_rows
        )
        
        logger.info(
            "SQL execution successful",
            rows=table.num_rows,
            columns=table.num_columns,
            duration_ms=duration_ms,
            dialect=dialect
        )
        
        return {
            "ok": True,
            "table": table,
            "row_count": table.num_rows,
            "column_count": table.num_columns,
            "duration_ms": duration_ms,
            "sql": sql_final
        }
        
    except Exception as e:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        error_msg = str(e)[:2000]  # Truncate very long errors
        
        # Still consume budget for failed queries
        consume_budget(state, queries=1, seconds=duration_ms / 1000)
        
        # Add execution step
        add_execution_step(
            state,
            step_name="sql_execution",
            status="failed",
            duration_ms=duration_ms,
            sql=sql,
            error=error_msg
        )
        
        # Track error in state
        if "errors" not in state:
            state["errors"] = []
        
        state["errors"].append({
            "sql": sql,
            "error": error_msg,
            "timestamp": time.time(),
            "duration_ms": duration_ms
        })
        
        logger.error(
            "SQL execution failed",
            error=error_msg,
            duration_ms=duration_ms,
            dialect=dialect,
            sql_preview=sql[:200] + "..." if len(sql) > 200 else sql
        )
        
        return {
            "ok": False,
            "error": error_msg,
            "duration_ms": duration_ms,
            "sql": sql
        }


def ensure_limit(sql: str, dialect: str, row_cap: int) -> str:
    """
    Ensure SQL query has appropriate LIMIT clause.
    
    Args:
        sql: SQL query
        dialect: SQL dialect
        row_cap: Maximum rows to return
        
    Returns:
        SQL with limit clause applied
    """
    sql_upper = sql.upper()
    
    # Skip if already has LIMIT or TOP
    if "LIMIT" in sql_upper or "TOP" in sql_upper:
        return sql
    
    # Apply dialect-specific limiting
    if dialect == "mssql":
        # SQL Server uses TOP after SELECT
        if sql.strip().upper().startswith("SELECT"):
            return sql.replace("SELECT", f"SELECT TOP {row_cap}", 1)
    else:
        # Most databases use LIMIT at the end
        return f"{sql.rstrip(';')} LIMIT {row_cap}"
    
    return sql


def llm_generate_sql(prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate SQL using LLM with structured output.
    
    Args:
        prompt: Formatted prompt for SQL generation
        model: LLM model to use
        
    Returns:
        Dictionary with sql and notes
    """
    try:
        chosen_model = model or settings.default_llm_model
        llm = create_llm(model=chosen_model, temperature=settings.llm_temperature)
        response = llm.invoke(prompt)
        
        # Parse JSON response
        content = response.content.strip()
        
        # Handle potential markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        result = json.loads(content)
        
        logger.debug(
            "Generated SQL",
            model=chosen_model,
            has_sql=bool(result.get("sql")),
            notes=result.get("notes", "")[:100]
        )
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM JSON response", error=str(e), content=content[:500])
        # Fallback: try to extract SQL from response
        lines = content.split('\n')
        sql_lines = []
        in_sql = False
        
        for line in lines:
            if 'SELECT' in line.upper() or in_sql:
                in_sql = True
                sql_lines.append(line)
                if line.strip().endswith(';'):
                    break
        
        return {
            "sql": "\n".join(sql_lines) if sql_lines else "SELECT 1",
            "notes": "Generated from unparseable response"
        }
        
    except Exception as e:
        logger.error("LLM SQL generation failed", error=str(e))
        return {
            "sql": "SELECT 1 -- Error generating SQL",
            "notes": f"Error: {str(e)}"
        }


def llm_generate_diagnostics(prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate diagnostic queries using LLM.
    
    Args:
        prompt: Formatted prompt for diagnostic generation
        model: LLM model to use
        
    Returns:
        Dictionary with diagnostic_sqls and purpose
    """
    try:
        chosen_model = model or settings.default_llm_model
        llm = create_llm(model=chosen_model, temperature=settings.llm_temperature)
        response = llm.invoke(prompt)
        
        content = response.content.strip()
        
        # Handle markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        result = json.loads(content)
        
        logger.debug(
            "Generated diagnostics",
            model=chosen_model,
            num_queries=len(result.get("diagnostic_sqls", [])),
            purpose=result.get("purpose", "")[:100]
        )
        
        return result
        
    except Exception as e:
        logger.error("LLM diagnostic generation failed", error=str(e))
        return {
            "diagnostic_sqls": [
                "SELECT COUNT(*) as row_count FROM information_schema.tables",
                "SELECT 1 as health_check"
            ],
            "purpose": f"Fallback diagnostics due to error: {str(e)}"
        }

def select_relevant_tables(
    state: AnalystState,
    tables: List[str],
    max_candidates: int = 12,
    prompt_table_limit: int = 200
) -> Dict[str, Any]:
    """Use the LLM to select tables most relevant to the current question."""
    if not tables:
        return {"tables": [], "notes": "No tables available", "method": "empty"}

    question = (
        state.get('spec', {}).get('question', '').strip()
        if isinstance(state, dict)
        else ''
    )

    if not question:
        return {
            "tables": tables[:max_candidates],
            "notes": "No question provided; using first tables",
            "method": "fallback",
        }

    shown_tables = tables[:prompt_table_limit]
    truncated = len(tables) > prompt_table_limit
    table_list = "\\n".join(f"- {name}" for name in shown_tables)

    prompt = f"""You are a senior data analyst preparing to write SQL for a business question.

QUESTION:
{question}

AVAILABLE TABLES (showing {len(shown_tables)} of {len(tables)} total):
{table_list}
"""
    if truncated:
        prompt += "\\nAdditional tables exist beyond this list; if you are unsure include a note in your response.\\n"

    prompt += f"""
Select up to {max_candidates} tables that are most relevant for answering the question.
Return a JSON object with exactly this structure:
{{
    "tables": ["table_a", "table_b"],
    "notes": "Short explanation of why these tables were chosen"
}}

Rules:
- Only return names that appear in the provided table list.
- Prefer the smallest set of tables needed to answer the question.
- If unsure, include your uncertainty in the notes.
"""

    try:
        llm = create_llm(
            model=settings.default_llm_model,
            temperature=settings.llm_temperature
        )
        response = llm.invoke(prompt)
        content = response.content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]

        result = json.loads(content)
        raw_tables = result.get('tables', []) or []
        selected = []
        for name in raw_tables:
            if name in tables and name not in selected:
                selected.append(name)
            if len(selected) >= max_candidates:
                break

        notes = result.get('notes') or result.get('reason') or result.get('explanation')
        if selected:
            logger.debug(
                "Selected relevant tables",
                selected_count=len(selected),
                total_available=len(tables)
            )
            return {"tables": selected, "notes": notes or "LLM-selected tables", "method": "llm"}
    except Exception as exc:  # Broad catch to ensure profiling keeps going
        logger.warning("Table selection via LLM failed", error=str(exc))

    fallback_tables = tables[:max_candidates]
    logger.debug(
        "Falling back to default table selection",
        selected_count=len(fallback_tables),
        total_available=len(tables)
    )
    return {
        "tables": fallback_tables,
        "notes": "Fallback to first tables",
        "method": "fallback",
    }



def generate_schema_card(state: AnalystState) -> Dict[str, Any]:
    """
    Generate a schema card by profiling the database.

    Args:
        state: Current analysis state

    Returns:
        Schema card with table and column information
    """
    connector = state["ctx"]["connector"]

    try:
        # List available tables and store for downstream nodes
        tables = connector.list_tables()
        state.setdefault("ctx", {})["available_tables"] = tables

        selection = select_relevant_tables(state, tables)
        selected_tables = selection.get("tables", [])
        if not selected_tables and tables:
            selected_tables = tables[:10]

        state["ctx"]["selected_tables"] = selected_tables

        schema_card = {
            "tables": {},
            "generated_at": time.time(),
            "table_selection": {
                "available_tables": len(tables),
                "selected_tables": selected_tables,
                "method": selection.get("method", "unknown"),
                "notes": selection.get("notes", ""),
            },
        }

        for table in selected_tables:
            try:
                columns = connector.get_columns(table)
                profile = connector.profile_counts(table)

                sample_rows = []
                if profile.get("total_rows", 0) < 1000:
                    try:
                        sample_table = connector.read_table(table, limit=5)
                        if sample_table.num_rows > 0:
                            sample_df = sample_table.to_pandas()
                            sample_rows = [
                                dict(row) for _, row in sample_df.head(3).iterrows()
                            ]
                    except Exception:
                        pass  # Sample data is optional

                schema_card["tables"][table] = {
                    "columns": columns,
                    "row_count": profile.get("total_rows", 0),
                    "sample_rows": sample_rows,
                }

                logger.debug(
                    "Profiled table",
                    table=table,
                    columns=len(columns),
                    rows=profile.get("total_rows", 0)
                )

            except Exception as e:
                logger.warning("Failed to profile table", table=table, error=str(e))
                continue

        logger.info(
            "Generated schema card",
            tables=len(schema_card["tables"]),
            total_tables_available=len(tables),
            selection_method=schema_card["table_selection"]["method"],
        )

        return schema_card

    except Exception as e:
        logger.error("Failed to generate schema card", error=str(e))
        return {
            "tables": {},
            "error": str(e),
            "generated_at": time.time()
        }
