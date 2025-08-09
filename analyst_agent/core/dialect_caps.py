"""
Dialect capabilities and prompt building for direct SQL generation.

Provides dialect-specific hints and capabilities to help the LLM generate
correct SQL for different database systems without cross-dialect compilation.
"""

from typing import Dict, Any, List, Optional


# Dialect capabilities for prompt engineering
DIALECT_CAPABILITIES = {
    "postgres": {
        "limit": "LIMIT n",
        "date_trunc": "DATE_TRUNC('month', ts_column)",
        "timezone": "ts_column AT TIME ZONE 'Asia/Kolkata'",
        "string_agg": "STRING_AGG(column, ',')",
        "ilike": True,
        "boolean": True,
        "json_support": True,
        "window_functions": True,
        "cte": True,
        "identifier_quote": '"',
        "examples": [
            "SELECT DATE_TRUNC('month', created_at) as month, COUNT(*) FROM orders GROUP BY 1",
            "SELECT * FROM users WHERE email ILIKE '%@example.com'",
            "WITH monthly_sales AS (...) SELECT * FROM monthly_sales"
        ]
    },
    
    "mysql": {
        "limit": "LIMIT n",
        "date_trunc": "DATE_FORMAT(ts_column, '%Y-%m-01')",
        "timezone": "CONVERT_TZ(ts_column, '+00:00', '+05:30')",
        "string_agg": "GROUP_CONCAT(column)",
        "ilike": False,  # Use LOWER(col) LIKE LOWER(val)
        "boolean": True,
        "json_support": True,
        "window_functions": True,
        "cte": True,
        "identifier_quote": "`",
        "examples": [
            "SELECT DATE_FORMAT(created_at, '%Y-%m-01') as month, COUNT(*) FROM orders GROUP BY 1",
            "SELECT * FROM users WHERE LOWER(email) LIKE LOWER('%@example.com%')",
            "SELECT GROUP_CONCAT(name) FROM users"
        ]
    },
    
    "sqlite": {
        "limit": "LIMIT n", 
        "date_trunc": "strftime('%Y-%m-01', ts_column)",
        "timezone": None,  # Limited timezone support
        "string_agg": "GROUP_CONCAT(column)",
        "ilike": False,
        "boolean": True,
        "json_support": True,
        "window_functions": True,
        "cte": True,
        "identifier_quote": '"',
        "examples": [
            "SELECT strftime('%Y-%m-01', created_at) as month, COUNT(*) FROM orders GROUP BY 1",
            "SELECT * FROM users WHERE LOWER(email) LIKE LOWER('%@example.com%')",
            "SELECT GROUP_CONCAT(name) FROM users"
        ]
    },
    
    "snowflake": {
        "limit": "LIMIT n",
        "date_trunc": "DATE_TRUNC('month', ts_column)",
        "timezone": "CONVERT_TIMEZONE('Asia/Kolkata', ts_column)",
        "string_agg": "LISTAGG(column, ',')",
        "ilike": True,
        "boolean": True,
        "json_support": True,
        "window_functions": True,
        "cte": True,
        "qualify": True,
        "identifier_quote": '"',
        "examples": [
            "SELECT DATE_TRUNC('month', created_at) as month, COUNT(*) FROM orders GROUP BY 1",
            "SELECT * FROM users WHERE email ILIKE '%@example.com'",
            "SELECT * FROM (SELECT *, ROW_NUMBER() OVER (ORDER BY sales DESC) as rn FROM products) QUALIFY rn <= 10"
        ]
    },
    
    "bigquery": {
        "limit": "LIMIT n",
        "date_trunc": "TIMESTAMP_TRUNC(ts_column, MONTH)",
        "timezone": "TIMESTAMP(ts_column, 'Asia/Kolkata')",
        "string_agg": "STRING_AGG(column, ',')",
        "ilike": False,  # Use LOWER(col) LIKE LOWER(val)
        "boolean": True,
        "json_support": True,
        "window_functions": True,
        "cte": True,
        "backticks": True,
        "identifier_quote": "`",
        "examples": [
            "SELECT TIMESTAMP_TRUNC(created_at, MONTH) as month, COUNT(*) FROM `project.dataset.orders` GROUP BY 1",
            "SELECT * FROM `project.dataset.users` WHERE LOWER(email) LIKE LOWER('%@example.com%')",
            "SELECT STRING_AGG(name, ',') FROM `project.dataset.users`"
        ]
    },
    
    "mssql": {
        "limit": "TOP n",  # Goes after SELECT
        "date_trunc": "DATETRUNC(month, ts_column)",
        "timezone": None,  # Limited timezone support
        "string_agg": "STRING_AGG(column, ',')",
        "ilike": False,
        "boolean": True,
        "json_support": True,
        "window_functions": True,
        "cte": True,
        "identifier_quote": "[",
        "examples": [
            "SELECT TOP 100 DATETRUNC(month, created_at) as month, COUNT(*) FROM [orders] GROUP BY DATETRUNC(month, created_at)",
            "SELECT * FROM [users] WHERE LOWER(email) LIKE LOWER('%@example.com%')",
            "SELECT STRING_AGG(name, ',') FROM [users]"
        ]
    },
    
    "duckdb": {
        "limit": "LIMIT n",
        "date_trunc": "DATE_TRUNC('month', ts_column)",
        "timezone": "ts_column AT TIME ZONE 'Asia/Kolkata'",
        "string_agg": "STRING_AGG(column, ',')",
        "ilike": True,
        "boolean": True,
        "json_support": True,
        "window_functions": True,
        "cte": True,
        "identifier_quote": '"',
        "examples": [
            "SELECT DATE_TRUNC('month', created_at) as month, COUNT(*) FROM orders GROUP BY 1",
            "SELECT * FROM users WHERE email ILIKE '%@example.com'",
            "SELECT STRING_AGG(name, ',') FROM users"
        ]
    }
}


def get_dialect_capabilities(dialect: str) -> Dict[str, Any]:
    """
    Get capabilities for a specific SQL dialect.
    
    Args:
        dialect: SQL dialect name
        
    Returns:
        Dictionary of capabilities and examples
    """
    return DIALECT_CAPABILITIES.get(dialect, DIALECT_CAPABILITIES["postgres"])


def build_sql_prompt(
    dialect: str,
    question: str,
    schema_card: Dict[str, Any],
    constraints: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build a prompt for SQL generation in a specific dialect.
    
    Args:
        dialect: Target SQL dialect
        question: Natural language question
        schema_card: Database schema information
        constraints: Additional constraints and hints
        
    Returns:
        Formatted prompt for LLM
    """
    caps = get_dialect_capabilities(dialect)
    constraints = constraints or {}
    
    # Build schema information
    schema_info = _format_schema_info(schema_card)
    
    # Build capability hints
    capability_hints = _format_capability_hints(caps)
    
    # Build examples
    examples = _format_examples(caps.get("examples", []))
    
    prompt = f"""You are a data analyst who writes only {dialect.upper()} SQL. Do not use functions from other dialects.

QUESTION: {question}

DATABASE SCHEMA:
{schema_info}

{dialect.upper()} CAPABILITIES:
{capability_hints}

EXAMPLES OF VALID {dialect.upper()} SYNTAX:
{examples}

REQUIREMENTS:
- Write only valid {dialect.upper()} SQL
- Use appropriate functions for date/time operations
- Handle timezone conversion if needed (business timezone: Asia/Kolkata)
- Include appropriate LIMIT clause for large datasets
- Return results that directly answer the question

OUTPUT FORMAT:
Return a JSON object with exactly this structure:
{{
    "sql": "<your SQL query here>",
    "notes": "<brief explanation of approach>"
}}

Do not include any prose before or after the JSON."""
    
    return prompt


def build_diagnostic_prompt(
    dialect: str,
    question: str,
    last_sql: str,
    db_error: str,
    schema_card: Dict[str, Any]
) -> str:
    """
    Build a prompt for generating diagnostic queries.
    
    Args:
        dialect: Target SQL dialect
        question: Original question
        last_sql: SQL query that failed
        db_error: Database error message
        schema_card: Database schema information
        
    Returns:
        Formatted diagnostic prompt
    """
    caps = get_dialect_capabilities(dialect)
    schema_info = _format_schema_info(schema_card)
    
    prompt = f"""You are a data analyst debugging a {dialect.upper()} SQL query that failed.

ORIGINAL QUESTION: {question}

FAILED SQL:
{last_sql}

DATABASE ERROR:
{db_error}

DATABASE SCHEMA:
{schema_info}

Generate 3-5 diagnostic {dialect.upper()} queries to understand why the query failed:
- Check table existence and row counts
- Verify column names and data types
- Check for data availability in date ranges
- Examine distinct values in key columns
- Validate join conditions if applicable

OUTPUT FORMAT:
Return a JSON object:
{{
    "diagnostic_sqls": [
        "SELECT COUNT(*) FROM table1",
        "SELECT DISTINCT status FROM orders",
        "SELECT MIN(created_at), MAX(created_at) FROM orders"
    ],
    "purpose": "Brief explanation of what these queries will reveal"
}}

Write only valid {dialect.upper()} SQL in the diagnostic queries."""
    
    return prompt


def build_refinement_prompt(
    dialect: str,
    question: str,
    failed_sql: str,
    db_error: str,
    diagnostics: List[Dict[str, Any]]
) -> str:
    """
    Build a prompt for refining/fixing a failed SQL query.
    
    Args:
        dialect: Target SQL dialect
        question: Original question
        failed_sql: SQL query that failed
        db_error: Database error message
        diagnostics: Results from diagnostic queries
        
    Returns:
        Formatted refinement prompt
    """
    caps = get_dialect_capabilities(dialect)
    
    # Format diagnostic results
    diag_info = ""
    for i, diag in enumerate(diagnostics[:5]):
        if diag.get("ok"):
            diag_info += f"Diagnostic {i+1}: {diag.get('row_count', 0)} rows found\n"
            # Add sample data if available
            if diag.get("table") and len(diag["table"]) > 0:
                sample = diag["table"].to_pandas().head(3).to_string()
                diag_info += f"Sample data:\n{sample}\n\n"
        else:
            diag_info += f"Diagnostic {i+1}: FAILED - {diag.get('error', 'Unknown error')}\n"
    
    prompt = f"""You are a data analyst fixing a {dialect.upper()} SQL query that failed.

ORIGINAL QUESTION: {question}

FAILED SQL:
{failed_sql}

DATABASE ERROR: 
{db_error}

DIAGNOSTIC RESULTS:
{diag_info}

Based on the diagnostic information, produce a corrected {dialect.upper()} SQL query that:
- Fixes the specific error that occurred
- Uses correct table/column names as revealed by diagnostics
- Handles the data types and formats found
- Answers the original question

OUTPUT FORMAT:
Return a JSON object:
{{
    "sql": "<corrected SQL query>",
    "what_changed": "<brief explanation of what was fixed>"
}}

Write only valid {dialect.upper()} SQL."""
    
    return prompt


def _format_schema_info(schema_card: Dict[str, Any]) -> str:
    """Format schema information for prompts."""
    if not schema_card.get("tables"):
        return "Schema information not available."
    
    info = []
    for table, details in schema_card["tables"].items():
        columns = details.get("columns", [])
        col_info = []
        for col in columns:
            col_type = col.get("type", "unknown")
            nullable = " NULL" if col.get("nullable", True) else " NOT NULL"
            pk = " PRIMARY KEY" if col.get("primary_key", False) else ""
            col_info.append(f"  {col['name']} {col_type}{nullable}{pk}")
        
        info.append(f"Table: {table}")
        info.append("\n".join(col_info))
        
        # Add sample data if available
        if details.get("sample_rows"):
            info.append("Sample data:")
            for row in details["sample_rows"][:3]:
                info.append(f"  {row}")
        
        info.append("")  # Empty line between tables
    
    return "\n".join(info)


def _format_capability_hints(caps: Dict[str, Any]) -> str:
    """Format capability hints for prompts."""
    hints = []
    
    if caps.get("limit"):
        hints.append(f"- Use `{caps['limit']}` for limiting results")
    
    if caps.get("date_trunc"):
        hints.append(f"- Use `{caps['date_trunc']}` for date grouping")
    
    if caps.get("timezone"):
        hints.append(f"- Use `{caps['timezone']}` for timezone conversion")
    
    if caps.get("string_agg"):
        hints.append(f"- Use `{caps['string_agg']}` for string aggregation")
    
    if caps.get("ilike"):
        hints.append("- Use `ILIKE` for case-insensitive text search")
    else:
        hints.append("- Use `LOWER(col) LIKE LOWER(pattern)` for case-insensitive search")
    
    if caps.get("qualify"):
        hints.append("- Use `QUALIFY` clause for window function filtering")
    
    if caps.get("backticks"):
        hints.append("- Use backticks for table/column identifiers")
    elif caps.get("identifier_quote"):
        quote = caps["identifier_quote"]
        hints.append(f"- Use {quote} for table/column identifiers when needed")
    
    return "\n".join(hints)


def _format_examples(examples: List[str]) -> str:
    """Format SQL examples for prompts."""
    if not examples:
        return "No examples available."
    
    formatted = []
    for i, example in enumerate(examples, 1):
        formatted.append(f"{i}. {example}")
    
    return "\n".join(formatted) 