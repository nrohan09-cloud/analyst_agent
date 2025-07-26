"""
Analysis endpoints for processing data analysis requests.
"""

from datetime import datetime
import uuid
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, status
import structlog

from analyst_agent.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    JobStatusResponse,
    AnalysisResult,
    JobStatus,
    ErrorResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter()

# In-memory job storage (TODO: Replace with persistent storage)
job_store: Dict[str, Dict[str, Any]] = {}


async def process_analysis_job(job_id: str, request: AnalysisRequest) -> None:
    """
    Process an analysis job in the background using the LangGraph agent.
    
    Args:
        job_id: Unique job identifier
        request: Analysis request data
    """
    from analyst_agent.agents.analysis_agent import analysis_agent
    
    try:
        # Update job status to running
        job_store[job_id]["status"] = JobStatus.RUNNING
        job_store[job_id]["current_step"] = "Initializing analysis"
        
        logger.info("Starting analysis job with LangGraph agent", job_id=job_id, question=request.question)
        
        # Execute the analysis using the LangGraph agent
        result = await analysis_agent.execute_analysis(job_id, request)
        
        # Update job with results
        job_store[job_id]["status"] = result.status
        job_store[job_id]["result"] = result
        job_store[job_id]["progress"] = 1.0
        job_store[job_id]["current_step"] = result.summary
        
        if result.status == JobStatus.FAILED:
            job_store[job_id]["error"] = result.error_message
            logger.error("Analysis job failed", job_id=job_id, error=result.error_message)
        else:
            logger.info("Analysis job completed successfully", job_id=job_id, insights_count=len(result.insights))
        
    except Exception as e:
        # Handle job failure
        job_store[job_id]["status"] = JobStatus.FAILED
        job_store[job_id]["error"] = str(e)
        job_store[job_id]["current_step"] = "Failed"
        
        logger.error("Analysis job failed", job_id=job_id, error=str(e), exc_info=True)


@router.post("/ask", response_model=AnalysisResponse)
async def ask_question(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
) -> AnalysisResponse:
    """
    Submit a natural language question for data analysis.
    
    Args:
        request: Analysis request containing question and data source
        background_tasks: FastAPI background tasks
        
    Returns:
        AnalysisResponse: Job information and initial response
    """
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    logger.info(
        "Received analysis request",
        job_id=job_id,
        question=request.question,
        data_source_type=request.data_source.type
    )
    
    # Initialize job in store
    job_store[job_id] = {
        "status": JobStatus.PENDING,
        "request": request,
        "created_at": datetime.utcnow(),
        "progress": 0.0,
        "current_step": "Queued",
        "result": None,
        "error": None
    }
    
    # Start background processing
    background_tasks.add_task(process_analysis_job, job_id, request)
    
    return AnalysisResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Analysis request received and queued for processing"
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Get the status of an analysis job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        JobStatusResponse: Job status and results
    """
    if job_id not in job_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job_data = job_store[job_id]
    
    return JobStatusResponse(
        job_id=job_id,
        status=job_data["status"],
        progress=job_data.get("progress"),
        current_step=job_data.get("current_step"),
        result=job_data.get("result")
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str) -> Dict[str, str]:
    """
    Cancel a running analysis job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        dict: Cancellation confirmation
    """
    if job_id not in job_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job_data = job_store[job_id]
    
    if job_data["status"] in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job_data['status']}"
        )
    
    # TODO: Implement actual job cancellation logic
    job_store[job_id]["status"] = JobStatus.CANCELLED
    job_store[job_id]["current_step"] = "Cancelled"
    
    logger.info("Job cancelled", job_id=job_id)
    
    return {"message": f"Job {job_id} cancelled successfully"} 