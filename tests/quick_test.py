"""
Quick API Test - Simple verification that API is working
"""

import requests
import sys

# Set encoding for Windows console if needed
if sys.platform == 'win32':
    import os
    os.system('chcp 65001 > nul')

API_BASE = "http://127.0.0.1:8000"

print("\n" + "=" * 70)
print("  QUICK API TEST")
print("=" * 70)

try:
    # 1. Health check
    print("\n[ ] Testing health endpoint...")
    r = requests.get(f"{API_BASE}/api/health")
    if r.status_code == 200:
        print(f"  [OK] API is healthy: {r.json()['status']}")
    else:
        print(f"  [FAIL] Health check failed: {r.status_code}")
        print(f"  Response: {r.text}")

    # 2. Get recommendations
    print("\n[ ] Getting recommendations for user_0...")
    r = requests.get(f"{API_BASE}/api/recommendations/user_0")
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] User: {data['user_id']}")
        print(f"  [OK] Total recommendations: {data['total_count']}")
        if data['recommendations']:
            print(f"\n  Top recommendation:")
            rec = data['recommendations'][0]
            print(f"    Course: {rec['title']}")
            print(f"    Score: {rec['score']:.3f}")
            print(f"    Reason: {rec['why_recommended']}")
        else:
            print("  [WARN] No recommendations returned (catalog might be empty or all dismissed)")
    else:
        print(f"  [FAIL] Failed to get recommendations: {r.status_code}")
        print(f"  Response: {r.text}")

    # 3. Get statistics
    print("\n[ ] Getting statistics...")
    r = requests.get(f"{API_BASE}/api/recommendations/user_0/stats")
    if r.status_code == 200:
        stats = r.json()
        print(f"  [OK] Total: {stats['total_recommendations']}")
        print(f"  [OK] Active: {stats['active_recommendations']}")
        print(f"  [OK] Dismissed: {stats['dismissed_count']}")
    else:
        print(f"  [FAIL] Failed to get statistics: {r.status_code}")
        print(f"  Response: {r.text}")

    print("\n" + "=" * 70)
    print("  TEST SUMMARY COMPLETE")
    print("=" * 70)
    print("\n  Next steps:")
    print("  1. Open http://127.0.0.1:8000/api/docs for interactive testing")
    print("  2. Try different users: user_1, user_2, ..., user_99")
    print("  3. Integrate with React component\n")

except requests.exceptions.ConnectionError:
    print("\n  [ERROR] Cannot connect to API server!")
    print("  Make sure the server is running.")
except Exception as e:
    print(f"\n  [ERROR] {e}\n")
