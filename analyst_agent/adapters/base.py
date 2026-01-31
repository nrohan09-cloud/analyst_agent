"""
Base connector interface for data source adapters.

Defines the protocol that all data source connectors must implement
to provide a consistent interface for the analysis engine.
"""

from typing import Protocol, Any, Dict, List, Optional, runtime_checkable
import pyarrow as pa


@runtime_checkable
class Connector(Protocol):
    """
    Protocol for data source connectors.
    
    All connectors must implement this interface to provide consistent
    access to different data sources (SQL databases, files, NoSQL, etc.).
    """
    
    name: str
    kind: str  # "sql" | "nosql" | "file"
    dialect: Optional[str]  # e.g., "postgres", "bigquery", "snowflake", etc.

    def list_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        List available tables in the data source.
        
        Args:
            schema: Optional schema name to filter tables
            
        Returns:
            List of table names
        """
        ...

    def get_columns(self, table: str) -> List[Dict[str, Any]]:
        """
        Get column information for a table.
        
        Args:
            table: Table name
            
        Returns:
            List of column dictionaries with name, type, nullable, etc.
        """
        ...

    def get_constraints(self, table: str) -> Dict[str, Any]:
        """
        Get table-level constraint information.
        
        Args:
            table: Table name
            
        Returns:
            Dictionary with primary_key, foreign_keys, unique_constraints,
            and check_constraints entries.
        """
        ...

    def profile_counts(self, table: str, ts_col: Optional[str] = None) -> Dict[str, Any]:
        """
        Get basic profiling information for a table.
        
        Args:
            table: Table name
            ts_col: Optional timestamp column for time-based profiling
            
        Returns:
            Dictionary with row counts, date ranges, etc.
        """
        ...

    def run_sql(
        self, 
        sql: str, 
        params: Optional[Dict[str, Any]] = None, 
        limit: Optional[int] = None
    ) -> pa.Table:
        """
        Execute SQL query and return results as Arrow table.
        
        Args:
            sql: SQL query string
            params: Optional query parameters
            limit: Optional row limit
            
        Returns:
            Arrow table with query results
        """
        ...

    def read_table(
        self, 
        table: str, 
        columns: Optional[List[str]] = None, 
        limit: Optional[int] = None
    ) -> pa.Table:
        """
        Read data from a table directly.
        
        Args:
            table: Table name
            columns: Optional list of columns to read
            limit: Optional row limit
            
        Returns:
            Arrow table with table data
        """
        ...

    def supports_sql(self) -> bool:
        """
        Check if connector supports SQL queries.
        
        Returns:
            True if SQL is supported
        """
        ...

    def quote_ident(self, ident: str) -> str:
        """
        Quote an identifier for safe use in SQL.
        
        Args:
            ident: Identifier to quote
            
        Returns:
            Quoted identifier
        """
        ...

    def limit_clause(self, n: int) -> str:
        """
        Generate a LIMIT clause for the dialect.
        
        Args:
            n: Number of rows to limit
            
        Returns:
            Dialect-specific LIMIT clause
        """
        ...

    def close(self) -> None:
        """Close any open connections."""
        ...


class BaseConnector:
    """
    Base implementation providing common functionality.
    
    Connectors can inherit from this class to get default implementations
    of common methods and utilities.
    """
    
    def __init__(self, name: str, kind: str, dialect: Optional[str] = None):
        self.name = name
        self.kind = kind
        self.dialect = dialect
        self._closed = False

    def supports_sql(self) -> bool:
        """Default implementation based on kind."""
        return self.kind == "sql"

    def quote_ident(self, ident: str) -> str:
        """Default identifier quoting using double quotes."""
        if self.dialect in ("mysql",):
            return f"`{ident}`"
        elif self.dialect in ("mssql",):
            return f"[{ident}]"
        else:
            return f'"{ident}"'

    def get_constraints(self, table: str) -> Dict[str, Any]:
        """Return empty constraint information by default."""
        return {
            "primary_key": {"name": None, "columns": []},
            "foreign_keys": [],
            "unique_constraints": [],
            "check_constraints": [],
        }

    def limit_clause(self, n: int) -> str:
        """Default LIMIT clause implementation."""
        if self.dialect in ("mssql",):
            return f"TOP {n}"  # Note: goes after SELECT
        else:
            return f"LIMIT {n}"

    def close(self) -> None:
        """Mark connector as closed."""
        self._closed = True

    def _check_closed(self) -> None:
        """Check if connector is closed and raise error if so."""
        if self._closed:
            raise RuntimeError(f"Connector {self.name} is closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 
