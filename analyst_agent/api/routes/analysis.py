"""
Analysis API routes using the new connector system and LangGraph workflow.

Provides endpoints for running data analysis queries with support for multiple
database dialects and async workflow execution.
"""

import uuid
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
import structlog
from urllib.parse import quote_plus

from analyst_agent.models.contracts import (
    QuerySpec, 
    DataSource, 
    RunResult,
    AnalysisRequest,
    AnalysisResponse,
    JobStatusResponse,
    SupportedDialect,
    Artifact,
    QualityReport,
    QualityGate,
    ExecutionStep
)
from analyst_agent.adapters import make_connector
from analyst_agent.core.graph import run_analysis_async
from analyst_agent.core.state import add_execution_step as _add_execution_step
from analyst_agent.settings import settings


logger = structlog.get_logger(__name__)


def streaming_add_execution_step(
    state,
    step_name: str,
    status: str,
    duration_ms: Optional[float] = None,
    sql: Optional[str] = None,
    row_count: Optional[int] = None,
    error: Optional[str] = None,
    **metadata
):
    """Enhanced execution step tracker that updates job store for streaming."""
    # Call the original function
    result = _add_execution_step(
        state, step_name, status, duration_ms, sql, row_count, error, **metadata
    )
    
    # Update job store for streaming
    job_id = state.get("job_id")
    if job_id and job_id in job_store:
        # Get the latest step
        execution_steps = state.get("execution_steps", [])
        if execution_steps:
            latest_step = execution_steps[-1]
            
            # Update job store with streaming-friendly data
            if "execution_steps" not in job_store[job_id]:
                job_store[job_id]["execution_steps"] = []
            
            job_store[job_id]["execution_steps"] = execution_steps
            job_store[job_id]["current_step"] = step_name
            
            # Update overall job status
            if status == "failed" and not job_store[job_id].get("error"):
                job_store[job_id]["error"] = error
    
    return result


# Monkey patch the execution step function for streaming
try:
    import analyst_agent.core.nodes as nodes_module
    nodes_module.add_execution_step = streaming_add_execution_step
except ImportError:
    logger.warning("Could not import nodes module for streaming patch")

router = APIRouter()

# In-memory job store (replace with Redis/database in production)
job_store: Dict[str, Dict[str, Any]] = {}


def construct_database_url(kind: str, config: Dict[str, Any]) -> str:
    """
    Construct a database URL from individual connection parameters.
    
    Args:
        kind: Database type (postgres, mysql, etc.)
        config: Configuration with host, database, user, password, port
        
    Returns:
        Constructed database URL
    """
    user = config.get('user', '')
    password = config.get('password', '')
    host = config.get('host', 'localhost')
    port = config.get('port')
    database = config.get('database', '')
    
    # URL encode password to handle special characters
    if password:
        password = quote_plus(password)
    
    # Default ports for different database types
    default_ports = {
        'postgres': 5432,
        'mysql': 3306,
        'mssql': 1433,
        'sqlite': None,  # SQLite doesn't use host/port
        'snowflake': 443,
        'bigquery': None,  # BigQuery uses different auth
        'duckdb': None,
    }
    
    if not port and kind in default_ports and default_ports[kind]:
        port = default_ports[kind]
    
    # Construct URL based on database type
    if kind == 'sqlite':
        return f"sqlite:///{database}"
    elif kind == 'postgres':
        credentials = f"{user}:{password}@" if user else ""
        port_str = f":{port}" if port else ""
        return f"postgresql://{credentials}{host}{port_str}/{database}"
    elif kind == 'mysql':
        credentials = f"{user}:{password}@" if user else ""
        port_str = f":{port}" if port else ""
        return f"mysql+pymysql://{credentials}{host}{port_str}/{database}"
    elif kind == 'mssql':
        credentials = f"{user}:{password}@" if user else ""
        port_str = f":{port}" if port else ""
        return f"mssql+pyodbc://{credentials}{host}{port_str}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
    elif kind == 'snowflake':
        account = config.get('account', host)  # Snowflake uses account name
        warehouse = config.get('warehouse', 'COMPUTE_WH')
        schema = config.get('schema', 'PUBLIC')
        return f"snowflake://{user}:{password}@{account}/{database}/{schema}?warehouse={warehouse}"
    elif kind == 'duckdb':
        return f"duckdb:///{database}"
    else:
        # Generic fallback
        credentials = f"{user}:{password}@" if user else ""
        port_str = f":{port}" if port else ""
        return f"{kind}://{credentials}{host}{port_str}/{database}"


async def process_analysis_job(job_id: str, spec: QuerySpec, data_source: DataSource) -> None:
    """
    Background task to process analysis jobs using the LangGraph workflow.
    
    Args:
        job_id: Unique job identifier
        spec: Query specification
        data_source: Data source configuration
    """
    logger.info("Starting analysis job", job_id=job_id)
    
    job_store[job_id]["status"] = "running"
    job_store[job_id]["current_step"] = "initializing"
    
    try:
        # Create connector with URL construction if needed
        config = dict(data_source.config)
        
        # If no URL provided but individual connection params are available, construct URL
        if 'url' not in config and all(key in config for key in ['host', 'database', 'user']):
            url = construct_database_url(data_source.kind, config)
            config['url'] = url
            # Remove individual parameters that are now in the URL
            for key in ['host', 'database', 'user', 'password', 'port']:
                config.pop(key, None)
        
        connector = make_connector(
            kind=data_source.kind,
            **config,
            business_tz=data_source.business_tz
        )
        
        # Set up execution context
        ctx = {
            "connector": connector,
            "dialect": spec.dialect,
            "business_tz": data_source.business_tz
        }
        
        # Update job status
        job_store[job_id]["current_step"] = "running_analysis"
        
        # Run the analysis workflow
        final_state = await run_analysis_async(
            job_id=job_id,
            spec=spec.model_dump(),
            ctx=ctx
        )
        
        # Convert state to RunResult
        result = state_to_run_result(job_id, final_state)
        
        # Store result
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["result"] = result
        job_store[job_id]["completed_at"] = datetime.utcnow()
        
        # Close connector
        connector.close()
        
        logger.info(
            "Analysis job completed",
            job_id=job_id,
            quality_score=final_state.get("quality", {}).get("score", 0)
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Analysis job failed", job_id=job_id, error=error_msg)
        
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = error_msg
        job_store[job_id]["completed_at"] = datetime.utcnow()


def state_to_run_result(job_id: str, state: Dict[str, Any]) -> RunResult:
    """
    Convert analysis state to RunResult format.
    
    Args:
        job_id: Job identifier
        state: Final analysis state
        
    Returns:
        Formatted RunResult
    """
    # Convert artifacts
    artifacts = []
    for artifact in state.get("artifacts", []):
        # Ensure artifact content is JSON-serializable (e.g., dtypes)
        content = artifact.get("content")
        if isinstance(content, dict):
            summary = content.get("summary")
            if isinstance(summary, dict) and isinstance(summary.get("dtypes"), dict):
                # Convert any non-JSON-serializable dtype objects to strings
                summary["dtypes"] = {k: str(v) for k, v in summary["dtypes"].items()}
                content["summary"] = summary
        artifacts.append(Artifact(
            id=artifact["id"],
            kind=artifact["kind"],
            title=artifact["title"],
            meta=artifact.get("meta", {}),
            content=content,
            file_path=artifact.get("file_path")
        ))
    
    # Convert quality report
    quality_data = state.get("quality", {})
    gates = []
    for gate_name, passed in quality_data.get("gates", {}).items():
        gates.append(QualityGate(
            name=gate_name,
            passed=passed,
            score=1.0 if passed else 0.0,
            message=f"{gate_name} {'passed' if passed else 'failed'}"
        ))
    
    quality = QualityReport(
        passed=quality_data.get("passed", False),
        score=quality_data.get("score", 0.0),
        gates=gates,
        notes=quality_data.get("notes", []),
        reconciliation=quality_data.get("reconciliation", {}),
        plateau=quality_data.get("plateau", False)
    )
    
    # Convert execution steps
    execution_steps = []
    for step in state.get("execution_steps", []):
        execution_steps.append(ExecutionStep(
            step_name=step["step_name"],
            status=step["status"],
            start_time=step.get("start_time"),
            end_time=step.get("end_time"), 
            duration_ms=step.get("duration_ms"),
            sql=step.get("sql"),
            row_count=step.get("row_count"),
            error=step.get("error"),
            metadata=step.get("metadata", {})
        ))
    
    # Separate artifacts by type
    tables = [a for a in artifacts if a.kind == "table"]
    charts = [a for a in artifacts if a.kind == "chart"]
    
    # Handle datetime fields that might be strings or datetime objects
    created_at = state.get("created_at", datetime.utcnow())
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    elif not isinstance(created_at, datetime):
        created_at = datetime.utcnow()
    
    completed_at = None
    if state.get("completed_at"):
        completed_at_raw = state.get("completed_at")
        if isinstance(completed_at_raw, str):
            completed_at = datetime.fromisoformat(completed_at_raw)
        elif isinstance(completed_at_raw, datetime):
            completed_at = completed_at_raw
    
    return RunResult(
        job_id=job_id,
        answer=state.get("answer", "No answer generated"),
        tables=tables,
        charts=charts,
        quality=quality,
        lineage=state.get("lineage", {}),
        execution_steps=execution_steps,
        created_at=created_at,
        completed_at=completed_at
    )


@router.post("/query", response_model=RunResult)
async def run_query(
    spec: QuerySpec, 
    data_source: DataSource,
    background_tasks: BackgroundTasks
) -> RunResult:
    """
    Run a data analysis query using the new workflow system.
    
    This endpoint creates a new analysis job and returns the results
    directly (for synchronous execution) or job information (for async).
    """
    job_id = str(uuid.uuid4())
    
    logger.info(
        "Received analysis request",
        job_id=job_id,
        question=spec.question,
        dialect=spec.dialect,
        data_source_kind=data_source.kind
    )
    
    # Validate dialect support
    try:
        SupportedDialect(spec.dialect)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported dialect: {spec.dialect}"
        )
    
    # Initialize job tracking
    job_store[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "spec": spec.model_dump(),
        "data_source": data_source.model_dump(),
        "created_at": datetime.utcnow(),
        "current_step": None,
        "result": None,
        "error": None
    }
    
    # For small queries, run synchronously
    if spec.validation_profile.value == "fast":
        try:
            await process_analysis_job(job_id, spec, data_source)
            
            if job_store[job_id]["status"] == "completed":
                return job_store[job_id]["result"]
            else:
                error = job_store[job_id].get("error", "Unknown error")
                raise HTTPException(status_code=500, detail=f"Analysis failed: {error}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Synchronous analysis failed", job_id=job_id, error=str(e))
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    # For larger queries, run asynchronously
    else:
        background_tasks.add_task(process_analysis_job, job_id, spec, data_source)
        
        # Return partial result with job tracking info
        return RunResult(
            job_id=job_id,
            answer="Analysis is running. Check job status for updates.",
            tables=[],
            charts=[],
            quality=QualityReport(
                passed=False,
                score=0.0,
                gates=[],
                notes=["Analysis in progress"],
                reconciliation={},
                plateau=False
            ),
            lineage={"status": "running"},
            execution_steps=[],
            created_at=datetime.utcnow(),
            completed_at=None
        )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Get the status of an analysis job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Job status information
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_store[job_id]
    
    # Calculate progress based on status
    progress = None
    if job["status"] == "pending":
        progress = 0.0
    elif job["status"] == "running":
        progress = 0.5  # Rough estimate
    elif job["status"] in ["completed", "failed"]:
        progress = 1.0
    
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=progress,
        current_step=job.get("current_step"),
        estimated_completion=None,  # Could implement time estimation
        result=job.get("result"),
        error=job.get("error")
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str) -> JSONResponse:
    """
    Cancel a running analysis job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Cancellation status
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_store[job_id]
    
    if job["status"] in ["completed", "failed"]:
        return JSONResponse(
            content={"message": f"Job {job_id} already {job['status']}"},
            status_code=200
        )
    
    # Mark as cancelled (actual cancellation would require more complex logic)
    job["status"] = "cancelled"
    job["completed_at"] = datetime.utcnow()
    
    logger.info("Job cancelled", job_id=job_id)
    
    return JSONResponse(
        content={"message": f"Job {job_id} cancelled"},
        status_code=200
    )


@router.get("/stream/{job_id}")
async def stream_job_progress(job_id: str):
    """
    Stream real-time progress updates for an analysis job using Server-Sent Events.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        StreamingResponse with SSE events
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    def _json_safe(value):
        """Best-effort conversion of arbitrary objects to JSON-serializable structures."""
        # Fast path for primitives
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        # Datetime-like
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                return str(value)
        # Pydantic models
        if hasattr(value, "model_dump"):
            try:
                return value.model_dump(mode="json")
            except Exception:
                try:
                    return value.model_dump()
                except Exception:
                    return str(value)
        # Dict
        if isinstance(value, dict):
            return {str(k): _json_safe(v) for k, v in value.items()}
        # List/Tuple/Set
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(v) for v in value]
        # Fallback: string representation (covers numpy dtypes, Arrow types, etc.)
        return str(value)

    async def event_generator():
        """Generate SSE events for job progress."""
        last_step_count = 0
        last_status = None
        
        try:
            while True:
                if job_id not in job_store:
                    break
                    
                job = job_store[job_id]
                current_status = job.get("status", "pending")
                
                # Send status updates
                if current_status != last_status:
                    event_data = {
                        "type": "status",
                        "job_id": job_id,
                        "status": current_status,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    last_status = current_status
                
                # Send execution step updates
                steps = job.get("execution_steps", [])
                
                # Stream new execution steps
                if len(steps) > last_step_count:
                    for step in steps[last_step_count:]:
                        step_data = {
                            "type": "step",
                            "job_id": job_id,
                            "step_name": step.get("step_name"),
                            "status": step.get("status"),
                            "timestamp": step.get("timestamp").isoformat() if hasattr(step.get("timestamp", None), 'isoformat') else str(step.get("timestamp")),
                            "duration_ms": step.get("duration_ms"),
                            "sql": step.get("sql"),
                            "row_count": step.get("row_count"),
                            "error": step.get("error"),
                            "metadata": _json_safe(step.get("metadata", {}))
                        }
                        yield f"data: {json.dumps(step_data)}\n\n"
                    
                    last_step_count = len(steps)
                
                # Send progress update
                progress = calculate_job_progress(job)
                if progress is not None:
                    progress_data = {
                        "type": "progress",
                        "job_id": job_id,
                        "progress": progress,
                        "current_step": job.get("current_step"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(progress_data)}\n\n"
                
                # Send completion event and break
                if current_status in ["completed", "failed", "cancelled"]:
                    completion_data = {
                        "type": "completion",
                        "job_id": job_id,
                        "status": current_status,
                        "result": _json_safe(serialize_result(job.get("result"))) if current_status == "completed" else None,
                        "error": job.get("error"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(completion_data)}\n\n"
                    break
                
                # Wait before next update
                await asyncio.sleep(0.5)
                
        except Exception as e:
            error_data = {
                "type": "error",
                "job_id": job_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


def calculate_job_progress(job: Dict[str, Any]) -> Optional[float]:
    """Calculate job progress percentage based on execution steps."""
    status = job.get("status")
    
    if status == "pending":
        return 0.0
    elif status in ["completed", "failed", "cancelled"]:
        return 100.0
    elif status == "running":
        # Calculate based on completed steps
        steps = job.get("execution_steps", [])
        
        if not steps:
            return 10.0  # Started but no steps yet
        
        # Map step names to progress percentages
        step_weights = {
            "plan": 10,
            "profile": 20,
            "mvq": 40,
            "diagnose": 50,
            "refine": 60,
            "transform": 70,
            "produce": 80,
            "validate": 90,
            "present": 100
        }
        
        completed_steps = [s for s in steps if s.get("status") == "completed"]
        if not completed_steps: 
            return 15.0  # Some progress made
        
        # Get the highest progress from completed steps
        max_progress = 0
        for step in completed_steps:
            step_name = step.get("step_name")
            if step_name in step_weights:
                max_progress = max(max_progress, step_weights[step_name])
        
        return float(max_progress)
    
    return None


def serialize_result(result) -> Dict[str, Any]:
    """Serialize a result object for JSON transmission (JSON-safe)."""
    if result is None:
        return None
    
    # Prefer Pydantic's JSON-mode dump to coerce datetimes and enums
    if hasattr(result, 'model_dump'):
        try:
            return result.model_dump(mode="json")  # ensures JSON-serializable types
        except TypeError:
            # Fallback to default dump and let jsonable_encoder handle later if needed
            return result.model_dump()
    elif isinstance(result, dict):
        return result
    else:
        return {"serialization_error": "Could not serialize result"}


# Legacy compatibility endpoint
@router.post("/ask", response_model=AnalysisResponse)
async def ask_question(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
) -> AnalysisResponse:
    """
    Legacy endpoint for backward compatibility.
    
    Converts old request format to new system.
    """
    # Auto-detect dialect from data source kind
    dialect_mapping = {
        "postgres": SupportedDialect.POSTGRES,
        "mysql": SupportedDialect.MYSQL,
        "sqlite": SupportedDialect.SQLITE,
        "snowflake": SupportedDialect.SNOWFLAKE,
        "bigquery": SupportedDialect.BIGQUERY,
        "mssql": SupportedDialect.MSSQL
    }
    
    dialect = dialect_mapping.get(request.data_source.kind, SupportedDialect.POSTGRES)
    
    # Convert to new format
    spec = request.to_query_spec(dialect)
    
    # Run analysis
    result = await run_query(spec, request.data_source, background_tasks)
    
    return AnalysisResponse(
        job_id=result.job_id,
        status="completed" if result.quality.passed else "failed",
        result=result,
        message=result.answer
    )


@router.get("/dialects")
async def list_supported_dialects() -> Dict[str, Any]:
    """
    List all supported SQL dialects.
    
    Returns:
        Dictionary with supported dialects and their capabilities
    """
    from analyst_agent.core.dialect_caps import DIALECT_CAPABILITIES
    
    return {
        "supported_dialects": [d.value for d in SupportedDialect],
        "capabilities": {
            dialect: {
                "functions": caps.get("examples", []),
                "features": {
                    "window_functions": caps.get("window_functions", False),
                    "cte": caps.get("cte", False),
                    "json_support": caps.get("json_support", False),
                    "ilike": caps.get("ilike", False)
                }
            }
            for dialect, caps in DIALECT_CAPABILITIES.items()
        }
    }


@router.get("/connectors")
async def list_available_connectors() -> Dict[str, Any]:
    """
    List all available data source connectors.
    
    Returns:
        Dictionary with available connector types
    """
    from analyst_agent.adapters.registry import list_available_connectors
    
    return {
        "available_connectors": list_available_connectors(),
        "total_count": len(list_available_connectors())
    }
