#!/usr/bin/env python3
"""
Simple run script for Analyst Agent

Usage:
    python run.py              # Start the API server
    python run.py --test       # Run tests
    python run.py --setup      # Validate setup
    python run.py --help       # Show help
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_api():
    """Start the API server with uvicorn."""
    print("🚀 Starting Analyst Agent API server...")
    print("   API will be available at: http://localhost:8000")
    print("   Documentation at: http://localhost:8000/docs")
    print("   Press Ctrl+C to stop")
    print()
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "analyst_agent.api.app:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

def run_tests():
    """Run the test suite."""
    print("🧪 Running Analyst Agent tests...")
    
    test_files = [
        "test_setup.py",
        "examples/multi_provider_test.py",
        "examples/new_system_test.py"
    ]
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"\n📝 Running {test_file}...")
            try:
                subprocess.run([sys.executable, test_file], check=True)
                print(f"✅ {test_file} passed")
            except subprocess.CalledProcessError:
                print(f"❌ {test_file} failed")
        else:
            print(f"⚠️  {test_file} not found, skipping...")

def validate_setup():
    """Validate the setup and configuration."""
    print("🔍 Validating Analyst Agent setup...")
    
    try:
        subprocess.run([sys.executable, "test_setup.py"], check=True)
    except subprocess.CalledProcessError:
        print("❌ Setup validation failed")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Analyst Agent - Autonomous AI Data Analyst",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py              # Start API server
  python run.py --test       # Run all tests  
  python run.py --setup      # Validate setup
  
For more options:
  python main.py --help      # Main application help
  uvicorn analyst_agent.api.app:app --help  # Server options
        """
    )
    
    parser.add_argument(
        "--test", 
        action="store_true",
        help="Run the test suite"
    )
    
    parser.add_argument(
        "--setup", 
        action="store_true",
        help="Validate setup and configuration"
    )
    
    args = parser.parse_args()
    
    if args.test:
        run_tests()
    elif args.setup:
        validate_setup()
    else:
        run_api()

if __name__ == "__main__":
    main() 