"""
Data adapters for connecting to various data sources.

Provides a pluggable interface for database connectivity with support for
SQL and NoSQL databases, file formats, and cloud data platforms.
"""

from .base import Connector
from .registry import make_connector, register
from .sqlalchemy_connector import SQLAlchemyConnector

__all__ = [
    "Connector",
    "make_connector", 
    "register",
    "SQLAlchemyConnector",
] 