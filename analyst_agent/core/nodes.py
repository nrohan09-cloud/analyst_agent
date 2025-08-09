"""
Core analysis nodes for the LangGraph workflow.

These nodes implement the analysis lifecycle: plan → profile → mvq → diagnose → 
refine → produce → transform → validate → present
"""

import time
import uuid
from typing import Dict, Any
import structlog

from .state import (
    AnalystState, 
    add_execution_step, 
    has_budget,
    get_last_sql,
    get_last_error,
    add_artifact,
    update_state_timestamp
)
from .sql_executor import (
    try_execute_sql,
    llm_generate_sql,
    llm_generate_diagnostics,
    generate_schema_card
)
from .dialect_caps import (
    build_sql_prompt,
    build_diagnostic_prompt,
    build_refinement_prompt
)

logger = structlog.get_logger(__name__)


def plan(state: AnalystState) -> AnalystState:
    """
    Plan the analysis approach based on the question.
    
    This node analyzes the question and sets up the analysis context,
    including identifying key tables and metrics needed.
    """
    logger.info("Starting analysis planning", job_id=state["job_id"])
    
    add_execution_step(
        state,
        step_name="plan",
        status="running"
    )
    
    try:
        question = state["spec"]["question"]
        dialect = state["ctx"]["dialect"]
        
        # Store planning context
        state["ctx"]["plan"] = {
            "question": question,
            "dialect": dialect,
            "approach": "direct_sql_generation",
            "planned_at": time.time()
        }
        
        add_execution_step(
            state,
            step_name="plan",
            status="completed",
            metadata={
                "question": question,
                "dialect": dialect
            }
        )
        
        logger.info("Analysis planning completed", job_id=state["job_id"])
        
    except Exception as e:
        add_execution_step(
            state,
            step_name="plan",
            status="failed",
            error=str(e)
        )
        logger.error("Planning failed", job_id=state["job_id"], error=str(e))
    
    return update_state_timestamp(state)


def profile(state: AnalystState) -> AnalystState:
    """
    Profile the database schema and generate a schema card.
    
    This node discovers available tables, columns, and sample data
    to inform SQL generation.
    """
    logger.info("Starting database profiling", job_id=state["job_id"])
    
    add_execution_step(
        state,
        step_name="profile",
        status="running"
    )
    
    try:
        # Generate schema card
        schema_card = generate_schema_card(state)
        state["ctx"]["schema_card"] = schema_card
        
        # Log profiling results
        table_count = len(schema_card.get("tables", {}))
        
        add_execution_step(
            state,
            step_name="profile",
            status="completed",
            metadata={
                "tables_found": table_count,
                "has_sample_data": any(
                    table.get("sample_rows") 
                    for table in schema_card.get("tables", {}).values()
                )
            }
        )
        
        logger.info(
            "Database profiling completed",
            job_id=state["job_id"],
            tables=table_count
        )
        
    except Exception as e:
        add_execution_step(
            state,
            step_name="profile", 
            status="failed",
            error=str(e)
        )
        logger.error("Profiling failed", job_id=state["job_id"], error=str(e))
        
        # Set empty schema card as fallback
        state["ctx"]["schema_card"] = {"tables": {}, "error": str(e)}
    
    return update_state_timestamp(state)


def mvq(state: AnalystState) -> AnalystState:
    """
    Generate and execute Minimal Viable Query (MVQ).
    
    This node generates the initial SQL query to answer the question
    using the discovered schema information.
    """
    logger.info("Generating minimal viable query", job_id=state["job_id"])
    
    add_execution_step(
        state,
        step_name="mvq",
        status="running"
    )
    
    try:
        if not has_budget(state):
            raise Exception("Budget exhausted")
        
        # Build SQL generation prompt
        dialect = state["ctx"]["dialect"]
        question = state["spec"]["question"]
        schema_card = state["ctx"].get("schema_card", {})
        
        prompt = build_sql_prompt(
            dialect=dialect,
            question=question,
            schema_card=schema_card
        )
        
        # Generate SQL using LLM
        generation = llm_generate_sql(prompt)
        sql = generation["sql"]
        notes = generation.get("notes", "")
        
        # Execute the generated SQL
        result = try_execute_sql(state, sql)
        state["rs"] = result
        
        # Track in history
        if "history" not in state:
            state["history"] = []
        
        state["history"].append({
            "stage": "mvq",
            "sql": sql,
            "notes": notes,
            "ok": result["ok"],
            "row_count": result.get("row_count", 0),
            "error": result.get("error"),
            "timestamp": time.time()
        })
        
        add_execution_step(
            state,
            step_name="mvq",
            status="completed" if result["ok"] else "failed",
            sql=sql,
            row_count=result.get("row_count", 0),
            error=result.get("error")
        )
        
        if result["ok"]:
            logger.info(
                "MVQ executed successfully",
                job_id=state["job_id"],
                rows=result.get("row_count", 0)
            )
        else:
            logger.warning(
                "MVQ execution failed",
                job_id=state["job_id"],
                error=result.get("error", "Unknown error")
            )
        
    except Exception as e:
        add_execution_step(
            state,
            step_name="mvq",
            status="failed",
            error=str(e)
        )
        logger.error("MVQ generation failed", job_id=state["job_id"], error=str(e))
        state["rs"] = {"ok": False, "error": str(e)}
    
    state["attempt"] = state.get("attempt", 0) + 1
    return update_state_timestamp(state)


def diagnose(state: AnalystState) -> AnalystState:
    """
    Run diagnostic queries to understand why the main query failed or returned no data.
    
    This node generates and executes diagnostic SQL to debug issues.
    """
    logger.info("Running diagnostics", job_id=state["job_id"])
    
    add_execution_step(
        state,
        step_name="diagnose",
        status="running"
    )
    
    try:
        if not has_budget(state):
            logger.warning("Skipping diagnostics - budget exhausted")
            return state
        
        # Get last error and SQL
        last_sql = get_last_sql(state) or "No SQL available"
        last_error = get_last_error(state) or state["rs"].get("error", "No data returned")
        
        # Build diagnostic prompt
        dialect = state["ctx"]["dialect"]
        question = state["spec"]["question"]
        schema_card = state["ctx"].get("schema_card", {})
        
        prompt = build_diagnostic_prompt(
            dialect=dialect,
            question=question,
            last_sql=last_sql,
            db_error=last_error,
            schema_card=schema_card
        )
        
        # Generate diagnostic queries
        diag_plan = llm_generate_diagnostics(prompt)
        diagnostic_sqls = diag_plan.get("diagnostic_sqls", [])
        
        # Execute diagnostic queries
        diagnostics = []
        for sql in diagnostic_sqls[:5]:  # Limit to 5 diagnostics
            if not has_budget(state):
                break
            result = try_execute_sql(state, sql)
            diagnostics.append(result)
        
        state["diagnostics"] = diagnostics
        
        # Count successful diagnostics
        successful = sum(1 for d in diagnostics if d.get("ok"))
        
        add_execution_step(
            state,
            step_name="diagnose",
            status="completed",
            metadata={
                "diagnostic_queries": len(diagnostic_sqls),
                "successful_diagnostics": successful,
                "purpose": diag_plan.get("purpose", "")
            }
        )
        
        logger.info(
            "Diagnostics completed",
            job_id=state["job_id"],
            successful=successful,
            total=len(diagnostics)
        )
        
    except Exception as e:
        add_execution_step(
            state,
            step_name="diagnose",
            status="failed",
            error=str(e)
        )
        logger.error("Diagnostics failed", job_id=state["job_id"], error=str(e))
        state["diagnostics"] = []
    
    return update_state_timestamp(state)


def refine(state: AnalystState) -> AnalystState:
    """
    Refine the SQL query based on diagnostic results.
    
    This node uses diagnostic information to fix the SQL query
    and try again with corrections.
    """
    logger.info("Refining query", job_id=state["job_id"])
    
    add_execution_step(
        state,
        step_name="refine",
        status="running"
    )
    
    try:
        if not has_budget(state):
            raise Exception("Budget exhausted")
        
        # Get refinement context
        dialect = state["ctx"]["dialect"]
        question = state["spec"]["question"]
        failed_sql = get_last_sql(state) or ""
        db_error = get_last_error(state) or ""
        diagnostics = state.get("diagnostics", [])
        
        # Build refinement prompt
        prompt = build_refinement_prompt(
            dialect=dialect,
            question=question,
            failed_sql=failed_sql,
            db_error=db_error,
            diagnostics=diagnostics
        )
        
        # Generate refined SQL
        generation = llm_generate_sql(prompt)
        sql = generation["sql"]
        changes = generation.get("what_changed", "Unknown changes")
        
        # Execute refined SQL
        result = try_execute_sql(state, sql)
        state["rs"] = result
        
        # Track in history
        state["history"].append({
            "stage": "refine",
            "sql": sql,
            "changes": changes,
            "ok": result["ok"],
            "row_count": result.get("row_count", 0),
            "error": result.get("error"),
            "timestamp": time.time()
        })
        
        add_execution_step(
            state,
            step_name="refine",
            status="completed" if result["ok"] else "failed",
            sql=sql,
            row_count=result.get("row_count", 0),
            error=result.get("error"),
            metadata={"changes": changes}
        )
        
        if result["ok"]:
            logger.info(
                "Query refinement successful",
                job_id=state["job_id"],
                rows=result.get("row_count", 0)
            )
        else:
            logger.warning(
                "Refined query still failed",
                job_id=state["job_id"],
                error=result.get("error", "Unknown error")
            )
        
    except Exception as e:
        add_execution_step(
            state,
            step_name="refine",
            status="failed",
            error=str(e)
        )
        logger.error("Query refinement failed", job_id=state["job_id"], error=str(e))
        state["rs"] = {"ok": False, "error": str(e)}
    
    state["attempt"] = state.get("attempt", 0) + 1
    return update_state_timestamp(state)


def transform(state: AnalystState) -> AnalystState:
    """
    Transform and shape the raw query results.
    
    This node performs any necessary data transformations
    on the successful query results.
    """
    logger.info("Transforming results", job_id=state["job_id"])
    
    add_execution_step(
        state,
        step_name="transform",
        status="running"
    )
    
    try:
        if not state["rs"].get("ok"):
            logger.warning("Skipping transform - no successful results")
            return state
        
        # Get the result table
        table = state["rs"]["table"]
        
        if table.num_rows == 0:
            logger.warning("No rows to transform")
            state["shaped"] = {"empty": True}
            return state
        
        # Convert to pandas for easier manipulation
        df = table.to_pandas()
        
        # Basic transformations (can be expanded)
        shaped_data = {
            "dataframe": df,
            "summary": {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "dtypes": df.dtypes.to_dict()
            },
            "sample": df.head(10).to_dict('records') if len(df) > 0 else []
        }
        
        state["shaped"] = shaped_data
        
        add_execution_step(
            state,
            step_name="transform",
            status="completed",
            metadata={
                "rows": len(df),
                "columns": len(df.columns)
            }
        )
        
        logger.info(
            "Data transformation completed",
            job_id=state["job_id"],
            rows=len(df),
            columns=len(df.columns)
        )
        
    except Exception as e:
        add_execution_step(
            state,
            step_name="transform",
            status="failed",
            error=str(e)
        )
        logger.error("Data transformation failed", job_id=state["job_id"], error=str(e))
        state["shaped"] = {"error": str(e)}
    
    return update_state_timestamp(state)


def produce(state: AnalystState) -> AnalystState:
    """
    Produce final data artifacts from the transformed results.
    
    This node creates the final data artifacts (tables, etc.)
    that will be returned to the user.
    """
    logger.info("Producing artifacts", job_id=state["job_id"])
    
    add_execution_step(
        state,
        step_name="produce",
        status="running"
    )
    
    try:
        shaped_data = state.get("shaped", {})
        
        if shaped_data.get("empty") or shaped_data.get("error"):
            logger.warning("No data to produce artifacts from")
            return state
        
        # Create table artifact
        df = shaped_data.get("dataframe")
        if df is not None and len(df) > 0:
            artifact_id = f"table_{uuid.uuid4().hex[:8]}"
            
            # Create table artifact
            add_artifact(
                state,
                artifact_id=artifact_id,
                kind="table",
                title="Analysis Results",
                content={
                    "data": df.to_dict('records'),
                    "columns": list(df.columns),
                    "summary": shaped_data.get("summary", {})
                }
            )
            
            logger.info(
                "Created table artifact",
                job_id=state["job_id"],
                artifact_id=artifact_id,
                rows=len(df)
            )
        
        # Create SQL artifact from history
        if state.get("history"):
            successful_queries = [
                h for h in state["history"] 
                if h.get("ok") and h.get("sql")
            ]
            
            if successful_queries:
                latest_query = successful_queries[-1]
                sql_artifact_id = f"sql_{uuid.uuid4().hex[:8]}"
                
                add_artifact(
                    state,
                    artifact_id=sql_artifact_id,
                    kind="sql",
                    title="Final SQL Query",
                    content={
                        "sql": latest_query["sql"],
                        "notes": latest_query.get("notes", ""),
                        "row_count": latest_query.get("row_count", 0)
                    }
                )
        
        add_execution_step(
            state,
            step_name="produce",
            status="completed",
            metadata={
                "artifacts_created": len(state.get("artifacts", []))
            }
        )
        
        logger.info(
            "Artifact production completed",
            job_id=state["job_id"],
            artifacts=len(state.get("artifacts", []))
        )
        
    except Exception as e:
        add_execution_step(
            state,
            step_name="produce",
            status="failed",
            error=str(e)
        )
        logger.error("Artifact production failed", job_id=state["job_id"], error=str(e))
    
    return update_state_timestamp(state)


def validate(state: AnalystState) -> AnalystState:
    """
    Validate the analysis results and compute quality score.
    
    This node performs quality checks on the results and
    determines if they meet the required standards.
    """
    logger.info("Validating results", job_id=state["job_id"])
    
    add_execution_step(
        state,
        step_name="validate",
        status="running"
    )
    
    try:
        # Basic quality checks
        has_data = state["rs"].get("ok", False) and state["rs"].get("row_count", 0) > 0
        has_artifacts = len(state.get("artifacts", [])) > 0
        budget_ok = has_budget(state)
        
        # Calculate quality score
        score = 0.0
        gates = {}
        
        if has_data:
            score += 0.6
            gates["has_data"] = True
        else:
            gates["has_data"] = False
        
        if has_artifacts:
            score += 0.3
            gates["has_artifacts"] = True
        else:
            gates["has_artifacts"] = False
        
        if state.get("attempt", 0) <= 3:
            score += 0.1
            gates["reasonable_attempts"] = True
        else:
            gates["reasonable_attempts"] = False
        
        # Check for plateau (no improvement over attempts)
        plateau = False
        if state.get("attempt", 0) >= 3:
            recent_scores = [h.get("score", 0) for h in state.get("history", [])[-2:]]
            if recent_scores and all(s <= score + 0.01 for s in recent_scores):
                plateau = True
        
        quality_report = {
            "passed": score >= 0.7,
            "score": score,
            "gates": gates,
            "notes": [],
            "plateau": plateau
        }
        
        if not has_data:
            quality_report["notes"].append("No data returned from query")
        if not has_artifacts:
            quality_report["notes"].append("No artifacts generated")
        if not budget_ok:
            quality_report["notes"].append("Budget exhausted")
        
        state["quality"] = quality_report
        
        add_execution_step(
            state,
            step_name="validate",
            status="completed",
            metadata={
                "quality_score": score,
                "quality_passed": quality_report["passed"],
                "plateau": plateau
            }
        )
        
        logger.info(
            "Validation completed",
            job_id=state["job_id"],
            score=score,
            passed=quality_report["passed"]
        )
        
    except Exception as e:
        add_execution_step(
            state,
            step_name="validate",
            status="failed",
            error=str(e)
        )
        logger.error("Validation failed", job_id=state["job_id"], error=str(e))
        
        # Set minimal quality report
        state["quality"] = {
            "passed": False,
            "score": 0.0,
            "gates": {},
            "notes": [f"Validation error: {str(e)}"],
            "plateau": False
        }
    
    return update_state_timestamp(state)


def present(state: AnalystState) -> AnalystState:
    """
    Generate the final presentation and natural language answer.
    
    This node creates the final answer and prepares all outputs
    for return to the user.
    """
    logger.info("Presenting results", job_id=state["job_id"])
    
    add_execution_step(
        state,
        step_name="present",
        status="running"
    )
    
    try:
        # Generate natural language answer
        question = state["spec"]["question"]
        has_data = state["rs"].get("ok", False) and state["rs"].get("row_count", 0) > 0
        
        if has_data:
            row_count = state["rs"].get("row_count", 0)
            shaped_data = state.get("shaped", {})
            
            if shaped_data and not shaped_data.get("error"):
                summary = shaped_data.get("summary", {})
                answer = f"Analysis completed successfully. Found {row_count} rows of data with {summary.get('columns', 0)} columns. The query returned relevant data for: {question}"
            else:
                answer = f"Analysis completed with {row_count} rows of data, but transformation failed."
        else:
            error = state["rs"].get("error", "Unknown error")
            answer = f"Analysis could not be completed. Error: {error}. Question was: {question}"
        
        state["answer"] = answer
        
        # Set completion timestamp
        state["completed_at"] = time.time()
        
        add_execution_step(
            state,
            step_name="present",
            status="completed",
            metadata={
                "answer_length": len(answer),
                "final_artifacts": len(state.get("artifacts", []))
            }
        )
        
        logger.info(
            "Presentation completed",
            job_id=state["job_id"],
            has_answer=bool(state.get("answer"))
        )
        
    except Exception as e:
        add_execution_step(
            state,
            step_name="present",
            status="failed",
            error=str(e)
        )
        logger.error("Presentation failed", job_id=state["job_id"], error=str(e))
        
        # Set fallback answer
        state["answer"] = f"Analysis encountered an error during presentation: {str(e)}"
    
    return update_state_timestamp(state) 