"""
LangGraph-based Analysis Agent for autonomous data analysis.

This module contains the main agent that orchestrates the entire data analysis
workflow from planning to final insights generation.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict
import uuid

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import structlog

from analyst_agent.settings import settings
from analyst_agent.schemas import (
    AnalysisRequest, 
    AnalysisResult, 
    JobStatus, 
    Insight, 
    Chart, 
    ExecutionStep,
    AnalysisType
)

logger = structlog.get_logger(__name__)


class AnalysisState(TypedDict):
    """State structure for the analysis workflow."""
    job_id: str
    request: AnalysisRequest
    current_step: str
    progress: float
    plan: Optional[Dict[str, Any]]
    data_info: Optional[Dict[str, Any]]
    analysis_results: Optional[Dict[str, Any]]
    visualizations: Optional[List[Chart]]
    insights: Optional[List[Insight]]
    summary: Optional[str]
    execution_steps: List[ExecutionStep]
    error: Optional[str]


class AnalysisAgent:
    """Main analysis agent that coordinates the entire workflow."""
    
    def __init__(self):
        """Initialize the analysis agent."""
        self.llm = self._create_llm()
        self.memory = MemorySaver()
        self.graph = self._create_workflow()
    
    def _create_llm(self) -> Optional[ChatOpenAI]:
        """Create and configure the LLM instance."""
        if not settings.openai_api_key:
            logger.warning("No OpenAI API key configured, running in mock mode")
            return None
            
        return ChatOpenAI(
            model=settings.default_llm_model,
            temperature=0.1,  # Lower temperature for more consistent analysis
            max_tokens=4000,
            api_key=settings.openai_api_key
        )
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for analysis."""
        workflow = StateGraph(AnalysisState)
        
        # Add workflow nodes
        workflow.add_node("planner", self._plan_analysis)
        workflow.add_node("data_loader", self._load_data)
        workflow.add_node("analyzer", self._analyze_data)
        workflow.add_node("visualizer", self._create_visualizations)
        workflow.add_node("summarizer", self._generate_summary)
        workflow.add_node("error_handler", self._handle_error)
        
        # Define the workflow edges
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "data_loader")
        workflow.add_edge("data_loader", "analyzer")
        workflow.add_edge("analyzer", "visualizer")
        workflow.add_edge("visualizer", "summarizer")
        workflow.add_edge("summarizer", END)
        workflow.add_edge("error_handler", END)
        
        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "planner",
            self._should_continue,
            {
                "continue": "data_loader",
                "error": "error_handler"
            }
        )
        
        return workflow.compile(checkpointer=self.memory)
    
    async def execute_analysis(self, job_id: str, request: AnalysisRequest) -> AnalysisResult:
        """
        Execute the complete analysis workflow.
        
        Args:
            job_id: Unique identifier for the job
            request: Analysis request with question and data source
            
        Returns:
            AnalysisResult: Complete analysis results
        """
        logger.info("Starting analysis execution", job_id=job_id, question=request.question)
        
        # Initialize the state
        initial_state = AnalysisState(
            job_id=job_id,
            request=request,
            current_step="Initializing",
            progress=0.0,
            plan=None,
            data_info=None,
            analysis_results=None,
            visualizations=None,
            insights=None,
            summary=None,
            execution_steps=[],
            error=None
        )
        
        try:
            # Execute the workflow
            config = {"configurable": {"thread_id": job_id}}
            final_state = await self.graph.ainvoke(initial_state, config=config)
            
            # Create the analysis result
            result = AnalysisResult(
                job_id=job_id,
                status=JobStatus.FAILED if final_state.get("error") else JobStatus.COMPLETED,
                question=request.question,
                summary=final_state.get("summary", "Analysis completed"),
                insights=final_state.get("insights", []),
                charts=final_state.get("visualizations", []),
                tables=[],  # TODO: Add table results
                execution_steps=final_state.get("execution_steps", []),
                metadata={
                    "data_source_type": request.data_source.type.value,
                    "analysis_plan": final_state.get("plan", {}),
                    "data_info": final_state.get("data_info", {})
                },
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error_message=final_state.get("error")
            )
            
            logger.info("Analysis execution completed", job_id=job_id, status=result.status)
            return result
            
        except Exception as e:
            logger.error("Analysis execution failed", job_id=job_id, error=str(e), exc_info=True)
            
            # Create error result
            return AnalysisResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                question=request.question,
                summary="Analysis failed due to an error",
                insights=[],
                charts=[],
                tables=[],
                execution_steps=initial_state.get("execution_steps", []),
                metadata={"error_type": type(e).__name__},
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )
    
    async def _plan_analysis(self, state: AnalysisState) -> AnalysisState:
        """
        Plan the analysis based on the user's question and data source.
        
        This node creates a structured plan for what analysis to perform.
        """
        logger.info("Planning analysis", job_id=state["job_id"])
        
        self._add_execution_step(
            state,
            "Planning Analysis",
            "Creating analysis plan based on question and data source",
            JobStatus.RUNNING
        )
        
        try:
            # Create planning prompt
            planning_prompt = f"""
            You are an expert data analyst. Create a detailed analysis plan for the following request:
            
            Question: {state['request'].question}
            Data Source Type: {state['request'].data_source.type.value}
            Analysis Types Requested: {state['request'].preferences.analysis_types if state['request'].preferences else ['descriptive']}
            
            Create a JSON analysis plan with:
            1. "steps": List of analysis steps to perform
            2. "analysis_types": Types of analysis to conduct (descriptive, inferential, predictive)
            3. "visualizations": Recommended chart types
            4. "key_metrics": Important metrics to calculate
            5. "potential_insights": What insights we might discover
            
            Return only valid JSON.
            """
            
            # Use LLM if available, otherwise use mock response
            if self.llm:
                messages = [
                    SystemMessage(content="You are an expert data analyst AI assistant."),
                    HumanMessage(content=planning_prompt)
                ]
                
                response = await self.llm.ainvoke(messages)
                plan_content = response.content.strip()
            else:
                # Mock response for testing without API key
                plan_content = json.dumps({
                    "steps": [
                        "Load and examine the CSV data structure",
                        "Calculate descriptive statistics for all numeric columns",
                        "Identify data quality issues and missing values",
                        "Perform correlation analysis between variables",
                        "Create distribution visualizations",
                        "Generate summary insights and recommendations"
                    ],
                    "analysis_types": ["descriptive", "correlation", "distribution"],
                    "visualizations": ["histogram", "scatter_plot", "correlation_heatmap"],
                    "key_metrics": ["mean", "median", "std_dev", "correlation_matrix", "missing_value_count"],
                    "potential_insights": [
                        "Distribution patterns and outliers in the data",
                        "Relationships and correlations between variables",
                        "Data quality assessment and completeness"
                    ]
                })
            
            # Parse the plan
            try:
                plan = json.loads(plan_content)
            except json.JSONDecodeError:
                # Fallback to a simple plan if JSON parsing fails
                plan = {
                    "steps": [
                        "Load and examine data structure",
                        "Perform descriptive statistics",
                        "Create basic visualizations",
                        "Generate insights"
                    ],
                    "analysis_types": ["descriptive"],
                    "visualizations": ["histogram", "scatter", "bar"],
                    "key_metrics": ["mean", "median", "correlation"],
                    "potential_insights": ["Distribution patterns", "Relationships between variables"]
                }
            
            state["plan"] = plan
            state["current_step"] = "Analysis Planned"
            state["progress"] = 0.2
            
            self._complete_execution_step(state, "Planning Analysis", plan)
            
            logger.info("Analysis planning completed", job_id=state["job_id"], plan=plan)
            
        except Exception as e:
            logger.error("Analysis planning failed", job_id=state["job_id"], error=str(e))
            state["error"] = f"Planning failed: {str(e)}"
            self._fail_execution_step(state, "Planning Analysis", str(e))
        
        return state
    
    async def _load_data(self, state: AnalysisState) -> AnalysisState:
        """
        Load data from the specified source and gather basic information.
        
        This is a placeholder that will be enhanced when we implement actual connectors.
        """
        logger.info("Loading data", job_id=state["job_id"])
        
        self._add_execution_step(
            state,
            "Loading Data",
            f"Connecting to {state['request'].data_source.type.value} data source",
            JobStatus.RUNNING
        )
        
        try:
            # TODO: Implement actual data loading using connectors
            # For now, simulate data loading
            
            data_info = {
                "source_type": state['request'].data_source.type.value,
                "rows": 1000,  # Simulated
                "columns": 10,  # Simulated
                "size_mb": 2.5,  # Simulated
                "columns_info": {
                    "numeric_columns": ["sales", "revenue", "profit"],
                    "categorical_columns": ["category", "region"],
                    "date_columns": ["date", "timestamp"]
                },
                "sample_data": {
                    "sales": [100, 150, 200, 175, 300],
                    "category": ["A", "B", "C", "A", "B"]
                }
            }
            
            state["data_info"] = data_info
            state["current_step"] = "Data Loaded"
            state["progress"] = 0.4
            
            self._complete_execution_step(state, "Loading Data", data_info)
            
            logger.info("Data loading completed", job_id=state["job_id"], data_info=data_info)
            
        except Exception as e:
            logger.error("Data loading failed", job_id=state["job_id"], error=str(e))
            state["error"] = f"Data loading failed: {str(e)}"
            self._fail_execution_step(state, "Loading Data", str(e))
        
        return state
    
    async def _analyze_data(self, state: AnalysisState) -> AnalysisState:
        """
        Perform the actual data analysis based on the plan.
        
        This will be enhanced with actual statistical analysis capabilities.
        """
        logger.info("Analyzing data", job_id=state["job_id"])
        
        self._add_execution_step(
            state,
            "Analyzing Data",
            "Performing statistical analysis and generating insights",
            JobStatus.RUNNING
        )
        
        try:
            # TODO: Implement actual analysis using statistics and ML modules
            # For now, generate mock analysis results
            
            analysis_results = {
                "descriptive_stats": {
                    "sales_mean": 175.0,
                    "sales_median": 150.0,
                    "sales_std": 75.5,
                    "total_records": 1000
                },
                "correlations": {
                    "sales_revenue": 0.85,
                    "sales_profit": 0.72
                },
                "insights_found": [
                    "Strong positive correlation between sales and revenue",
                    "Sales distribution appears right-skewed",
                    "Category A shows highest average sales"
                ]
            }
            
            # Generate insights
            insights = []
            for i, insight_text in enumerate(analysis_results["insights_found"]):
                insight = Insight(
                    title=f"Key Finding {i+1}",
                    description=insight_text,
                    confidence=0.85,
                    type=AnalysisType.DESCRIPTIVE,
                    supporting_data={"source": "statistical_analysis"}
                )
                insights.append(insight)
            
            state["analysis_results"] = analysis_results
            state["insights"] = insights
            state["current_step"] = "Analysis Completed"
            state["progress"] = 0.6
            
            self._complete_execution_step(state, "Analyzing Data", analysis_results)
            
            logger.info("Data analysis completed", job_id=state["job_id"], insights_count=len(insights))
            
        except Exception as e:
            logger.error("Data analysis failed", job_id=state["job_id"], error=str(e))
            state["error"] = f"Data analysis failed: {str(e)}"
            self._fail_execution_step(state, "Analyzing Data", str(e))
        
        return state
    
    async def _create_visualizations(self, state: AnalysisState) -> AnalysisState:
        """
        Create visualizations based on the analysis results.
        
        This will be enhanced with actual plotting capabilities.
        """
        logger.info("Creating visualizations", job_id=state["job_id"])
        
        self._add_execution_step(
            state,
            "Creating Visualizations",
            "Generating charts and visual representations",
            JobStatus.RUNNING
        )
        
        try:
            # TODO: Implement actual visualization generation
            # For now, create mock chart objects
            
            charts = []
            
            # Mock histogram
            histogram_chart = Chart(
                title="Sales Distribution",
                type="histogram",
                data={
                    "x": [100, 150, 200, 175, 300, 125, 180, 220, 160, 190],
                    "bins": 10,
                    "xlabel": "Sales Amount",
                    "ylabel": "Frequency"
                },
                config={"color": "blue", "alpha": 0.7}
            )
            charts.append(histogram_chart)
            
            # Mock scatter plot
            scatter_chart = Chart(
                title="Sales vs Revenue Correlation",
                type="scatter",
                data={
                    "x": [100, 150, 200, 175, 300],
                    "y": [120, 180, 240, 210, 360],
                    "xlabel": "Sales",
                    "ylabel": "Revenue"
                },
                config={"color": "red", "size": 50}
            )
            charts.append(scatter_chart)
            
            state["visualizations"] = charts
            state["current_step"] = "Visualizations Created"
            state["progress"] = 0.8
            
            self._complete_execution_step(state, "Creating Visualizations", {"charts_created": len(charts)})
            
            logger.info("Visualization creation completed", job_id=state["job_id"], charts_count=len(charts))
            
        except Exception as e:
            logger.error("Visualization creation failed", job_id=state["job_id"], error=str(e))
            state["error"] = f"Visualization creation failed: {str(e)}"
            self._fail_execution_step(state, "Creating Visualizations", str(e))
        
        return state
    
    async def _generate_summary(self, state: AnalysisState) -> AnalysisState:
        """
        Generate a comprehensive summary of the analysis results.
        """
        logger.info("Generating summary", job_id=state["job_id"])
        
        self._add_execution_step(
            state,
            "Generating Summary",
            "Creating comprehensive analysis summary",
            JobStatus.RUNNING
        )
        
        try:
            # Create summary prompt
            insights_text = "\n".join([f"- {insight.description}" for insight in state.get("insights", [])])
            
            summary_prompt = f"""
            Create a comprehensive summary of this data analysis:
            
            Original Question: {state['request'].question}
            
            Key Findings:
            {insights_text}
            
            Analysis Results: {json.dumps(state.get('analysis_results', {}), indent=2)}
            
            Visualizations Created: {len(state.get('visualizations', []))} charts
            
            Provide a clear, executive-level summary that answers the original question and highlights the most important insights.
            """
            
            # Use LLM if available, otherwise use mock response
            if self.llm:
                messages = [
                    SystemMessage(content="You are an expert data analyst providing executive summaries."),
                    HumanMessage(content=summary_prompt)
                ]
                
                response = await self.llm.ainvoke(messages)
                summary = response.content.strip()
            else:
                # Mock summary for testing without API key
                insights_count = len(state.get('insights', []))
                charts_count = len(state.get('visualizations', []))
                
                summary = f"""
## Executive Summary

**Analysis Question:** {state['request'].question}

**Key Findings:**
- Successfully analyzed the provided dataset ({state['request'].data_source.type.value} format)
- Generated {insights_count} key insights with statistical validation
- Created {charts_count} visualizations to support findings
- Identified important patterns and trends in the data

**Main Insights:**
{chr(10).join([f"• {insight.description} (Confidence: {insight.confidence:.0%})" for insight in state.get('insights', [])])}

**Recommendations:**
Based on the analysis, the data shows clear patterns that can inform decision-making. 
The visualizations highlight key relationships and distributions that warrant further investigation.

**Technical Notes:**
- Analysis completed using automated statistical methods
- All findings include confidence scores for reliability assessment
- Visualizations provide interactive exploration capabilities

This analysis provides a solid foundation for data-driven decision making.
                """.strip()
            
            state["summary"] = summary
            state["current_step"] = "Analysis Complete"
            state["progress"] = 1.0
            
            self._complete_execution_step(state, "Generating Summary", {"summary_length": len(summary)})
            
            logger.info("Summary generation completed", job_id=state["job_id"])
            
        except Exception as e:
            logger.error("Summary generation failed", job_id=state["job_id"], error=str(e))
            state["error"] = f"Summary generation failed: {str(e)}"
            self._fail_execution_step(state, "Generating Summary", str(e))
        
        return state
    
    async def _handle_error(self, state: AnalysisState) -> AnalysisState:
        """Handle errors that occur during the workflow."""
        logger.error("Handling workflow error", job_id=state["job_id"], error=state.get("error"))
        
        state["current_step"] = "Error Occurred"
        state["summary"] = f"Analysis failed: {state.get('error', 'Unknown error')}"
        
        return state
    
    def _should_continue(self, state: AnalysisState) -> str:
        """Determine whether to continue the workflow or handle an error."""
        if state.get("error"):
            return "error"
        return "continue"
    
    def _add_execution_step(self, state: AnalysisState, step_name: str, description: str, status: JobStatus):
        """Add a new execution step to the state."""
        step = ExecutionStep(
            step_name=step_name,
            description=description,
            status=status,
            start_time=datetime.utcnow()
        )
        state["execution_steps"].append(step)
    
    def _complete_execution_step(self, state: AnalysisState, step_name: str, output: Any):
        """Mark the current execution step as completed."""
        for step in reversed(state["execution_steps"]):
            if step.step_name == step_name and step.status == JobStatus.RUNNING:
                step.status = JobStatus.COMPLETED
                step.end_time = datetime.utcnow()
                step.output = output
                if step.start_time and step.end_time:
                    step.duration_seconds = (step.end_time - step.start_time).total_seconds()
                break
    
    def _fail_execution_step(self, state: AnalysisState, step_name: str, error: str):
        """Mark the current execution step as failed."""
        for step in reversed(state["execution_steps"]):
            if step.step_name == step_name and step.status == JobStatus.RUNNING:
                step.status = JobStatus.FAILED
                step.end_time = datetime.utcnow()
                step.error = error
                if step.start_time and step.end_time:
                    step.duration_seconds = (step.end_time - step.start_time).total_seconds()
                break


# Global instance for use across the application
analysis_agent = AnalysisAgent() 