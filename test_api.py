#!/usr/bin/env python3
"""
Simple test script for MCP FastAPI
"""
import asyncio
import httpx
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

async def test_api_endpoints():
    """Test the main API endpoints"""
    async with httpx.AsyncClient() as client:
        print("🧪 Testing MCP FastAPI endpoints...")
        
        # Test root endpoint
        print("\n1. Testing root endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test health check
        print("\n2. Testing health endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                health = response.json()
                print(f"   Overall Healthy: {health.get('overall_healthy', False)}")
                print(f"   Components: {list(health.get('components', {}).keys())}")
            else:
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test status endpoint
        print("\n3. Testing status endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/status")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                status = response.json()
                print(f"   Version: {status.get('version', 'unknown')}")
                print(f"   Initialized: {status.get('initialized', False)}")
                print(f"   Running: {status.get('running', False)}")
            else:
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test tools endpoint
        print("\n4. Testing tools endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/tools")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                tools = response.json()
                print(f"   Available tools: {len(tools)} found")
                if tools:
                    print(f"   Tool categories: {list(tools.keys())}")
            else:
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test analysis types endpoint
        print("\n5. Testing analysis types endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/analysis/types")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                types = response.json()
                print(f"   Available analysis types: {types}")
            else:
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test chat endpoint
        print("\n6. Testing chat endpoint...")
        try:
            chat_request = {
                "message": "Hello! What can you help me with?",
                "context": {}
            }
            response = await client.post(
                f"{BASE_URL}/chat",
                json=chat_request
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                chat_response = response.json()
                print(f"   Success: {chat_response.get('success', False)}")
                print(f"   Response: {chat_response.get('response', 'No response')[:100]}...")
                print(f"   Suggestions: {len(chat_response.get('suggestions', []))}")
            else:
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        print("\n✅ API testing complete!")

def main():
    """Run the tests"""
    print("🚀 Starting MCP FastAPI tests...")
    print(f"📡 Base URL: {BASE_URL}")
    print("📝 Make sure the API server is running: python run_api.py")
    
    asyncio.run(test_api_endpoints())

if __name__ == "__main__":
    main() 