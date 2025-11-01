"""
LangGraph workflow for the analysis engine.

Defines the complete analysis workflow with conditional routing between nodes
based on execution results and quality thresholds.
"""

from typing import Dict, Any, Literal, Optional
import structlog
from langgraph.graph import StateGraph, END
from analyst_agent.settings import settings

from .state import AnalystState, has_budget
from .nodes import (
    plan,
    profile,
    mvq,
    diagnose,
    refine,
    transform,
    produce,
    validate,
    present
)

logger = structlog.get_logger(__name__)


def need_diagnostics(state: AnalystState) -> Literal["diagnose", "transform"]:
    """
    Determine if diagnostics are needed after MVQ execution.
    
    Args:
        state: Current analysis state
        
    Returns:
        Next node to execute
    """
    rs = state.get("rs", {})
    
    # Need diagnostics if:
    # 1. Query failed
    # 2. Query returned no data
    # 3. Previous attempts had weird results
    rs_failed = not rs.get("ok", False)
    rs_empty = rs.get("row_count", 0) == 0
    
    # Check history for patterns that indicate we need diagnostics
    history = state.get("history", [])
    if history:
        latest = history[-1]
        weird_result = latest.get("flag_weird", False)
    else:
        weird_result = False
    
    needs_diag = rs_failed or rs_empty or weird_result
    
    logger.debug(
        "Diagnostics decision",
        job_id=state.get("job_id"),
        rs_failed=rs_failed,
        rs_empty=rs_empty,
        weird_result=weird_result,
        needs_diagnostics=needs_diag
    )
    
    return "diagnose" if needs_diag else "transform"


def should_continue_iteration(state: AnalystState) -> Literal["diagnose", "present"]:
    """
    Determine if we should continue iterating or present final results.
    
    Args:
        state: Current analysis state
        
    Returns:
        Next node to execute
    """
    quality = state.get("quality", {})
    
    # Get quality metrics
    quality_score = quality.get("score", 0.0)
    quality_passed = quality.get("passed", False)
    plateau = quality.get("plateau", False)
    
    # Check budget
    budget_ok = has_budget(state)
    
    # Check attempt count
    max_attempts = state.get("spec", {}).get("budget", {}).get("queries", 30) // 5  # Use ~20% of query budget for attempts
    attempt_count = state.get("attempt", 0)
    
    # Continue iterating if:
    # 1. Quality is below threshold AND
    # 2. We haven't plateaued AND
    # 3. We have budget AND
    # 4. We haven't exceeded max attempts
    should_continue = (
        quality_score < 0.85 and
        not plateau and
        budget_ok and
        attempt_count < max_attempts
    )
    
    logger.info(
        "Iteration decision",
        job_id=state.get("job_id"),
        quality_score=quality_score,
        quality_passed=quality_passed,
        plateau=plateau,
        budget_ok=budget_ok,
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        should_continue=should_continue
    )
    
    return "diagnose" if should_continue else "present"


def next_after_refine(state: AnalystState) -> Literal["diagnose", "transform"]:
    """
    Decide the next step after a refine attempt.
    
    Returns:
        "transform" if refine produced a successful result,
        otherwise "diagnose" to re-run troubleshooting with the new error.
    """
    rs = state.get("rs", {})
    ok = rs.get("ok", False)
    error = rs.get("error")
    
    logger.debug(
        "Refine routing decision",
        job_id=state.get("job_id"),
        succeeded=ok,
        error=error
    )
    
    return "transform" if ok else "diagnose"


def create_analysis_graph() -> StateGraph:
    """
    Create the complete analysis workflow graph.
    
    Returns:
        Compiled LangGraph StateGraph
    """
    logger.info("Creating analysis workflow graph")
    
    # Create the graph
    graph = StateGraph(AnalystState)
    
    # Add all nodes
    graph.add_node("plan", plan)
    graph.add_node("profile", profile)
    graph.add_node("mvq", mvq)
    graph.add_node("diagnose", diagnose)
    graph.add_node("refine", refine)
    graph.add_node("transform", transform)
    graph.add_node("produce", produce)
    graph.add_node("validate", validate)
    graph.add_node("present", present)
    
    # Set entry point
    graph.set_entry_point("plan")
    
    # Define the main flow
    graph.add_edge("plan", "profile")
    graph.add_edge("profile", "mvq")
    
    # Conditional: MVQ -> diagnostics or transform
    graph.add_conditional_edges(
        "mvq",
        need_diagnostics,
        {
            "diagnose": "diagnose",
            "transform": "transform"
        }
    )
    
    # Diagnostics leads to refinement
    graph.add_edge("diagnose", "refine")
    
    # Route after refinement based on success/failure
    graph.add_conditional_edges(
        "refine",
        next_after_refine,
        {
            "transform": "transform",
            "diagnose": "diagnose"
        }
    )
    
    # Transform -> produce -> validate
    graph.add_edge("transform", "produce")
    graph.add_edge("produce", "validate")
    
    # Conditional: validate -> continue iteration or present
    graph.add_conditional_edges(
        "validate",
        should_continue_iteration,
        {
            "diagnose": "diagnose",  # Re-enter at diagnostics for escalation
            "present": "present"
        }
    )
    
    # Present is the final node
    graph.add_edge("present", END)
    
    logger.info("Analysis workflow graph created successfully")
    
    return graph


def compile_analysis_graph() -> Any:
    """
    Create and compile the analysis workflow graph.
    
    Returns:
        Compiled graph ready for execution
    """
    graph = create_analysis_graph()
    compiled = graph.compile()
    
    logger.info("Analysis workflow graph compiled successfully")
    
    return compiled


# Create a global instance for easy import
analysis_graph = None


def get_analysis_graph():
    """
    Get the compiled analysis graph (lazy initialization).
    
    Returns:
        Compiled analysis graph
    """
    global analysis_graph
    
    if analysis_graph is None:
        analysis_graph = compile_analysis_graph()
    
    return analysis_graph


def run_analysis(
    job_id: str,
    spec: Dict[str, Any],
    ctx: Dict[str, Any],
    rls_context: Optional[Dict[str, Any]] = None
) -> AnalystState:
    """
    Run a complete analysis workflow.
    
    Args:
        job_id: Unique job identifier
        spec: Query specification
        ctx: Execution context (connector, etc.)
        rls_context: Optional RLS auth payload threaded through execution
        
    Returns:
        Final analysis state
    """
    from .state import create_initial_state
    
    logger.info("Starting analysis workflow", job_id=job_id)
    
    # Create initial state
    initial_state = create_initial_state(job_id, spec, ctx, rls_context)
    
    # Get compiled graph
    graph = get_analysis_graph()
    
    try:
        # Execute the workflow
        # Apply recursion limit via invoke config (per LangGraph docs)
        final_state = graph.invoke(
            initial_state,
            config={"recursion_limit": settings.graph_recursion_limit},
        )
        
        logger.info(
            "Analysis workflow completed",
            job_id=job_id,
            quality_score=final_state.get("quality", {}).get("score", 0),
            total_attempts=final_state.get("attempt", 0),
            has_answer=bool(final_state.get("answer"))
        )
        
        return final_state
        
    except Exception as e:
        logger.error("Analysis workflow failed", job_id=job_id, error=str(e))
        
        # Return failed state
        initial_state["answer"] = f"Analysis workflow failed: {str(e)}"
        initial_state["quality"] = {
            "passed": False,
            "score": 0.0,
            "gates": {},
            "notes": [f"Workflow error: {str(e)}"],
            "plateau": False
        }
        
        return initial_state


async def run_analysis_async(
    job_id: str,
    spec: Dict[str, Any],
    ctx: Dict[str, Any],
    rls_context: Optional[Dict[str, Any]] = None
) -> AnalystState:
    """
    Run a complete analysis workflow asynchronously.
    
    Args:
        job_id: Unique job identifier
        spec: Query specification
        ctx: Execution context (connector, etc.)
        rls_context: Optional RLS auth payload threaded through execution
        
    Returns:
        Final analysis state
    """
    from .state import create_initial_state
    
    logger.info("Starting async analysis workflow", job_id=job_id)
    
    # Create initial state
    initial_state = create_initial_state(job_id, spec, ctx, rls_context)
    
    # Get compiled graph
    graph = get_analysis_graph()
    
    try:
        # Execute the workflow asynchronously
        # Apply recursion limit via invoke config (per LangGraph docs)
        final_state = await graph.ainvoke(
            initial_state,
            config={"recursion_limit": settings.graph_recursion_limit},
        )
        
        logger.info(
            "Async analysis workflow completed",
            job_id=job_id,
            quality_score=final_state.get("quality", {}).get("score", 0),
            total_attempts=final_state.get("attempt", 0),
            has_answer=bool(final_state.get("answer"))
        )
        
        return final_state
        
    except Exception as e:
        logger.error("Async analysis workflow failed", job_id=job_id, error=str(e))
        
        # Return failed state
        initial_state["answer"] = f"Analysis workflow failed: {str(e)}"
        initial_state["quality"] = {
            "passed": False,
            "score": 0.0,
            "gates": {},
            "notes": [f"Workflow error: {str(e)}"],
            "plateau": False
        }
        
        return initial_state 
