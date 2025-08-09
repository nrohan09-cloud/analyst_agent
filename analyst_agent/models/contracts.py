"""
Data contracts for the Analyst Agent API.

These models define the interface between the FastAPI backend and TypeScript SDK,
with support for multiple database dialects and direct SQL generation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


class SupportedDialect(str, Enum):
    """Supported SQL dialects for direct query generation."""
    POSTGRES = "postgres"
    MYSQL = "mysql" 
    MSSQL = "mssql"
    SQLITE = "sqlite"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    DUCKDB = "duckdb"
    TRINO = "trino"
    CLICKHOUSE = "clickhouse"


class ValidationProfile(str, Enum):
    """Validation strictness levels."""
    FAST = "fast"           # Basic checks only
    BALANCED = "balanced"   # Standard validation suite
    STRICT = "strict"       # Full validation with stability checks


class DataSource(BaseModel):
    """Generic data source configuration supporting multiple database types."""
    kind: str = Field(..., description="Database type (postgres, mysql, snowflake, etc.)")
    config: Dict[str, Any] = Field(..., description="Connection configuration (DSN, credentials, etc.)")
    business_tz: str = Field(default="Asia/Kolkata", description="Business timezone for date operations")
    
    class Config:
        extra = "allow"


class QuerySpec(BaseModel):
    """Specification for a data analysis query."""
    question: str = Field(..., min_length=1, max_length=2000, description="Natural language question")
    dialect: SupportedDialect = Field(..., description="Target SQL dialect for query generation")
    time_window: Optional[str] = Field(None, description="Time window filter (e.g., 'last_6_months')")
    grain: Optional[str] = Field(None, description="Time granularity (month, day, hour)")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters")
    budget: Dict[str, int] = Field(
        default_factory=lambda: {"queries": 30, "seconds": 90},
        description="Resource limits for execution"
    )
    validation_profile: ValidationProfile = Field(
        default=ValidationProfile.BALANCED,
        description="Validation strictness level"
    )


class ArtifactType(str, Enum):
    """Types of artifacts generated during analysis."""
    TABLE = "table"
    CHART = "chart" 
    LOG = "log"
    SQL = "sql"


class Artifact(BaseModel):
    """Analysis artifact (table, chart, log, etc.)."""
    id: str = Field(..., description="Unique artifact identifier")
    kind: ArtifactType = Field(..., description="Type of artifact")
    title: str = Field(..., description="Human-readable title")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Artifact metadata")
    content: Optional[Dict[str, Any]] = Field(None, description="Artifact content/data")
    file_path: Optional[str] = Field(None, description="Path to artifact file if stored separately")


class QualityGate(BaseModel):
    """Individual quality gate result."""
    name: str = Field(..., description="Gate name")
    passed: bool = Field(..., description="Whether gate passed")
    score: float = Field(..., ge=0.0, le=1.0, description="Gate score (0.0-1.0)")
    message: Optional[str] = Field(None, description="Gate result message")


class QualityReport(BaseModel):
    """Quality assessment report for analysis results."""
    passed: bool = Field(..., description="Overall quality check passed")
    score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    gates: List[QualityGate] = Field(default_factory=list, description="Individual gate results")
    notes: List[str] = Field(default_factory=list, description="Quality assessment notes")
    reconciliation: Dict[str, float] = Field(
        default_factory=dict, 
        description="Reconciliation deltas across validation paths"
    )
    plateau: bool = Field(default=False, description="Whether improvement has plateaued")


class ExecutionStep(BaseModel):
    """Individual step in the analysis execution graph."""
    step_name: str = Field(..., description="Name of the execution step")
    status: str = Field(..., description="Step execution status")
    start_time: Optional[datetime] = Field(None, description="Step start timestamp")
    end_time: Optional[datetime] = Field(None, description="Step completion timestamp")
    duration_ms: Optional[float] = Field(None, description="Step duration in milliseconds")
    sql: Optional[str] = Field(None, description="SQL executed in this step")
    row_count: Optional[int] = Field(None, description="Number of rows processed")
    error: Optional[str] = Field(None, description="Error message if step failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Step-specific metadata")


class RunResult(BaseModel):
    """Complete analysis run result."""
    job_id: str = Field(..., description="Unique job identifier")
    answer: str = Field(..., description="Natural language answer to the question")
    tables: List[Artifact] = Field(default_factory=list, description="Table artifacts")
    charts: List[Artifact] = Field(default_factory=list, description="Chart artifacts")
    quality: QualityReport = Field(..., description="Quality assessment")
    lineage: Dict[str, Any] = Field(default_factory=dict, description="Data lineage and execution metadata")
    execution_steps: List[ExecutionStep] = Field(default_factory=list, description="Detailed execution trace")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Result creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


# Legacy compatibility for existing API
class AnalysisRequest(BaseModel):
    """Legacy analysis request format for backward compatibility."""
    question: str = Field(..., description="Natural language question")
    data_source: DataSource = Field(..., description="Data source configuration")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Analysis preferences")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

    def to_query_spec(self, dialect: SupportedDialect) -> QuerySpec:
        """Convert to new QuerySpec format."""
        return QuerySpec(
            question=self.question,
            dialect=dialect,
            time_window=self.preferences.get("time_window") if self.preferences else None,
            grain=self.preferences.get("grain") if self.preferences else None,
            filters=self.context or {},
            budget=self.preferences.get("budget", {"queries": 30, "seconds": 90}) if self.preferences else {"queries": 30, "seconds": 90},
            validation_profile=ValidationProfile.BALANCED
        )


class AnalysisResponse(BaseModel):
    """Legacy analysis response format."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    result: Optional[RunResult] = Field(None, description="Analysis result if completed")
    message: str = Field(default="Analysis request received", description="Status message")


class JobStatusResponse(BaseModel):
    """Job status check response."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="Completion progress")
    current_step: Optional[str] = Field(None, description="Currently executing step")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    result: Optional[RunResult] = Field(None, description="Final result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")


# Validators
@validator("budget", pre=True)
def validate_budget(cls, v):
    """Ensure budget has required fields with reasonable defaults."""
    if not isinstance(v, dict):
        return {"queries": 30, "seconds": 90}
    
    result = {"queries": 30, "seconds": 90}
    result.update(v)
    
    # Enforce reasonable limits
    result["queries"] = max(1, min(result["queries"], 100))
    result["seconds"] = max(10, min(result["seconds"], 600))
    
    return result 