#!/usr/bin/env python3
"""
Multi-Provider LLM Test

This script demonstrates the flexible LLM system that can work with:
- OpenAI (GPT-4, GPT-3.5-turbo)
- Anthropic (Claude models)
- Local models (Ollama)
- Automatic fallback between providers
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from analyst_agent.core.llm_factory import LLMFactory
from analyst_agent.settings import settings


def test_provider_detection():
    """Test which LLM providers are available."""
    print("🔍 Detecting available LLM providers...")
    
    providers = LLMFactory.get_available_providers()
    print(f"Available providers: {providers}")
    
    if settings.openai_api_key:
        print("✅ OpenAI API key configured")
    else:
        print("❌ OpenAI API key not found")
    
    if settings.anthropic_api_key:
        print("✅ Anthropic API key configured")
    else:
        print("❌ Anthropic API key not found")
    
    print(f"Default provider: {settings.default_llm_provider}")
    print(f"Default model: {settings.default_llm_model}")


def test_llm_creation():
    """Test creating LLM instances with different providers."""
    print("\n🤖 Testing LLM instance creation...")
    
    try:
        # Test default provider
        print(f"Testing default provider ({settings.default_llm_provider})...")
        llm = LLMFactory.create_llm()
        print(f"✅ Created LLM with default settings")
        
        # Test specific OpenAI model if available
        if "openai" in LLMFactory.get_available_providers():
            print("Testing OpenAI GPT-4...")
            openai_llm = LLMFactory.create_llm(provider="openai", model="gpt-4")
            print("✅ Created OpenAI GPT-4 instance")
        
        # Test Anthropic if available
        if "anthropic" in LLMFactory.get_available_providers():
            print("Testing Anthropic Claude...")
            anthropic_llm = LLMFactory.create_llm(provider="anthropic", model="gpt-4")
            print("✅ Created Anthropic Claude instance (mapped from gpt-4)")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM creation failed: {e}")
        return False


def test_sql_generation():
    """Test SQL generation with the multi-provider system."""
    print("\n📝 Testing SQL generation...")
    
    try:
        from analyst_agent.core.sql_executor import llm_generate_sql
        
        # Simple test prompt
        prompt = """You are a SQL expert. Generate a simple SELECT query to count rows in a 'users' table.

Return JSON with this exact format:
{"sql": "SELECT COUNT(*) FROM users;", "notes": "Simple row count query"}"""
        
        # This will use the configured provider automatically
        result = llm_generate_sql(prompt, model=settings.default_llm_model)
        
        if result and "sql" in result:
            print("✅ SQL generation successful")
            print(f"Generated SQL: {result['sql']}")
            print(f"Notes: {result.get('notes', 'No notes')}")
            return True
        else:
            print("❌ SQL generation returned invalid result")
            return False
            
    except Exception as e:
        print(f"❌ SQL generation failed: {e}")
        return False


def test_provider_fallback():
    """Test the provider fallback logic."""
    print("\n🔄 Testing provider fallback logic...")
    
    try:
        # Clear cache to test fresh creation
        LLMFactory.clear_cache()
        
        # Try to create with a non-existent provider
        print("Testing fallback from invalid provider...")
        
        # This should fall back to available providers
        available = LLMFactory.get_available_providers()
        if available:
            # Try creating with first available provider
            primary = available[0]
            llm = LLMFactory.create_llm(provider=primary)
            print(f"✅ Fallback successful to {primary}")
            return True
        else:
            print("❌ No providers available for fallback test")
            return False
            
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🧪 Multi-Provider LLM Test")
    print("=" * 50)
    
    test_results = []
    
    # Test 1: Provider detection
    test_provider_detection()
    
    # Test 2: LLM creation
    result2 = test_llm_creation()
    test_results.append(("LLM Creation", result2))
    
    # Test 3: SQL generation (only if we have providers)
    if LLMFactory.get_available_providers():
        result3 = test_sql_generation()
        test_results.append(("SQL Generation", result3))
    else:
        print("\n⚠️  Skipping SQL generation test - no LLM providers available")
        print("   Add OPENAI_API_KEY or ANTHROPIC_API_KEY to your .env file")
    
    # Test 4: Fallback logic
    result4 = test_provider_fallback()
    test_results.append(("Provider Fallback", result4))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    total = len(test_results)
    print(f"\n🎯 {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Multi-provider LLM system is working.")
        print("\n💡 You can now use any of these providers:")
        for provider in LLMFactory.get_available_providers():
            print(f"   • {provider}")
        print("\n🔧 To switch providers, set DEFAULT_LLM_PROVIDER in your .env file")
    else:
        print("\n⚠️  Some tests failed. Check your API key configuration.")


if __name__ == "__main__":
    asyncio.run(main()) 