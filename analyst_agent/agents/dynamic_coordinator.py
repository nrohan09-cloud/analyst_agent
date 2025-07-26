"""
Dynamic Workflow Coordinator

This coordinator builds and executes workflows dynamically based on:
1. Analysis requirements
2. Available agents 
3. Agent capabilities and confidence scores
4. Resource constraints and priorities
"""

import asyncio
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import json
import structlog

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from analyst_agent.schemas import AnalysisRequest, AnalysisResult, JobStatus, ExecutionStep
from analyst_agent.agents.agent_registry import (
    agent_registry, 
    BaseAgent, 
    AgentCapability, 
    AgentPriority
)

logger = structlog.get_logger(__name__)


class DynamicAnalysisState(Dict[str, Any]):
    """Extended state that supports dynamic agent execution."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Core state
        self.setdefault("job_id", "")
        self.setdefault("request", None)
        self.setdefault("current_step", "")
        self.setdefault("progress", 0.0)
        self.setdefault("execution_steps", [])
        self.setdefault("error", None)
        
        # Dynamic workflow state
        self.setdefault("available_agents", [])
        self.setdefault("selected_agents", [])
        self.setdefault("execution_plan", [])
        self.setdefault("agent_results", {})
        self.setdefault("capabilities_needed", set())
        self.setdefault("resource_budget", {})
        
        # Analysis artifacts
        self.setdefault("data_info", None)
        self.setdefault("insights", [])
        self.setdefault("visualizations", [])
        self.setdefault("summary", None)


class DynamicWorkflowCoordinator:
    """Coordinates dynamic workflow execution with ad-hoc agent participation."""
    
    def __init__(self):
        self.memory = MemorySaver()
        
    async def execute_analysis(self, job_id: str, request: AnalysisRequest) -> AnalysisResult:
        """
        Execute analysis with dynamic agent selection and workflow building.
        """
        logger.info("Starting dynamic analysis execution", 
                   job_id=job_id, 
                   question=request.question)
        
        # Initialize dynamic state
        state = DynamicAnalysisState({
            "job_id": job_id,
            "request": request,
            "current_step": "Initializing Dynamic Workflow",
            "progress": 0.0,
            "execution_steps": [],
            "resource_budget": {
                "max_time_seconds": 300,
                "max_api_calls": 50,
                "max_memory_mb": 512
            }
        })
        
        try:
            # Phase 1: Analyze requirements and discover agents
            await self._analyze_requirements(state)
            await self._discover_agents(state)
            
            # Phase 2: Plan optimal workflow
            await self._plan_dynamic_workflow(state)
            
            # Phase 3: Execute workflow dynamically
            await self._execute_dynamic_workflow(state)
            
            # Phase 4: Synthesize results
            await self._synthesize_results(state)
            
            # Create final result
            result = AnalysisResult(
                job_id=job_id,
                status=JobStatus.FAILED if state.get("error") else JobStatus.COMPLETED,
                question=request.question,
                summary=state.get("summary", "Dynamic analysis completed"),
                insights=state.get("insights", []),
                charts=state.get("visualizations", []),
                tables=[],
                execution_steps=state.get("execution_steps", []),
                metadata={
                    "workflow_type": "dynamic",
                    "agents_executed": [agent["name"] for agent in state.get("selected_agents", [])],
                    "capabilities_used": list(state.get("capabilities_needed", set())),
                    "execution_plan": state.get("execution_plan", [])
                },
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error_message=state.get("error")
            )
            
            logger.info("Dynamic analysis execution completed", 
                       job_id=job_id, 
                       status=result.status,
                       agents_count=len(state.get("selected_agents", [])))
            return result
            
        except Exception as e:
            logger.error("Dynamic analysis execution failed", 
                        job_id=job_id, 
                        error=str(e), 
                        exc_info=True)
            
            return AnalysisResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                question=request.question,
                summary="Dynamic analysis failed due to an error",
                insights=[],
                charts=[],
                tables=[],
                execution_steps=state.get("execution_steps", []),
                metadata={"error_type": type(e).__name__},
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )
    
    async def _analyze_requirements(self, state: DynamicAnalysisState):
        """Analyze the request to determine what capabilities are needed."""
        self._add_execution_step(state, "Requirement Analysis", 
                                "Analyzing request to determine needed capabilities", 
                                JobStatus.RUNNING)
        
        try:
            request = state["request"]
            question = request.question.lower()
            data_source = request.data_source
            
            # Determine needed capabilities based on question and data source
            capabilities_needed = set()
            
            # Always need data loading
            capabilities_needed.add(AgentCapability.DATA_LOADING)
            
            # Analyze question for specific requirements
            if any(word in question for word in ["trend", "time", "temporal", "seasonal"]):
                capabilities_needed.add(AgentCapability.TIME_SERIES)
            
            if any(word in question for word in ["predict", "forecast", "future"]):
                capabilities_needed.add(AgentCapability.PREDICTION)
                capabilities_needed.add(AgentCapability.MACHINE_LEARNING)
            
            if any(word in question for word in ["anomaly", "outlier", "unusual"]):
                capabilities_needed.add(AgentCapability.ANOMALY_DETECTION)
            
            if any(word in question for word in ["visualize", "chart", "plot", "graph"]):
                capabilities_needed.add(AgentCapability.VISUALIZATION)
            
            if any(word in question for word in ["text", "sentiment", "nlp"]):
                capabilities_needed.add(AgentCapability.TEXT_ANALYSIS)
            
            if any(word in question for word in ["geo", "location", "spatial", "map"]):
                capabilities_needed.add(AgentCapability.GEOSPATIAL)
            
            if any(word in question for word in ["financial", "revenue", "profit", "cost"]):
                capabilities_needed.add(AgentCapability.FINANCIAL_ANALYSIS)
            
            # Always include basic statistical analysis and reporting
            capabilities_needed.add(AgentCapability.STATISTICAL_ANALYSIS)
            capabilities_needed.add(AgentCapability.REPORTING)
            
            # Data source specific capabilities
            if data_source.type.value == "database":
                capabilities_needed.add(AgentCapability.DATABASE_QUERY)
            elif data_source.type.value == "api":
                capabilities_needed.add(AgentCapability.API_INTEGRATION)
            
            state["capabilities_needed"] = capabilities_needed
            state["current_step"] = "Requirements Analyzed"
            state["progress"] = 0.1
            
            self._complete_execution_step(state, "Requirement Analysis", {
                "capabilities_needed": [c.value for c in capabilities_needed],
                "data_source_type": data_source.type.value
            })
            
            logger.info("Requirements analysis completed", 
                       job_id=state["job_id"],
                       capabilities_needed=[c.value for c in capabilities_needed])
            
        except Exception as e:
            self._fail_execution_step(state, "Requirement Analysis", str(e))
            raise
    
    async def _discover_agents(self, state: DynamicAnalysisState):
        """Discover available agents that can handle the requirements."""
        self._add_execution_step(state, "Agent Discovery", 
                                "Finding capable agents for the analysis", 
                                JobStatus.RUNNING)
        
        try:
            request = state["request"]
            capabilities_needed = state["capabilities_needed"]
            
            # Find agents for each needed capability
            all_capable_agents = []
            
            for capability in capabilities_needed:
                agents = agent_registry.get_agents_by_capability(capability)
                for agent in agents:
                    confidence = await agent.can_handle(request, state)
                    if confidence > 0.3:  # Minimum confidence threshold
                        all_capable_agents.append({
                            "agent": agent,
                            "name": agent.metadata.name,
                            "confidence": confidence,
                            "capability": capability,
                            "priority": agent.metadata.priority.value,
                            "estimated_time": agent.metadata.execution_time_estimate
                        })
            
            # Remove duplicates and sort by confidence and priority
            seen_agents = set()
            unique_agents = []
            for agent_info in all_capable_agents:
                if agent_info["name"] not in seen_agents:
                    unique_agents.append(agent_info)
                    seen_agents.add(agent_info["name"])
            
            # Sort by priority (lower is better) then confidence (higher is better)
            unique_agents.sort(key=lambda x: (x["priority"], -x["confidence"]))
            
            state["available_agents"] = unique_agents
            state["current_step"] = "Agents Discovered"
            state["progress"] = 0.2
            
            self._complete_execution_step(state, "Agent Discovery", {
                "agents_found": len(unique_agents),
                "agent_names": [a["name"] for a in unique_agents]
            })
            
            logger.info("Agent discovery completed", 
                       job_id=state["job_id"],
                       agents_found=len(unique_agents))
            
        except Exception as e:
            self._fail_execution_step(state, "Agent Discovery", str(e))
            raise
    
    async def _plan_dynamic_workflow(self, state: DynamicAnalysisState):
        """Plan the optimal workflow execution order."""
        self._add_execution_step(state, "Workflow Planning", 
                                "Planning optimal agent execution order", 
                                JobStatus.RUNNING)
        
        try:
            available_agents = state["available_agents"]
            resource_budget = state["resource_budget"]
            
            # Select agents based on priority, confidence, and resource constraints
            selected_agents = []
            total_estimated_time = 0
            
            for agent_info in available_agents:
                # Check if we have budget for this agent
                if (total_estimated_time + agent_info["estimated_time"] 
                    <= resource_budget["max_time_seconds"]):
                    selected_agents.append(agent_info)
                    total_estimated_time += agent_info["estimated_time"]
                    
                    # Stop if we have critical capabilities covered
                    if agent_info["priority"] == AgentPriority.CRITICAL.value:
                        continue
                    
                    # Limit number of agents to prevent overload
                    if len(selected_agents) >= 8:
                        break
            
            # Resolve dependencies and create execution plan
            agent_names = [a["name"] for a in selected_agents]
            execution_order = agent_registry.resolve_dependencies(agent_names)
            
            # Create detailed execution plan
            execution_plan = []
            for i, agent_name in enumerate(execution_order):
                agent_info = next(a for a in selected_agents if a["name"] == agent_name)
                execution_plan.append({
                    "step": i + 1,
                    "agent_name": agent_name,
                    "capability": agent_info["capability"].value,
                    "confidence": agent_info["confidence"],
                    "estimated_time": agent_info["estimated_time"]
                })
            
            state["selected_agents"] = selected_agents
            state["execution_plan"] = execution_plan
            state["current_step"] = "Workflow Planned"
            state["progress"] = 0.3
            
            self._complete_execution_step(state, "Workflow Planning", {
                "selected_agents": len(selected_agents),
                "execution_plan": execution_plan,
                "total_estimated_time": total_estimated_time
            })
            
            logger.info("Workflow planning completed", 
                       job_id=state["job_id"],
                       selected_agents=len(selected_agents),
                       execution_order=execution_order)
            
        except Exception as e:
            self._fail_execution_step(state, "Workflow Planning", str(e))
            raise
    
    async def _execute_dynamic_workflow(self, state: DynamicAnalysisState):
        """Execute the planned workflow with dynamic agents."""
        execution_plan = state["execution_plan"]
        total_steps = len(execution_plan)
        
        for i, step in enumerate(execution_plan):
            agent_name = step["agent_name"]
            
            self._add_execution_step(state, f"Execute {agent_name}", 
                                    f"Running {agent_name} agent", 
                                    JobStatus.RUNNING)
            
            try:
                # Get the agent
                agent = agent_registry.get_agent(agent_name)
                if not agent:
                    raise ValueError(f"Agent {agent_name} not found in registry")
                
                # Execute the agent
                logger.info("Executing agent", 
                           agent_name=agent_name, 
                           step=i+1, 
                           total_steps=total_steps)
                
                agent_result = await agent.execute(state["request"], state)
                
                # Merge results into state
                state["agent_results"][agent_name] = agent_result
                
                # Update specific state fields based on agent results
                if "insights" in agent_result:
                    state.setdefault("insights", []).extend(agent_result["insights"])
                if "visualizations" in agent_result:
                    state.setdefault("visualizations", []).extend(agent_result["visualizations"])
                if "data_info" in agent_result:
                    state["data_info"] = agent_result["data_info"]
                
                # Update progress
                state["progress"] = 0.3 + (0.6 * (i + 1) / total_steps)
                state["current_step"] = f"Completed {agent_name}"
                
                self._complete_execution_step(state, f"Execute {agent_name}", {
                    "agent_name": agent_name,
                    "result_keys": list(agent_result.keys())
                })
                
            except Exception as e:
                logger.error("Agent execution failed", 
                           agent_name=agent_name, 
                           error=str(e))
                self._fail_execution_step(state, f"Execute {agent_name}", str(e))
                # Continue with other agents instead of failing completely
                continue
    
    async def _synthesize_results(self, state: DynamicAnalysisState):
        """Synthesize results from all executed agents."""
        self._add_execution_step(state, "Result Synthesis", 
                                "Combining results from all agents", 
                                JobStatus.RUNNING)
        
        try:
            agent_results = state["agent_results"]
            insights = state.get("insights", [])
            visualizations = state.get("visualizations", [])
            
            # Create summary based on all agent outputs
            summary_parts = [
                f"## Dynamic Analysis Results",
                f"",
                f"**Question:** {state['request'].question}",
                f"",
                f"**Agents Executed:** {len(agent_results)}",
                f"**Insights Generated:** {len(insights)}",
                f"**Visualizations Created:** {len(visualizations)}",
                f"",
                f"**Key Findings:**"
            ]
            
            for insight in insights[:5]:  # Top 5 insights
                summary_parts.append(f"• {insight.description}")
            
            summary_parts.extend([
                f"",
                f"**Analysis Approach:**",
                f"This analysis used a dynamic workflow that automatically selected and coordinated multiple specialized agents based on the question requirements. Each agent contributed its expertise to provide comprehensive insights.",
                f"",
                f"**Agents Involved:**"
            ])
            
            for agent_name, result in agent_results.items():
                summary_parts.append(f"• **{agent_name}**: {result.get('description', 'Analysis completed')}")
            
            state["summary"] = "\n".join(summary_parts)
            state["current_step"] = "Analysis Complete"
            state["progress"] = 1.0
            
            self._complete_execution_step(state, "Result Synthesis", {
                "total_insights": len(insights),
                "total_visualizations": len(visualizations),
                "agents_executed": list(agent_results.keys())
            })
            
        except Exception as e:
            self._fail_execution_step(state, "Result Synthesis", str(e))
            raise
    
    def _add_execution_step(self, state: DynamicAnalysisState, step_name: str, description: str, status: JobStatus):
        """Add a new execution step to the state."""
        step = ExecutionStep(
            step_name=step_name,
            description=description,
            status=status,
            start_time=datetime.utcnow()
        )
        state["execution_steps"].append(step)
    
    def _complete_execution_step(self, state: DynamicAnalysisState, step_name: str, output: Any):
        """Mark the current execution step as completed."""
        for step in reversed(state["execution_steps"]):
            if step.step_name == step_name and step.status == JobStatus.RUNNING:
                step.status = JobStatus.COMPLETED
                step.end_time = datetime.utcnow()
                step.output = output
                if step.start_time and step.end_time:
                    step.duration_seconds = (step.end_time - step.start_time).total_seconds()
                break
    
    def _fail_execution_step(self, state: DynamicAnalysisState, step_name: str, error: str):
        """Mark the current execution step as failed."""
        for step in reversed(state["execution_steps"]):
            if step.step_name == step_name and step.status == JobStatus.RUNNING:
                step.status = JobStatus.FAILED
                step.end_time = datetime.utcnow()
                step.error = error
                if step.start_time and step.end_time:
                    step.duration_seconds = (step.end_time - step.start_time).total_seconds()
                break


# Global coordinator instance
dynamic_coordinator = DynamicWorkflowCoordinator() 