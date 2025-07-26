"""
Dynamic Agent Registry for Ad-Hoc Agent Participation

This module provides a registry system where specialized agents can register
themselves and be dynamically discovered and invoked by the main workflow.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum
import asyncio
from dataclasses import dataclass
import structlog

from analyst_agent.schemas import AnalysisRequest, JobStatus

logger = structlog.get_logger(__name__)


class AgentCapability(Enum):
    """Capabilities that agents can provide."""
    DATA_LOADING = "data_loading"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    MACHINE_LEARNING = "machine_learning"
    VISUALIZATION = "visualization"
    TIME_SERIES = "time_series"
    TEXT_ANALYSIS = "text_analysis"
    DATABASE_QUERY = "database_query"
    API_INTEGRATION = "api_integration"
    GEOSPATIAL = "geospatial"
    FINANCIAL_ANALYSIS = "financial_analysis"
    ANOMALY_DETECTION = "anomaly_detection"
    PREDICTION = "prediction"
    REPORTING = "reporting"
    DATA_VALIDATION = "data_validation"


class AgentPriority(Enum):
    """Priority levels for agent execution."""
    CRITICAL = 1     # Must run (e.g., data validation)
    HIGH = 2         # Should run if applicable
    MEDIUM = 3       # Nice to have
    LOW = 4          # Optional enhancement


@dataclass
class AgentMetadata:
    """Metadata about a registered agent."""
    name: str
    description: str
    capabilities: Set[AgentCapability]
    priority: AgentPriority
    dependencies: List[str]  # Agent names this agent depends on
    execution_time_estimate: float  # Seconds
    resource_requirements: Dict[str, Any]
    
    
class BaseAgent(ABC):
    """Base class for all dynamically registrable agents."""
    
    @property
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        """Return metadata about this agent."""
        pass
    
    @abstractmethod
    async def can_handle(self, request: AnalysisRequest, context: Dict[str, Any]) -> float:
        """
        Determine if this agent can handle the request.
        
        Args:
            request: The analysis request
            context: Current analysis context/state
            
        Returns:
            Confidence score 0.0-1.0 (0 = cannot handle, 1 = perfect match)
        """
        pass
    
    @abstractmethod
    async def execute(self, request: AnalysisRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's functionality.
        
        Args:
            request: The analysis request
            context: Current analysis context/state
            
        Returns:
            Results to be merged into the analysis state
        """
        pass
    
    @abstractmethod
    async def estimate_cost(self, request: AnalysisRequest, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Estimate the cost of running this agent.
        
        Returns:
            Dictionary with cost estimates (time, compute, api_calls, etc.)
        """
        pass


class AgentRegistry:
    """Registry for dynamically discovering and managing agents."""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._capability_map: Dict[AgentCapability, List[str]] = {}
        
    def register_agent(self, agent: BaseAgent) -> None:
        """Register a new agent."""
        metadata = agent.metadata
        self._agents[metadata.name] = agent
        
        # Update capability mapping
        for capability in metadata.capabilities:
            if capability not in self._capability_map:
                self._capability_map[capability] = []
            self._capability_map[capability].append(metadata.name)
            
        logger.info("Registered agent", 
                   agent_name=metadata.name, 
                   capabilities=[c.value for c in metadata.capabilities])
    
    def unregister_agent(self, agent_name: str) -> None:
        """Remove an agent from the registry."""
        if agent_name in self._agents:
            agent = self._agents[agent_name]
            metadata = agent.metadata
            
            # Remove from capability mapping
            for capability in metadata.capabilities:
                if capability in self._capability_map:
                    self._capability_map[capability] = [
                        name for name in self._capability_map[capability] 
                        if name != agent_name
                    ]
            
            del self._agents[agent_name]
            logger.info("Unregistered agent", agent_name=agent_name)
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get a specific agent by name."""
        return self._agents.get(agent_name)
    
    def get_agents_by_capability(self, capability: AgentCapability) -> List[BaseAgent]:
        """Get all agents that provide a specific capability."""
        agent_names = self._capability_map.get(capability, [])
        return [self._agents[name] for name in agent_names if name in self._agents]
    
    def list_agents(self) -> List[AgentMetadata]:
        """List all registered agents."""
        return [agent.metadata for agent in self._agents.values()]
    
    async def find_capable_agents(self, 
                                request: AnalysisRequest, 
                                context: Dict[str, Any],
                                min_confidence: float = 0.3) -> List[tuple[BaseAgent, float]]:
        """
        Find agents capable of handling the request.
        
        Args:
            request: Analysis request
            context: Current context
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of (agent, confidence_score) tuples, sorted by confidence
        """
        capable_agents = []
        
        for agent in self._agents.values():
            try:
                confidence = await agent.can_handle(request, context)
                if confidence >= min_confidence:
                    capable_agents.append((agent, confidence))
            except Exception as e:
                logger.error("Error checking agent capability", 
                           agent_name=agent.metadata.name, 
                           error=str(e))
        
        # Sort by confidence (highest first)
        capable_agents.sort(key=lambda x: x[1], reverse=True)
        return capable_agents
    
    def resolve_dependencies(self, agent_names: List[str]) -> List[str]:
        """
        Resolve agent dependencies and return execution order.
        
        Args:
            agent_names: List of agent names to execute
            
        Returns:
            Ordered list of agent names respecting dependencies
        """
        # Simple topological sort for dependency resolution
        result = []
        visited = set()
        temp_visited = set()
        
        def visit(agent_name: str):
            if agent_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {agent_name}")
            if agent_name in visited:
                return
                
            temp_visited.add(agent_name)
            
            agent = self._agents.get(agent_name)
            if agent:
                for dep in agent.metadata.dependencies:
                    if dep in agent_names:  # Only consider dependencies in our execution list
                        visit(dep)
            
            temp_visited.remove(agent_name)
            visited.add(agent_name)
            result.append(agent_name)
        
        for name in agent_names:
            if name not in visited:
                visit(name)
        
        return result


# Global registry instance
agent_registry = AgentRegistry() 