"""
Quick API Test Script
Tests all endpoints of the Recommendation API
"""

import requests
import json
from typing import Dict, Any

API_BASE = "http://127.0.0.1:8000"

def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_response(response: requests.Response):
    print(f"Status Code: {response.status_code}")
    if response.status_code < 400:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Error: {response.text}")

def test_health():
    print_section("1. Health Check")
    try:
        response = requests.get(f"{API_BASE}/api/health")
        print_response(response)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_recommendations(user_id: str = "user_0"):
    print_section(f"2. Get Recommendations for {user_id}")
    try:
        response = requests.get(f"{API_BASE}/api/recommendations/{user_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status Code: {response.status_code}")
            print(f"✅ User ID: {data['user_id']}")
            print(f"✅ Total Recommendations: {data['total_count']}")
            print(f"✅ Generated At: {data['generated_at']}")
            print(f"✅ Next Update: {data['next_update']}")
            print(f"\nFirst 3 Recommendations:")
            for i, rec in enumerate(data['recommendations'][:3], 1):
                print(f"\n   {i}. {rec['title']}")
                print(f"      Score: {rec['score']:.3f}")
                print(f"      Difficulty: {rec['difficulty']}")
                print(f"      Why: {rec['why_recommended'][:80]}...")
            return True
        else:
            print_response(response)
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_dismiss_recommendation(user_id: str = "user_0", course_id: str = "course_0"):
    print_section(f"3. Dismiss Recommendation")
    try:
        payload = {
            "course_id": course_id,
            "reason": "Not interested - Testing dismissal"
        }
        response = requests.post(
            f"{API_BASE}/api/recommendations/{user_id}/dismiss",
            json=payload
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status Code: {response.status_code}")
            print(f"✅ Success: {data['success']}")
            print(f"✅ Message: {data['message']}")
            print(f"✅ Dismissed Course: {data['dismissed_course_id']}")
            print(f"✅ Remaining Count: {data['remaining_count']}")
            return True
        else:
            print_response(response)
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_refresh_recommendations(user_id: str = "user_0"):
    print_section(f"4. Refresh Recommendations")
    try:
        payload = {"reason": "Testing refresh functionality"}
        response = requests.post(
            f"{API_BASE}/api/recommendations/{user_id}/refresh",
            json=payload
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status Code: {response.status_code}")
            print(f"✅ Success: {data['success']}")
            print(f"✅ Message: {data['message']}")
            print(f"✅ New Count: {data['new_count']}")
            print(f"✅ Refreshed At: {data['refreshed_at']}")
            return True
        else:
            print_response(response)
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_statistics(user_id: str = "user_0"):
    print_section(f"5. Get Statistics")
    try:
        response = requests.get(f"{API_BASE}/api/recommendations/{user_id}/stats")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status Code: {response.status_code}")
            print(f"✅ User ID: {data['user_id']}")
            print(f"✅ Total Recommendations: {data['total_recommendations']}")
            print(f"✅ Active Recommendations: {data['active_recommendations']}")
            print(f"✅ Dismissed Count: {data['dismissed_count']}")
            print(f"✅ Last Updated: {data.get('last_updated', 'None')}")
            print(f"✅ Next Update: {data.get('next_update', 'None')}")
            return True
        else:
            print_response(response)
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("\n" + "🎯" * 40)
    print("  TAMKEEN RECOMMENDATION API - TEST SUITE")
    print("🎯" * 40)
    print(f"\nAPI Base URL: {API_BASE}")
    print(f"Testing all endpoints...\n")
    
    results = []
    
    # Test all endpoints
    results.append(("Health Check", test_health()))
    results.append(("Get Recommendations", test_get_recommendations()))
    results.append(("Get Statistics", test_get_statistics()))
    results.append(("Dismiss Recommendation", test_dismiss_recommendation()))
    results.append(("Refresh Recommendations", test_refresh_recommendations()))
    results.append(("Get Statistics (after changes)", test_get_statistics()))
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status:12} - {name}")
    
    print(f"\n{passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("\nYour API is working perfectly!")
        print("You can now:")
        print("1. Open http://127.0.0.1:8000/api/docs for interactive testing")
        print("2. Integrate the React component")
        print("3. Deploy to production")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
