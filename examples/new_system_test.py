#!/usr/bin/env python3
"""
Test the new LangGraph-based analysis system.

This script demonstrates the complete workflow using the new connector system,
direct SQL generation, and quality validation.
"""

import asyncio
import json
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import sys

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analyst_agent.models.contracts import QuerySpec, DataSource, SupportedDialect, ValidationProfile
from analyst_agent.adapters import make_connector
from analyst_agent.core.graph import run_analysis_async


async def setup_test_database():
    """Create a test SQLite database with sample data."""
    db_path = Path("examples") / "test_data.db"
    
    # Remove existing database
    if db_path.exists():
        db_path.unlink()
    
    # Create new database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            signup_date DATE,
            country TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date DATE,
            total_amount DECIMAL(10,2),
            status TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE order_items (
            item_id INTEGER PRIMARY KEY,
            order_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            unit_price DECIMAL(10,2),
            FOREIGN KEY (order_id) REFERENCES orders (order_id)
        )
    """)
    
    # Insert sample customers
    customers_data = [
        (1, "Alice Smith", "alice@example.com", "2023-01-15", "USA"),
        (2, "Bob Johnson", "bob@example.com", "2023-02-20", "Canada"),
        (3, "Carol Brown", "carol@example.com", "2023-03-10", "UK"),
        (4, "David Wilson", "david@example.com", "2023-04-05", "Australia"),
        (5, "Eva Davis", "eva@example.com", "2023-05-12", "Germany"),
    ]
    
    cursor.executemany(
        "INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
        customers_data
    )
    
    # Insert sample orders
    orders_data = [
        (1, 1, "2023-06-01", 125.50, "completed"),
        (2, 1, "2023-06-15", 89.99, "completed"), 
        (3, 2, "2023-06-10", 234.75, "completed"),
        (4, 3, "2023-06-20", 45.00, "pending"),
        (5, 2, "2023-07-01", 156.25, "completed"),
        (6, 4, "2023-07-05", 78.99, "shipped"),
        (7, 5, "2023-07-10", 299.99, "completed"),
        (8, 1, "2023-07-15", 67.50, "completed"),
        (9, 3, "2023-07-20", 189.00, "completed"),
        (10, 4, "2023-08-01", 112.75, "completed"),
    ]
    
    cursor.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
        orders_data
    )
    
    # Insert sample order items
    items_data = [
        (1, 1, "Laptop", 1, 125.50),
        (2, 2, "Mouse", 2, 44.99),
        (3, 3, "Keyboard", 1, 89.99),
        (4, 3, "Monitor", 1, 144.76),
        (5, 4, "Headphones", 1, 45.00),
        (6, 5, "Webcam", 1, 67.25),
        (7, 5, "Microphone", 1, 89.00),
        (8, 6, "Cable", 3, 26.33),
        (9, 7, "Printer", 1, 299.99),
        (10, 8, "Paper", 5, 13.50),
        (11, 9, "Ink", 3, 63.00),
        (12, 10, "Scanner", 1, 112.75),
    ]
    
    cursor.executemany(
        "INSERT INTO order_items VALUES (?, ?, ?, ?, ?)",
        items_data
    )
    
    conn.commit()
    conn.close()
    
    print(f"✅ Created test database: {db_path}")
    return db_path


async def test_analysis_workflow():
    """Test the complete analysis workflow."""
    print("\n🚀 Testing New LangGraph Analysis System")
    print("=" * 50)
    
    # Setup test database
    db_path = await setup_test_database()
    
    # Create data source
    data_source = DataSource(
        kind="sqlite",
        config={
            "url": f"sqlite:///{db_path.absolute()}"
        },
        business_tz="UTC"
    )
    
    # Test cases with different complexity levels
    test_cases = [
        {
            "name": "Simple Count Query",
            "spec": QuerySpec(
                question="How many customers do we have?",
                dialect=SupportedDialect.SQLITE,
                validation_profile=ValidationProfile.FAST
            ),
            "expected_patterns": ["customer", "count", "5"]
        },
        {
            "name": "Sales Analysis",
            "spec": QuerySpec(
                question="What are the total sales by month and which customer has spent the most?",
                dialect=SupportedDialect.SQLITE,
                time_window="last_6_months",
                validation_profile=ValidationProfile.BALANCED
            ),
            "expected_patterns": ["sales", "month", "customer"]
        },
        {
            "name": "Product Analysis",
            "spec": QuerySpec(
                question="What are the top selling products and their average prices?",
                dialect=SupportedDialect.SQLITE,
                validation_profile=ValidationProfile.BALANCED
            ),
            "expected_patterns": ["product", "price", "quantity"]
        },
        {
            "name": "Order Status Analysis",
            "spec": QuerySpec(
                question="Show me the distribution of order statuses and average order values",
                dialect=SupportedDialect.SQLITE,
                filters={"min_amount": 50},
                validation_profile=ValidationProfile.STRICT
            ),
            "expected_patterns": ["status", "completed", "average"]
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📊 Test {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            # Create unique job ID
            job_id = f"test_{uuid.uuid4().hex[:8]}"
            
            # Create connector
            connector = make_connector(
                kind=data_source.kind,
                **data_source.config,
                business_tz=data_source.business_tz
            )
            
            # Set up execution context
            ctx = {
                "connector": connector,
                "dialect": test_case["spec"].dialect,
                "business_tz": data_source.business_tz
            }
            
            print(f"Question: {test_case['spec'].question}")
            print(f"Dialect: {test_case['spec'].dialect}")
            print(f"Validation: {test_case['spec'].validation_profile}")
            
            # Run analysis
            start_time = datetime.now()
            final_state = await run_analysis_async(
                job_id=job_id,
                spec=test_case["spec"].model_dump(),
                ctx=ctx
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            # Extract results
            quality = final_state.get("quality", {})
            answer = final_state.get("answer", "No answer")
            artifacts = final_state.get("artifacts", [])
            execution_steps = final_state.get("execution_steps", [])
            
            # Print results
            print(f"⏱️  Duration: {duration:.2f}s")
            print(f"✨ Quality Score: {quality.get('score', 0):.2f}")
            print(f"✅ Quality Passed: {quality.get('passed', False)}")
            print(f"📋 Answer: {answer}")
            print(f"🎯 Artifacts: {len(artifacts)}")
            print(f"🔄 Execution Steps: {len(execution_steps)}")
            
            # Show execution trace
            print("\n📊 Execution Trace:")
            for step in execution_steps[-3:]:  # Show last 3 steps
                status_icon = "✅" if step["status"] == "completed" else "❌" if step["status"] == "failed" else "⏳"
                print(f"   {status_icon} {step['step_name']}: {step['status']}")
                if step.get("sql"):
                    sql_preview = step["sql"][:100] + "..." if len(step["sql"]) > 100 else step["sql"]
                    print(f"      SQL: {sql_preview}")
                if step.get("row_count") is not None:
                    print(f"      Rows: {step['row_count']}")
            
            # Show artifacts
            if artifacts:
                print("\n🎨 Generated Artifacts:")
                for artifact in artifacts:
                    print(f"   📄 {artifact['kind']}: {artifact['title']}")
                    if artifact.get("content") and artifact["kind"] == "table":
                        data = artifact["content"].get("data", [])
                        print(f"      Rows: {len(data)}")
                        if data:
                            columns = list(data[0].keys()) if data else []
                            print(f"      Columns: {', '.join(columns[:5])}")
            
            # Validate expected patterns
            validation_passed = True
            for pattern in test_case.get("expected_patterns", []):
                if pattern.lower() not in answer.lower():
                    print(f"⚠️  Missing expected pattern: '{pattern}'")
                    validation_passed = False
            
            result = {
                "test_name": test_case["name"],
                "success": quality.get("passed", False),
                "validation_passed": validation_passed,
                "quality_score": quality.get("score", 0),
                "duration": duration,
                "answer": answer,
                "artifacts_count": len(artifacts),
                "steps_count": len(execution_steps)
            }
            
            results.append(result)
            
            # Close connector
            connector.close()
            
            if quality.get("passed", False) and validation_passed:
                print("🎉 Test PASSED!")
            else:
                print("⚠️  Test had issues but completed")
                
        except Exception as e:
            print(f"❌ Test FAILED: {str(e)}")
            result = {
                "test_name": test_case["name"],
                "success": False,
                "validation_passed": False,
                "quality_score": 0,
                "duration": 0,
                "error": str(e),
                "artifacts_count": 0,
                "steps_count": 0
            }
            results.append(result)
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    
    successful_tests = sum(1 for r in results if r["success"])
    total_tests = len(results)
    avg_quality = sum(r["quality_score"] for r in results) / total_tests if total_tests > 0 else 0
    total_duration = sum(r["duration"] for r in results)
    
    print(f"Tests Passed: {successful_tests}/{total_tests}")
    print(f"Average Quality Score: {avg_quality:.2f}")
    print(f"Total Duration: {total_duration:.2f}s")
    
    # Detailed results
    print("\n📝 Detailed Results:")
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"   {status} {result['test_name']}")
        print(f"      Quality: {result['quality_score']:.2f}")
        print(f"      Duration: {result['duration']:.2f}s")
        if result.get("error"):
            print(f"      Error: {result['error']}")
    
    return results


async def test_connector_capabilities():
    """Test the connector system capabilities."""
    print("\n🔧 Testing Connector Capabilities")
    print("=" * 50)
    
    from analyst_agent.adapters.registry import list_available_connectors
    from analyst_agent.core.dialect_caps import DIALECT_CAPABILITIES
    
    # List available connectors
    connectors = list_available_connectors()
    print(f"Available Connectors: {len(connectors)}")
    for kind, class_name in connectors.items():
        print(f"   📊 {kind}: {class_name}")
    
    # List dialect capabilities
    print(f"\nSupported Dialects: {len(DIALECT_CAPABILITIES)}")
    for dialect, caps in DIALECT_CAPABILITIES.items():
        features = []
        if caps.get("window_functions"):
            features.append("windows")
        if caps.get("cte"):
            features.append("CTEs")
        if caps.get("json_support"):
            features.append("JSON")
        if caps.get("ilike"):
            features.append("ILIKE")
        
        print(f"   🗃️  {dialect}: {', '.join(features)}")


async def main():
    """Main test runner."""
    print("🧪 Analyst Agent - New System Integration Test")
    print("=" * 60)
    
    try:
        # Test connector capabilities
        await test_connector_capabilities()
        
        # Test analysis workflow
        results = await test_analysis_workflow()
        
        # Overall assessment
        successful_tests = sum(1 for r in results if r["success"])
        total_tests = len(results)
        
        if successful_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! The new system is working correctly.")
            return 0
        elif successful_tests > 0:
            print(f"\n⚠️  PARTIAL SUCCESS: {successful_tests}/{total_tests} tests passed.")
            return 1
        else:
            print("\n❌ ALL TESTS FAILED! There are issues with the new system.")
            return 2
            
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    exit_code = asyncio.run(main()) 