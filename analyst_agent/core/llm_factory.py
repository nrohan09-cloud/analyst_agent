"""
LLM Factory for multi-provider support.

Supports OpenAI, Anthropic, and other providers with automatic fallback logic.
"""

from typing import Optional, Dict, Any, List
from langchain_core.language_models import BaseChatModel
import structlog

from analyst_agent.settings import settings

logger = structlog.get_logger(__name__)

class LLMFactory:
    """Factory for creating LLM instances across different providers."""
    
    _cached_llms: Dict[str, BaseChatModel] = {}
    
    @classmethod
    def create_llm(
        cls, 
        provider: Optional[str] = None, 
        model: Optional[str] = None,
        temperature: float = 0,
        **kwargs
    ) -> BaseChatModel:
        """
        Create an LLM instance with automatic provider selection and fallback.
        
        Args:
            provider: LLM provider ("openai", "anthropic", "local")
            model: Model name
            temperature: Sampling temperature
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Configured LLM instance
        """
        provider = provider or settings.default_llm_provider
        model = model or settings.default_llm_model
        
        cache_key = f"{provider}:{model}:{temperature}"
        
        if cache_key in cls._cached_llms:
            return cls._cached_llms[cache_key]
        
        llm = cls._create_provider_llm(provider, model, temperature, **kwargs)
        
        if llm:
            cls._cached_llms[cache_key] = llm
            logger.info("Created LLM instance", provider=provider, model=model)
            return llm
        
        # Fallback logic
        logger.warning("Primary provider failed, trying fallbacks", provider=provider)
        for fallback_provider in cls._get_fallback_providers(provider):
            try:
                llm = cls._create_provider_llm(fallback_provider, model, temperature, **kwargs)
                if llm:
                    cls._cached_llms[cache_key] = llm
                    logger.info("Using fallback provider", 
                              original=provider, 
                              fallback=fallback_provider, 
                              model=model)
                    return llm
            except Exception as e:
                logger.warning("Fallback provider failed", 
                             provider=fallback_provider, 
                             error=str(e))
                continue
        
        raise Exception(f"No available LLM providers. Check your API keys.")
    
    @classmethod
    def _create_provider_llm(
        cls, 
        provider: str, 
        model: str, 
        temperature: float,
        **kwargs
    ) -> Optional[BaseChatModel]:
        """Create LLM for specific provider."""
        try:
            if provider == "openai":
                if not settings.openai_api_key:
                    logger.warning("OpenAI API key not configured")
                    return None
                
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    api_key=settings.openai_api_key,
                    **kwargs
                )
            
            elif provider == "anthropic":
                if not settings.anthropic_api_key:
                    logger.warning("Anthropic API key not configured")
                    return None
                
                from langchain_anthropic import ChatAnthropic
                # Map OpenAI model names to Anthropic equivalents
                anthropic_model = cls._map_to_anthropic_model(model)
                return ChatAnthropic(
                    model=anthropic_model,
                    temperature=temperature,
                    api_key=settings.anthropic_api_key,
                    **kwargs
                )
            
            elif provider == "local":
                # For local models (Ollama, LM Studio, etc.)
                from langchain_community.llms import Ollama
                return Ollama(
                    model=model,
                    temperature=temperature,
                    **kwargs
                )
            
            else:
                logger.error("Unsupported LLM provider", provider=provider)
                return None
                
        except ImportError as e:
            logger.error("LLM provider library not installed", 
                        provider=provider, 
                        error=str(e))
            return None
        except Exception as e:
            logger.error("Failed to create LLM instance", 
                        provider=provider, 
                        model=model, 
                        error=str(e))
            return None
    
    @classmethod
    def _map_to_anthropic_model(cls, openai_model: str) -> str:
        """Map OpenAI model names to Anthropic equivalents."""
        mapping = {
            "gpt-4": "claude-3-opus-20240229",
            "gpt-4-turbo": "claude-3-sonnet-20240229", 
            "gpt-3.5-turbo": "claude-3-haiku-20240307",
            "gpt-4o": "claude-3-5-sonnet-20241022"
        }
        return mapping.get(openai_model, "claude-3-sonnet-20240229")
    
    @classmethod
    def _get_fallback_providers(cls, primary_provider: str) -> List[str]:
        """Get ordered list of fallback providers."""
        all_providers = ["openai", "anthropic", "local"]
        fallbacks = [p for p in all_providers if p != primary_provider]
        
        # Prioritize providers with available API keys
        prioritized = []
        for provider in fallbacks:
            if provider == "openai" and settings.openai_api_key:
                prioritized.insert(0, provider)
            elif provider == "anthropic" and settings.anthropic_api_key:
                prioritized.insert(0, provider)
            else:
                prioritized.append(provider)
        
        return prioritized
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available providers based on configured API keys."""
        available = []
        
        if settings.openai_api_key:
            available.append("openai")
        if settings.anthropic_api_key:
            available.append("anthropic")
        
        # Local is always available if dependencies exist
        try:
            import ollama
            available.append("local")
        except ImportError:
            pass
        
        return available
    
    @classmethod
    def clear_cache(cls):
        """Clear the LLM cache."""
        cls._cached_llms.clear()
        logger.info("LLM cache cleared")


# Convenience function for backward compatibility
def create_llm(model: str = None, **kwargs) -> BaseChatModel:
    """Create an LLM instance using the factory."""
    return LLMFactory.create_llm(model=model, **kwargs) 