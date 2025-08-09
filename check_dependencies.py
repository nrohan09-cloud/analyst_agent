#!/usr/bin/env python3
"""
Dependency Checker for Analyst Agent

This script checks if all required packages are installed in your virtual environment
and provides helpful installation commands for missing packages.
"""

import sys
import subprocess
import importlib
import pkg_resources
from pathlib import Path
from typing import List, Dict, Tuple

# Core dependencies that must be present
CORE_DEPENDENCIES = {
    'fastapi': '0.104.0',
    'uvicorn': '0.24.0', 
    'langchain': '0.1.0',
    'langgraph': '0.1.0',
    'langchain-openai': '0.1.0',
    'pandas': '2.1.0',
    'pydantic': '2.5.0',
    'pydantic-settings': '2.1.0',
    'structlog': '23.2.0',
    'httpx': '0.25.0',
    'python-dotenv': '1.0.0',
    'sqlalchemy': '2.0.0',
    'pyarrow': '14.0.0'
}

# Optional dependencies for enhanced functionality
OPTIONAL_DEPENDENCIES = {
    'langchain-anthropic': '0.1.0',
    'langchain-community': '0.0.10',
    'duckdb': '0.9.0',
    'snowflake-connector-python': '3.5.0',
    'mysql-connector-python': '8.2.0',
    'pyodbc': '5.0.0',
    'asyncpg': '0.29.0',
    'psycopg2-binary': '2.9.0'
}

# Development dependencies
DEV_DEPENDENCIES = {
    'black': '23.10.0',
    'ruff': '0.1.0',
    'pytest': '7.4.0',
    'pytest-asyncio': '0.21.0',
    'mypy': '1.7.0'
}

def check_python_version() -> bool:
    """Check if Python version is compatible."""
    version = sys.version_info
    print(f"🐍 Python Version: {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 10):
        print("❌ Python 3.10+ is required")
        return False
    else:
        print("✅ Python version is compatible")
        return True

def check_virtual_env() -> bool:
    """Check if we're in a virtual environment."""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if in_venv:
        print("✅ Running in virtual environment")
        print(f"   Virtual env path: {sys.prefix}")
        return True
    else:
        print("⚠️  Not in a virtual environment")
        print("   Consider using: python -m venv venv && source venv/bin/activate")
        return False

def parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse version string into tuple for comparison."""
    try:
        return tuple(map(int, version_str.split('.')))
    except:
        return (0, 0, 0)

def check_package(package_name: str, min_version: str) -> Dict[str, any]:
    """Check if a package is installed and meets version requirements."""
    try:
        # Try to import the package
        importlib.import_module(package_name.replace('-', '_'))
        
        # Check version using pkg_resources
        try:
            installed_version = pkg_resources.get_distribution(package_name).version
            min_ver_tuple = parse_version(min_version)
            installed_ver_tuple = parse_version(installed_version)
            
            return {
                'installed': True,
                'version': installed_version,
                'meets_requirement': installed_ver_tuple >= min_ver_tuple,
                'error': None
            }
        except pkg_resources.DistributionNotFound:
            return {
                'installed': False,
                'version': None,
                'meets_requirement': False,
                'error': 'Package not found in pkg_resources'
            }
            
    except ImportError as e:
        return {
            'installed': False,
            'version': None,
            'meets_requirement': False,
            'error': str(e)
        }

def check_dependencies(deps: Dict[str, str], category: str) -> Tuple[List[str], List[str]]:
    """Check a category of dependencies."""
    print(f"\n📦 Checking {category} Dependencies:")
    print("-" * 50)
    
    installed = []
    missing = []
    
    for package, min_version in deps.items():
        result = check_package(package, min_version)
        
        if result['installed'] and result['meets_requirement']:
            print(f"✅ {package:<25} {result['version']}")
            installed.append(package)
        elif result['installed'] and not result['meets_requirement']:
            print(f"⚠️  {package:<25} {result['version']} (requires >={min_version})")
            missing.append(f"{package}>={min_version}")
        else:
            print(f"❌ {package:<25} Not installed")
            missing.append(f"{package}>={min_version}")
    
    return installed, missing

def check_analyst_agent_imports():
    """Check if analyst_agent modules can be imported."""
    print(f"\n🧠 Checking Analyst Agent Modules:")
    print("-" * 50)
    
    modules_to_check = [
        'analyst_agent.settings',
        'analyst_agent.api.app',
        'analyst_agent.core.graph',
        'analyst_agent.core.llm_factory',
        'analyst_agent.models.contracts',
        'analyst_agent.adapters.registry'
    ]
    
    all_good = True
    for module in modules_to_check:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module} - {e}")
            all_good = False
    
    return all_good

def generate_install_commands(missing_core: List[str], missing_optional: List[str], missing_dev: List[str]):
    """Generate installation commands for missing packages."""
    if not any([missing_core, missing_optional, missing_dev]):
        return
    
    print(f"\n🔧 Installation Commands:")
    print("=" * 50)
    
    if missing_core:
        print("📋 Core Dependencies (REQUIRED):")
        print(f"pip install {' '.join(missing_core)}")
        print()
    
    if missing_optional:
        print("🎯 Optional Dependencies (Enhanced functionality):")
        print(f"pip install {' '.join(missing_optional)}")
        print()
    
    if missing_dev:
        print("🛠️  Development Dependencies:")
        print(f"pip install {' '.join(missing_dev)}")
        print()
    
    print("💡 Or install everything at once:")
    print("pip install -e .")
    print("pip install -e \".[dev]\"  # Include dev dependencies")

def main():
    """Main dependency checking function."""
    print("🔍 Analyst Agent Dependency Checker")
    print("=" * 50)
    
    # Check Python version
    python_ok = check_python_version()
    
    # Check virtual environment
    venv_ok = check_virtual_env()
    
    # Check dependencies
    installed_core, missing_core = check_dependencies(CORE_DEPENDENCIES, "Core")
    installed_optional, missing_optional = check_dependencies(OPTIONAL_DEPENDENCIES, "Optional")
    installed_dev, missing_dev = check_dependencies(DEV_DEPENDENCIES, "Development")
    
    # Check analyst_agent modules
    modules_ok = check_analyst_agent_imports()
    
    # Summary
    print(f"\n📊 Summary:")
    print("=" * 50)
    print(f"Python Compatible: {'✅' if python_ok else '❌'}")
    print(f"Virtual Environment: {'✅' if venv_ok else '⚠️'}")
    print(f"Core Dependencies: {len(installed_core)}/{len(CORE_DEPENDENCIES)} ✅")
    print(f"Optional Dependencies: {len(installed_optional)}/{len(OPTIONAL_DEPENDENCIES)} ✅")
    print(f"Dev Dependencies: {len(installed_dev)}/{len(DEV_DEPENDENCIES)} ✅")
    print(f"Module Imports: {'✅' if modules_ok else '❌'}")
    
    # Generate install commands if needed
    generate_install_commands(missing_core, missing_optional, missing_dev)
    
    # Overall status
    if missing_core:
        print("\n❌ MISSING CORE DEPENDENCIES - Install required packages first!")
        return False
    elif not modules_ok:
        print("\n❌ MODULE IMPORT ERRORS - Check your installation!")
        return False
    else:
        print("\n🎉 All core dependencies are satisfied!")
        if missing_optional:
            print("💡 Consider installing optional dependencies for enhanced functionality")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 