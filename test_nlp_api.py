"""
Quick API Test Script
Tests all NLP endpoints to verify they're working
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n1. Testing Health Endpoint...")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/api/nlp/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_analyze():
    """Test conversation analysis"""
    print("\n2. Testing Conversation Analysis...")
    print("-" * 60)
    try:
        data = {
            "text": "Hello, I goes to school yesterday. I wants to improve my English speaking skills."
        }
        response = requests.post(f"{BASE_URL}/api/nlp/analyze", json=data)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Topics: {result.get('topics', [])}")
        print(f"Grammar Issues: {len(result.get('grammar_issues', []))} found")
        print(f"Vocabulary Level: {result.get('vocabulary_level')}")
        print(f"Suggestions: {result.get('suggestions', [])}")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_quiz():
    """Test quiz generation"""
    print("\n3. Testing Quiz Generation...")
    print("-" * 60)
    try:
        data = {
            "topic": "grammar",
            "difficulty": "medium",
            "num_questions": 3
        }
        response = requests.post(f"{BASE_URL}/api/nlp/generate-quiz", json=data)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Topic: {result.get('topic')}")
        print(f"Questions Generated: {len(result.get('questions', []))}")
        if result.get('questions'):
            print(f"First Question: {result['questions'][0]['question']}")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    print("=" * 60)
    print("NLP API Test Suite")
    print("=" * 60)
    print("\nMake sure the backend is running!")
    print("Command: python backend/main.py")
    print()
    input("Press Enter to start tests...")
    
    results = []
    
    # Test 1
    results.append(("Health Check", test_health()))
    time.sleep(1)
    
    # Test 2
    results.append(("Conversation Analysis", test_analyze()))
    time.sleep(1)
    
    # Test 3
    results.append(("Quiz Generation", test_quiz()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! NLP system is working perfectly!")
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
