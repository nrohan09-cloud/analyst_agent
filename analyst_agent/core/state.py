"""
State management for the LangGraph analysis workflow.

Defines the state structure that flows through the analysis nodes,
tracking query specification, execution context, results, and metadata.
"""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime


class AnalystState(TypedDict, total=False):
    """
    State object that flows through the LangGraph analysis workflow.
    
    This state tracks the complete analysis lifecycle from initial query
    specification through final results and quality assessment.
    """
    
    # Core specification and context
    spec: Dict[str, Any]                    # Materialized QuerySpec
    ctx: Dict[str, Any]                     # Execution context (connector, schema, etc.)
    
    # Data and results
    rs: Dict[str, Any]                      # Raw SQL results and metadata
    shaped: Dict[str, Any]                  # Transformed/shaped data frames
    artifacts: List[Dict[str, Any]]         # Generated artifacts (tables, charts, etc.)
    
    # Quality and validation
    quality: Dict[str, Any]                 # Quality assessment results
    validation_results: List[Dict[str, Any]]   # Individual validation checks
    
    # Execution tracking
    history: List[Dict[str, Any]]           # Execution history and step results
    attempt: int                            # Current attempt number
    budget_remaining: Dict[str, int]        # Remaining budget (queries, time)
    
    # Diagnostics and debugging
    diagnostics: List[Dict[str, Any]]       # Diagnostic query results
    errors: List[Dict[str, Any]]            # Error history
    
    # Final outputs
    answer: Optional[str]                   # Natural language answer
    execution_steps: List[Dict[str, Any]]   # Detailed execution trace
    lineage: Dict[str, Any]                 # Data lineage information
    
    # Metadata
    job_id: str                             # Unique job identifier
    created_at: datetime                    # Creation timestamp
    updated_at: datetime                    # Last update timestamp


def create_initial_state(
    job_id: str,
    spec: Dict[str, Any],
    ctx: Dict[str, Any]
) -> AnalystState:
    """
    Create an initial state object for a new analysis job.
    
    Args:
        job_id: Unique job identifier
        spec: Query specification dictionary
        ctx: Execution context dictionary
        
    Returns:
        Initialized AnalystState
    """
    now = datetime.utcnow()
    
    return AnalystState(
        job_id=job_id,
        spec=spec,
        ctx=ctx,
        rs={},
        shaped={},
        artifacts=[],
        quality={},
        validation_results=[],
        history=[],
        attempt=0,
        budget_remaining=spec.get("budget", {"queries": 30, "seconds": 90}).copy(),
        diagnostics=[],
        errors=[],
        answer=None,
        execution_steps=[],
        lineage={},
        created_at=now,
        updated_at=now,
    )


def update_state_timestamp(state: AnalystState) -> AnalystState:
    """Update the state timestamp."""
    state["updated_at"] = datetime.utcnow()
    return state


def add_execution_step(
    state: AnalystState,
    step_name: str,
    status: str,
    duration_ms: Optional[float] = None,
    sql: Optional[str] = None,
    row_count: Optional[int] = None,
    error: Optional[str] = None,
    **metadata
) -> AnalystState:
    """
    Add an execution step to the state.
    
    Args:
        state: Current state
        step_name: Name of the execution step
        status: Step status (running, completed, failed)
        duration_ms: Step duration in milliseconds
        sql: SQL executed in this step
        row_count: Number of rows processed
        error: Error message if step failed
        **metadata: Additional step metadata
        
    Returns:
        Updated state
    """
    step = {
        "step_name": step_name,
        "status": status,
        "timestamp": datetime.utcnow(),
        "duration_ms": duration_ms,
        "sql": sql,
        "row_count": row_count,
        "error": error,
        "metadata": metadata,
    }
    
    if "execution_steps" not in state:
        state["execution_steps"] = []
    
    state["execution_steps"].append(step)
    
    return update_state_timestamp(state)


def consume_budget(
    state: AnalystState,
    queries: int = 0,
    seconds: float = 0
) -> AnalystState:
    """
    Consume budget resources from the state.
    
    Args:
        state: Current state
        queries: Number of queries to consume
        seconds: Number of seconds to consume
        
    Returns:
        Updated state
    """
    if "budget_remaining" not in state:
        state["budget_remaining"] = {"queries": 30, "seconds": 90}
    
    state["budget_remaining"]["queries"] = max(
        0, 
        state["budget_remaining"]["queries"] - queries
    )
    state["budget_remaining"]["seconds"] = max(
        0,
        state["budget_remaining"]["seconds"] - int(seconds)
    )
    
    return update_state_timestamp(state)


def has_budget(state: AnalystState) -> bool:
    """
    Check if the state has remaining budget.
    
    Args:
        state: Current state
        
    Returns:
        True if budget remains
    """
    budget = state.get("budget_remaining", {"queries": 0, "seconds": 0})
    return budget.get("queries", 0) > 0 and budget.get("seconds", 0) > 0


def get_last_sql(state: AnalystState) -> Optional[str]:
    """
    Get the last SQL query from the execution history.
    
    Args:
        state: Current state
        
    Returns:
        Last SQL query or None
    """
    history = state.get("history", [])
    if not history:
        return None
    
    # Look for SQL in reverse chronological order
    for entry in reversed(history):
        if entry.get("sql"):
            return entry["sql"]
    
    return None


def get_last_error(state: AnalystState) -> Optional[str]:
    """
    Get the last error from the execution history.
    
    Args:
        state: Current state
        
    Returns:
        Last error message or None
    """
    errors = state.get("errors", [])
    if not errors:
        return None
    
    return errors[-1].get("error")


def add_artifact(
    state: AnalystState,
    artifact_id: str,
    kind: str,
    title: str,
    content: Optional[Dict[str, Any]] = None,
    file_path: Optional[str] = None,
    **meta
) -> AnalystState:
    """
    Add an artifact to the state.
    
    Args:
        state: Current state
        artifact_id: Unique artifact identifier
        kind: Artifact type (table, chart, log, sql)
        title: Human-readable title
        content: Artifact content
        file_path: Path to artifact file
        **meta: Additional metadata
        
    Returns:
        Updated state
    """
    artifact = {
        "id": artifact_id,
        "kind": kind,
        "title": title,
        "content": content,
        "file_path": file_path,
        "meta": meta,
        "created_at": datetime.utcnow(),
    }
    
    if "artifacts" not in state:
        state["artifacts"] = []
    
    state["artifacts"].append(artifact)
    
    return update_state_timestamp(state) 