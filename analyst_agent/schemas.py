"""
Pydantic schemas for API request/response models and data structures.

These models define the contract for the REST API and ensure proper
validation and serialization of data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


class DataSourceType(str, Enum):
    """Supported data source types."""
    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    CSV = "csv"
    PARQUET = "parquet"
    JSON = "json"


class AnalysisType(str, Enum):
    """Types of analysis that can be performed."""
    DESCRIPTIVE = "descriptive"
    INFERENTIAL = "inferential"
    PREDICTIVE = "predictive"
    EXPLORATORY = "exploratory"
    DIAGNOSTIC = "diagnostic"


class ChartType(str, Enum):
    """Supported chart types."""
    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    BOX = "box"
    HEATMAP = "heatmap"
    PIE = "pie"


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DataSourceConfig(BaseModel):
    """Configuration for connecting to a data source."""
    type: DataSourceType
    connection_string: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    file_path: Optional[str] = None
    table_name: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow additional fields for extensibility


class AnalysisPreferences(BaseModel):
    """User preferences for analysis."""
    analysis_types: List[AnalysisType] = Field(
        default=[AnalysisType.DESCRIPTIVE],
        description="Types of analysis to perform"
    )
    max_execution_time: Optional[int] = Field(
        default=None,
        description="Maximum execution time in seconds"
    )
    chart_types: List[ChartType] = Field(
        default=[],
        description="Preferred chart types for visualization"
    )
    include_code: bool = Field(
        default=False,
        description="Include generated code in response"
    )
    confidence_threshold: float = Field(
        default=0.8,
        description="Minimum confidence threshold for insights"
    )


class AnalysisRequest(BaseModel):
    """Request model for analysis endpoint."""
    question: str = Field(
        ...,
        description="Natural language question about the data",
        min_length=1,
        max_length=1000
    )
    data_source: DataSourceConfig = Field(
        ...,
        description="Data source configuration"
    )
    preferences: Optional[AnalysisPreferences] = Field(
        default=None,
        description="Analysis preferences"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context for the analysis"
    )


class Chart(BaseModel):
    """Chart/visualization data."""
    title: str
    type: ChartType
    data: Dict[str, Any]  # Chart-specific data structure
    config: Optional[Dict[str, Any]] = None  # Chart configuration
    base64_image: Optional[str] = None  # Base64 encoded image
    html: Optional[str] = None  # HTML representation


class Insight(BaseModel):
    """Individual insight from analysis."""
    title: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    type: AnalysisType
    supporting_data: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None


class ExecutionStep(BaseModel):
    """Individual step in the analysis execution."""
    step_name: str
    description: str
    status: JobStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    output: Optional[Any] = None
    error: Optional[str] = None


class AnalysisResult(BaseModel):
    """Complete analysis result."""
    job_id: str
    status: JobStatus
    question: str
    summary: str
    insights: List[Insight] = []
    charts: List[Chart] = []
    tables: List[Dict[str, Any]] = []
    generated_code: Optional[str] = None
    execution_steps: List[ExecutionStep] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Response model for analysis endpoint."""
    job_id: str
    status: JobStatus
    result: Optional[AnalysisResult] = None
    message: str = "Analysis request received"


class JobStatusResponse(BaseModel):
    """Response model for job status endpoint."""
    job_id: str
    status: JobStatus
    progress: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Progress as percentage (0.0 to 1.0)"
    )
    current_step: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    result: Optional[AnalysisResult] = None


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: datetime
    version: str
    uptime_seconds: float
    dependencies: Dict[str, str] = {}  # dependency_name -> status


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime


# Validation helpers
@validator("confidence", pre=True)
def validate_confidence(cls, v):
    """Ensure confidence is between 0 and 1."""
    if not 0.0 <= v <= 1.0:
        raise ValueError("Confidence must be between 0.0 and 1.0")
    return v 