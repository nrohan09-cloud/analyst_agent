#!/usr/bin/env python3
"""
Basic test example for the Analyst Agent API.

This script demonstrates how to use the service with a simple CSV analysis.
"""

import asyncio
import json
import os
from pathlib import Path

import pandas as pd
import httpx


async def test_api():
    """Test the basic API functionality."""
    base_url = "http://localhost:8000"
    
    # Check if the service is running
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/v1/health")
            print(f"✅ Service is running: {response.json()}")
        except httpx.ConnectError:
            print("❌ Service is not running. Start it with: python main.py")
            return
    
    # Create a sample CSV file for testing
    sample_data = {
        'product': ['A', 'B', 'C', 'A', 'B', 'C'] * 10,
        'sales': [100, 150, 200, 110, 160, 210] * 10,
        'month': ['Jan', 'Jan', 'Jan', 'Feb', 'Feb', 'Feb'] * 10,
        'region': ['North', 'South', 'East', 'West', 'North', 'South'] * 10
    }
    
    # Create examples directory and CSV file
    examples_dir = Path("examples")
    examples_dir.mkdir(exist_ok=True)
    csv_path = examples_dir / "sample_sales.csv"
    
    df = pd.DataFrame(sample_data)
    df.to_csv(csv_path, index=False)
    print(f"📊 Created sample data: {csv_path}")
    
    # Test the analysis API
    analysis_request = {
        "question": "What are the top selling products and their sales trends?",
        "data_source": {
            "type": "csv",
            "file_path": str(csv_path.absolute())
        },
        "preferences": {
            "analysis_types": ["descriptive"],
            "chart_types": ["bar", "line"],
            "include_code": False
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Submit analysis request
        print("\n🚀 Submitting analysis request...")
        response = await client.post(
            f"{base_url}/v1/ask",
            json=analysis_request
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to submit request: {response.text}")
            return
        
        result = response.json()
        job_id = result["job_id"]
        print(f"📝 Job submitted with ID: {job_id}")
        
        # Poll for completion
        print("⏳ Waiting for analysis to complete...")
        while True:
            status_response = await client.get(f"{base_url}/v1/jobs/{job_id}")
            status_data = status_response.json()
            
            print(f"   Status: {status_data['status']} - {status_data.get('current_step', 'N/A')}")
            
            if status_data["status"] == "completed":
                print("✅ Analysis completed!")
                result = status_data["result"]
                print(f"\n📋 Summary: {result['summary']}")
                print(f"📊 Found {len(result['insights'])} insights")
                print(f"📈 Generated {len(result['charts'])} charts")
                break
            elif status_data["status"] == "failed":
                print(f"❌ Analysis failed: {status_data.get('error', 'Unknown error')}")
                break
            
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(test_api()) 