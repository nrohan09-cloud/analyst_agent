"""
SQL execution wrapper with error handling and budget tracking.

Provides a centralized system for executing SQL queries with proper
error handling, budget consumption, and result formatting.
"""

import time
import json
from typing import Dict, Any, Optional
import structlog
from .llm_factory import create_llm
from analyst_agent.settings import settings

from .state import AnalystState, consume_budget, add_execution_step
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
    
    start_time = time.perf_counter()
    
    try:
        # Ensure row limit is applied
        sql_final = ensure_limit(sql, dialect, row_cap)
        
        # Execute query through connector
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
        # List available tables
        tables = connector.list_tables()
        
        schema_card = {
            "tables": {},
            "generated_at": time.time()
        }
        
        # Profile each table (limit to first 10 for performance)
        for table in tables[:10]:
            try:
                columns = connector.get_columns(table)
                profile = connector.profile_counts(table)
                
                # Get sample data for small tables
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
                    "sample_rows": sample_rows
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
            total_tables_available=len(tables)
        )
        
        return schema_card
        
    except Exception as e:
        logger.error("Failed to generate schema card", error=str(e))
        return {
            "tables": {},
            "error": str(e),
            "generated_at": time.time()
        } 