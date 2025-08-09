"""
Connector registry and factory for managing data source adapters.

Provides a centralized system for registering and creating connectors
for different data source types.
"""

from typing import Dict, Type, Any, Optional
import structlog
from .base import Connector

logger = structlog.get_logger(__name__)

# Global registry of connector classes
CONNECTORS: Dict[str, Type[Connector]] = {}


def register(kind: str):
    """
    Decorator to register a connector class for a specific kind.
    
    Args:
        kind: The data source kind (e.g., "postgres", "mysql", "snowflake")
        
    Example:
        @register("postgres")
        class PostgresConnector(BaseConnector):
            ...
    """
    def _wrap(cls: Type[Connector]) -> Type[Connector]:
        CONNECTORS[kind] = cls
        logger.info("Registered connector", kind=kind, class_name=cls.__name__)
        return cls
    return _wrap


def make_connector(kind: str, **kwargs) -> Connector:
    """
    Create a connector instance for the specified kind.
    
    Args:
        kind: The data source kind
        **kwargs: Configuration parameters for the connector
        
    Returns:
        Configured connector instance
        
    Raises:
        ValueError: If the connector kind is not supported
    """
    if kind not in CONNECTORS:
        available = list(CONNECTORS.keys())
        raise ValueError(
            f"Unsupported connector kind: {kind}. "
            f"Available kinds: {available}"
        )
    
    connector_class = CONNECTORS[kind]
    
    try:
        logger.info("Creating connector", kind=kind, class_name=connector_class.__name__)
        return connector_class(**kwargs)
    except Exception as e:
        logger.error("Failed to create connector", kind=kind, error=str(e))
        raise


def list_available_connectors() -> Dict[str, str]:
    """
    Get a list of all available connector kinds and their class names.
    
    Returns:
        Dictionary mapping connector kinds to class names
    """
    return {kind: cls.__name__ for kind, cls in CONNECTORS.items()}


def get_connector_info(kind: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a specific connector.
    
    Args:
        kind: The connector kind
        
    Returns:
        Dictionary with connector information or None if not found
    """
    if kind not in CONNECTORS:
        return None
    
    cls = CONNECTORS[kind]
    return {
        "kind": kind,
        "class_name": cls.__name__,
        "module": cls.__module__,
        "doc": cls.__doc__,
    } 