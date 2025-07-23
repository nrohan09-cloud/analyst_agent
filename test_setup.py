#!/usr/bin/env python3
"""
Setup test script for the Analyst Agent service.

This script verifies that all dependencies are installed correctly
and the basic functionality works as expected.
"""

import sys
import subprocess
import importlib
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} (compatible)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (requires 3.10+)")
        return False


def check_package_installation():
    """Check if required packages are installed."""
    print("\n📦 Checking package installation...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'pandas',
        'structlog',
        'httpx'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -e .")
        return False
    
    return True


def check_project_structure():
    """Check if the project structure is correct."""
    print("\n📁 Checking project structure...")
    
    required_files = [
        'pyproject.toml',
        'main.py',
        'analyst_agent/__init__.py',
        'analyst_agent/settings.py',
        'analyst_agent/schemas.py',
        'analyst_agent/api/app.py',
        'analyst_agent/api/routes/health.py',
        'analyst_agent/api/routes/analysis.py'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} (missing)")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️  Missing files: {', '.join(missing_files)}")
        return False
    
    return True


def test_import_modules():
    """Test importing the main modules."""
    print("\n🔍 Testing module imports...")
    
    try:
        from analyst_agent.settings import settings
        print("✅ Settings module")
        
        from analyst_agent.schemas import AnalysisRequest
        print("✅ Schemas module")
        
        from analyst_agent.api.app import app
        print("✅ FastAPI app")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality without starting the server."""
    print("\n⚙️  Testing basic functionality...")
    
    try:
        from analyst_agent.settings import settings
        
        # Test settings
        assert settings.app_name == "Analyst Agent"
        assert settings.api_port == 8000
        print("✅ Settings configuration")
        
        # Test schema validation
        from analyst_agent.schemas import AnalysisRequest, DataSourceConfig
        
        request = AnalysisRequest(
            question="Test question",
            data_source=DataSourceConfig(type="csv", file_path="/test.csv")
        )
        assert request.question == "Test question"
        print("✅ Schema validation")
        
        # Test FastAPI app creation
        from analyst_agent.api.app import create_app
        app = create_app()
        assert app.title == "Analyst Agent API"
        print("✅ FastAPI app creation")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False


def main():
    """Run all setup tests."""
    print("🧪 Analyst Agent Setup Test")
    print("=" * 50)
    
    tests = [
        check_python_version,
        check_package_installation,
        check_project_structure,
        test_import_modules,
        test_basic_functionality
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All tests passed ({passed}/{total})")
        print("\n🚀 Ready to start the service!")
        print("Run: python main.py")
        return True
    else:
        print(f"❌ {total - passed} tests failed ({passed}/{total})")
        print("\n🔧 Please fix the issues above before proceeding.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 