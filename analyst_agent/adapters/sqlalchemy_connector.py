"""
SQLAlchemy-based connector for SQL databases.

Provides connectivity to various SQL databases (PostgreSQL, MySQL, SQLite, etc.)
using SQLAlchemy as the underlying driver abstraction layer.
"""

from typing import Dict, List, Optional, Any
import time
import pandas as pd
import pyarrow as pa
import uuid
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
import structlog

from .base import BaseConnector
from .registry import register

logger = structlog.get_logger(__name__)


class SQLAlchemyConnector(BaseConnector):
    """
    Universal SQL connector using SQLAlchemy.
    
    Supports multiple SQL databases including PostgreSQL, MySQL, SQLite,
    SQL Server, and others through SQLAlchemy's unified interface.
    """
    
    def __init__(
        self, 
        url: str, 
        schema: Optional[str] = None, 
        business_tz: str = "Asia/Kolkata",
        dialect: str = "postgres",
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        **engine_kwargs
    ):
        """
        Initialize SQLAlchemy connector.
        
        Args:
            url: Database connection URL
            schema: Default schema name
            business_tz: Business timezone for date operations
            dialect: SQL dialect identifier
            pool_size: Connection pool size
            max_overflow: Maximum pool overflow
            pool_timeout: Connection timeout
            **engine_kwargs: Additional SQLAlchemy engine arguments
        """
        super().__init__(
            name=f"sqlalchemy:{dialect}",
            kind="sql", 
            dialect=dialect
        )
        
        self.url = url
        self.schema = schema
        self.business_tz = business_tz
        
        # Create SQLAlchemy engine with connection pooling
        engine_config = {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_pre_ping": True,  # Validate connections before use
            **engine_kwargs
        }
        
        try:
            self.engine = create_engine(url, **engine_config)
            logger.info(
                "Created SQLAlchemy connector",
                dialect=dialect,
                schema=schema,
                url_scheme=self.engine.url.drivername
            )
        except Exception as e:
            logger.error("Failed to create SQLAlchemy engine", error=str(e))
            raise
    
    def list_tables(self, schema: Optional[str] = None) -> List[str]:
        """List available tables in the database."""
        self._check_closed()
        
        target_schema = schema or self.schema
        
        try:
            with self.engine.connect() as conn:
                inspector = inspect(conn)
                tables = inspector.get_table_names(schema=target_schema)
                
                logger.debug(
                    "Listed tables",
                    schema=target_schema,
                    count=len(tables)
                )
                
                return tables
                
        except SQLAlchemyError as e:
            logger.error("Failed to list tables", schema=target_schema, error=str(e))
            raise
    
    def get_columns(self, table: str) -> List[Dict[str, Any]]:
        """Get column information for a table."""
        self._check_closed()
        
        try:
            with self.engine.connect() as conn:
                inspector = inspect(conn)
                columns = inspector.get_columns(table, schema=self.schema)
                
                # Normalize column information
                result = []
                for col in columns:
                    result.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "default": col.get("default"),
                        "primary_key": col.get("primary_key", False),
                        "autoincrement": col.get("autoincrement", False),
                    })
                
                logger.debug(
                    "Retrieved column info",
                    table=table,
                    column_count=len(result)
                )
                
                return result
                
        except SQLAlchemyError as e:
            logger.error("Failed to get columns", table=table, error=str(e))
            raise
    
    def profile_counts(self, table: str, ts_col: Optional[str] = None) -> Dict[str, Any]:
        """Get basic profiling information for a table."""
        self._check_closed()
        
        try:
            with self.engine.connect() as conn:
                # Basic row count
                count_sql = f"SELECT COUNT(*) as total_rows FROM {self.quote_ident(table)}"
                result = conn.execute(text(count_sql)).fetchone()
                total_rows = result[0] if result else 0
                
                profile = {
                    "total_rows": total_rows,
                    "table": table,
                    "schema": self.schema,
                }
                
                # Time-based profiling if timestamp column provided
                if ts_col and total_rows > 0:
                    ts_sql = f"""
                    SELECT 
                        MIN({self.quote_ident(ts_col)}) as min_date,
                        MAX({self.quote_ident(ts_col)}) as max_date
                    FROM {self.quote_ident(table)}
                    WHERE {self.quote_ident(ts_col)} IS NOT NULL
                    """
                    ts_result = conn.execute(text(ts_sql)).fetchone()
                    
                    if ts_result and ts_result[0]:
                        profile.update({
                            "min_date": ts_result[0],
                            "max_date": ts_result[1],
                            "date_column": ts_col,
                        })
                
                logger.debug(
                    "Profiled table",
                    table=table,
                    total_rows=total_rows,
                    has_dates=bool(ts_col and profile.get("min_date"))
                )
                
                return profile
                
        except SQLAlchemyError as e:
            logger.error("Failed to profile table", table=table, error=str(e))
            raise
    
    def run_sql(
        self, 
        sql: str, 
        params: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> pa.Table:
        """Execute SQL query and return results as Arrow table."""
        self._check_closed()
        
        # Add limit if specified and not already present
        if limit is not None and "LIMIT" not in sql.upper() and "TOP" not in sql.upper():
            if self.dialect == "mssql":
                # SQL Server uses TOP which goes after SELECT
                if sql.strip().upper().startswith("SELECT"):
                    sql = sql.replace("SELECT", f"SELECT TOP {limit}", 1)
            else:
                sql = f"{sql} {self.limit_clause(limit)}"
        
        start_time = time.perf_counter()
        
        try:
            with self.engine.connect() as conn:
                # Execute query with pandas for easier Arrow conversion
                df = pd.read_sql_query(text(sql), conn, params=params)
                
                # Convert to Arrow table with UUID-safe fallback
                table = self._to_arrow(df)
                
                duration = round((time.perf_counter() - start_time) * 1000, 2)
                
                logger.info(
                    "Executed SQL query",
                    rows=len(df),
                    columns=len(df.columns),
                    duration_ms=duration,
                    sql_preview=sql[:100] + "..." if len(sql) > 100 else sql
                )
                
                return table
                
        except SQLAlchemyError as e:
            duration = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "SQL query failed",
                error=str(e),
                duration_ms=duration,
                sql_preview=sql[:200] + "..." if len(sql) > 200 else sql
            )
            raise
    
    def read_table(
        self, 
        table: str, 
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> pa.Table:
        """Read data from a table directly."""
        self._check_closed()
        
        # Build SELECT statement
        if columns:
            cols = ", ".join(self.quote_ident(col) for col in columns)
        else:
            cols = "*"
        
        sql = f"SELECT {cols} FROM {self.quote_ident(table)}"
        
        if limit:
            if self.dialect == "mssql":
                sql = f"SELECT TOP {limit} {cols} FROM {self.quote_ident(table)}"
            else:
                sql += f" {self.limit_clause(limit)}"
        
        return self.run_sql(sql)
    
    def _to_arrow(self, df: pd.DataFrame) -> pa.Table:
        """Convert pandas DataFrame to Arrow, normalizing unsupported types."""
        try:
            return pa.Table.from_pandas(df, preserve_index=False)
        except (TypeError, pa.ArrowInvalid) as err:
            logger.debug("Retrying pandas→arrow conversion after type normalization", error=str(err))
        
        normalized = df.copy()
        
        for col in normalized.columns:
            series = normalized[col]
            
            if series.dtype == "object":
                # Convert UUID objects (and other non-null objects) to strings
                def _coerce(val: Any) -> Any:
                    if isinstance(val, uuid.UUID):
                        return str(val)
                    return val
                
                normalized[col] = series.map(_coerce)
                
                # If column still object, coerce entire column to pandas string dtype
                if normalized[col].dtype == "object":
                    normalized[col] = normalized[col].astype("string")
        
        return pa.Table.from_pandas(normalized, preserve_index=False)
    
    def close(self) -> None:
        """Close the database connection."""
        if not self._closed and hasattr(self, 'engine'):
            self.engine.dispose()
            logger.info("Closed SQLAlchemy connector", name=self.name)
        super().close()


# Register common SQL database connectors
@register("postgres")
class PostgreSQLConnector(SQLAlchemyConnector):
    def __init__(self, **kwargs):
        kwargs.setdefault("dialect", "postgres")
        super().__init__(**kwargs)


@register("mysql")  
class MySQLConnector(SQLAlchemyConnector):
    def __init__(self, **kwargs):
        kwargs.setdefault("dialect", "mysql")
        super().__init__(**kwargs)


@register("sqlite")
class SQLiteConnector(SQLAlchemyConnector):
    def __init__(self, **kwargs):
        kwargs.setdefault("dialect", "sqlite")
        super().__init__(**kwargs)


@register("mssql")
class SQLServerConnector(SQLAlchemyConnector):
    def __init__(self, **kwargs):
        kwargs.setdefault("dialect", "mssql")
        super().__init__(**kwargs)


@register("snowflake")
class SnowflakeConnector(SQLAlchemyConnector):
    def __init__(self, **kwargs):
        kwargs.setdefault("dialect", "snowflake")
        super().__init__(**kwargs)


@register("duckdb")
class DuckDBConnector(SQLAlchemyConnector):
    def __init__(self, **kwargs):
        kwargs.setdefault("dialect", "duckdb")
        super().__init__(**kwargs) 
