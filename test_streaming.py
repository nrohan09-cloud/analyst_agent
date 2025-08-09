#!/usr/bin/env python3
"""
Test the streaming functionality with a simple analysis request.
"""

import asyncio
import json
import aiohttp
from datetime import datetime

API_BASE = "http://localhost:8000"

async def test_streaming_analysis():
    """Test the streaming analysis functionality."""
    
    # Create analysis request
    spec = {
        "question": "Show me all customers with their order counts",
        "dialect": "sqlite",
        "time_window": None,
        "filters": {},
        "budget": {"queries": 30, "seconds": 90},
        "validation_profile": "balanced"
    }
    
    data_source = {
        "kind": "sqlite",
        "config": {
            "database": "data/test_ecommerce.db"
        },
        "business_tz": "America/New_York"
    }
    
    async with aiohttp.ClientSession() as session:
        # Submit the analysis job
        print("🚀 Submitting analysis job...")
        async with session.post(f"{API_BASE}/v1/query", json={
            "spec": spec,
            "data_source": data_source
        }) as response:
            if response.status != 200:
                print(f"❌ Failed to submit job: {response.status}")
                return
            
            result = await response.json()
            job_id = result.get("job_id")
            
            if not job_id:
                print("❌ No job ID returned")
                return
            
            print(f"✅ Job submitted: {job_id}")
        
        # Stream the progress
        print("📡 Starting streaming...")
        try:
            async with session.get(f"{API_BASE}/v1/stream/{job_id}") as stream_response:
                if stream_response.status != 200:
                    print(f"❌ Failed to start stream: {stream_response.status}")
                    return
                
                async for line in stream_response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_json = line[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_json)
                            print_stream_event(data)
                        except json.JSONDecodeError:
                            print(f"⚠️  Could not parse: {data_json}")
                        
        except Exception as e:
            print(f"❌ Streaming error: {e}")

def print_stream_event(data):
    """Pretty print a stream event."""
    event_type = data.get('type', 'unknown')
    timestamp = datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat()))
    time_str = timestamp.strftime("%H:%M:%S")
    
    if event_type == 'status':
        status = data.get('status', 'unknown')
        print(f"[{time_str}] 📊 Status: {status}")
    
    elif event_type == 'step':
        step_name = data.get('step_name', 'unknown')
        status = data.get('status', 'unknown')
        row_count = data.get('row_count')
        error = data.get('error')
        
        if status == 'completed':
            emoji = "✅"
        elif status == 'running':
            emoji = "🔄"
        elif status == 'failed':
            emoji = "❌"
        else:
            emoji = "📝"
        
        msg = f"[{time_str}] {emoji} {step_name}: {status}"
        
        if row_count is not None:
            msg += f" ({row_count} rows)"
        if error:
            msg += f" - Error: {error}"
        
        print(msg)
    
    elif event_type == 'progress':
        progress = data.get('progress', 0)
        current_step = data.get('current_step', 'unknown')
        print(f"[{time_str}] 📈 Progress: {progress:.1f}% - {current_step}")
    
    elif event_type == 'completion':
        status = data.get('status', 'unknown')
        print(f"[{time_str}] 🏁 Completed: {status}")
        
        if status == 'completed':
            result = data.get('result', {})
            answer = result.get('answer', 'No answer')
            print(f"[{time_str}] 💡 Answer: {answer[:100]}...")
    
    elif event_type == 'error':
        error = data.get('error', 'Unknown error')
        print(f"[{time_str}] ❌ Error: {error}")
    
    else:
        print(f"[{time_str}] ❓ Unknown event: {event_type}")

if __name__ == "__main__":
    print("🧪 Testing Streaming Analysis API")
    print("=" * 50)
    asyncio.run(test_streaming_analysis())
