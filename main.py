"""
Main entry point for the Analyst Agent service.

This module provides the application entry point for ASGI servers like uvicorn.
"""

import uvicorn
from analyst_agent.api.app import app
from analyst_agent.settings import settings


def main() -> None:
    """Main entry point for the application."""
    uvicorn.run(
        "analyst_agent.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main() 