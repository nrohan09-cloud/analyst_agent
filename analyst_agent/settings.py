"""
Configuration settings for the Analyst Agent service.

Uses Pydantic Settings to manage environment variables and configuration
with proper validation and type checking.
"""

from typing import Optional, List
from pydantic import Field, validator, AliasChoices
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = Field(default="Analyst Agent", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(
        default=False,
        description="Debug mode",
        validation_alias=AliasChoices("DEBUG", "debug"),
    )
    
    # API settings
    api_host: str = Field(
        default="0.0.0.0",
        description="API host",
        validation_alias=AliasChoices("API_HOST", "api_host"),
    )
    api_port: int = Field(
        default=8000,
        description="API port",
        validation_alias=AliasChoices("API_PORT", "api_port"),
    )
    api_prefix: str = Field(default="/v1", description="API prefix")
    
    # Security settings
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for JWT tokens"
    )
    access_token_expire_minutes: int = Field(
        default=30, 
        description="Access token expiration time in minutes"
    )
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # Database settings
    database_url: Optional[str] = Field(
        default=None,
        description="Database connection URL"
    )
    database_pool_size: int = Field(
        default=10,
        description="Database connection pool size"
    )
    
    # LLM Provider settings
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    default_llm_provider: str = Field(
        default="openai",
        description="Default LLM provider (openai, anthropic, etc.)"
    )
    default_llm_model: str = Field(
        default="gpt-4o",
        description="Default LLM model",
        validation_alias=AliasChoices("DEFAULT_LLM_MODEL", "default_llm_model"),
    )
    llm_temperature: float = Field(
        default=0.0,
        description="Default LLM temperature (0.0-1.0)",
        validation_alias=AliasChoices("LLM_TEMPERATURE", "TEMPERATURE", "llm_temperature"),
    )

    # LangSmith settings
    langsmith_tracing: bool = Field(
        default=False,
        description="Enable LangSmith tracing",
        validation_alias=AliasChoices("LANGSMITH_TRACING", "langsmith_tracing"),
    )
    langsmith_api_key: Optional[str] = Field(
        default=None,
        description="LangSmith API key",
        validation_alias=AliasChoices("LANGSMITH_API_KEY", "langsmith_api_key"),
    )
    langsmith_endpoint: Optional[str] = Field(
        default=None,
        description="LangSmith endpoint URL",
        validation_alias=AliasChoices("LANGSMITH_ENDPOINT", "langsmith_endpoint"),
    )
    langsmith_project: Optional[str] = Field(
        default=None,
        description="LangSmith project name",
        validation_alias=AliasChoices("LANGSMITH_PROJECT", "LANGCHAIN_PROJECT", "langsmith_project"),
    )
    
    # Analysis settings
    max_execution_time: int = Field(
        default=300,
        description="Maximum execution time for analysis in seconds"
    )
    max_memory_mb: int = Field(
        default=1024,
        description="Maximum memory usage for analysis in MB"
    )
    enable_code_execution: bool = Field(
        default=True,
        description="Enable safe code execution for analysis"
    )
    
    # LangGraph / workflow settings
    graph_recursion_limit: int = Field(
        default=25,
        description="LangGraph recursion limit for workflow loops",
        validation_alias=AliasChoices("RECURSION_LIMIT", "GRAPH_RECURSION_LIMIT", "LANGGRAPH_RECURSION_LIMIT"),
    )
    
    # Logging settings
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json, text)"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @validator("default_llm_provider")
    def validate_llm_provider(cls, v):
        valid_providers = ["openai", "anthropic", "local"]
        if v.lower() not in valid_providers:
            raise ValueError(f"default_llm_provider must be one of {valid_providers}")
        return v.lower()

    @validator("graph_recursion_limit")
    def validate_graph_recursion_limit(cls, v):
        # Keep within sane bounds to avoid runaway loops
        try:
            iv = int(v)
        except Exception:
            raise ValueError("graph_recursion_limit must be an integer")
        if iv < 5:
            iv = 5
        if iv > 500:
            iv = 500
        return iv

    @validator("llm_temperature")
    def validate_llm_temperature(cls, v):
        try:
            fv = float(v)
        except Exception:
            raise ValueError("llm_temperature must be a float")
        if fv < 0.0:
            fv = 0.0
        if fv > 1.0:
            fv = 1.0
        return fv


# Global settings instance
settings = Settings() 