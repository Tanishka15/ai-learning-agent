#!/usr/bin/env python3
"""
Test the reasoning chain through direct API call with session
"""

import requests
import json

def test_reasoning_via_api():
    """Test reasoning chain via direct API call"""
    
    # First, try to establish a session
    session = requests.Session()
    
    # Try to access the main page to get session
    try:
        response = session.get("http://localhost:5005/")
        print(f"Main page status: {response.status_code}")
    except Exception as e:
        print(f"Error accessing main page: {e}")
        return
    
    # Try the chat endpoint with reasoning enabled
    chat_data = {
        "message": "What are my upcoming assignments?",
        "show_reasoning": True
    }
    
    try:
        response = session.post(
            "http://localhost:5005/chat",
            json=chat_data,
            headers={"Content-Type": "application/json"},
            allow_redirects=False
        )
        
        print(f"Chat response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"\n✅ Success! Response received:")
                print(f"Answer: {result.get('answer', 'No answer')}")
                
                reasoning_chain = result.get('reasoning_chain', [])
                if reasoning_chain:
                    print(f"\n🧠 Reasoning chain ({len(reasoning_chain)} steps):")
                    for i, step in enumerate(reasoning_chain, 1):
                        print(f"  {i}. {step.get('step_type', 'Unknown')}: {step.get('description', 'No description')}")
                else:
                    print("\n❌ No reasoning chain found!")
                    
            except json.JSONDecodeError:
                print(f"Response content: {response.text[:500]}...")
        else:
            print(f"Response content: {response.text[:500]}...")
            
    except Exception as e:
        print(f"Error making chat request: {e}")

if __name__ == "__main__":
    test_reasoning_via_api()