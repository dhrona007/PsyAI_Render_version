#!/usr/bin/env python3
"""
Test the Flask chat endpoint directly with verbose logging.
"""

import sys
import json
import logging
from app import app

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

print("=" * 80)
print("TESTING FLASK CHAT ENDPOINT")
print("=" * 80)

# Create test client
with app.test_client() as client:
    print("\n[TEST] Sending POST /api/chat with message 'Hey'")
    print("-" * 80)

    response = client.post(
        "/api/chat",
        json={"message": "Hey"},
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")

    try:
        data = response.get_json()
        print(f"\nResponse JSON:")
        print(json.dumps(data, indent=2))

        if "reply" in data:
            print(f"\n✓ Reply received ({len(data['reply'])} chars):")
            print(f"  {data['reply'][:200]}...")
        elif "error" in data:
            print(f"\n✗ Error: {data['error']}")
        else:
            print(f"\n? Unexpected response format")
            print(data)
    except Exception as e:
        print(f"\n✗ Failed to parse response: {e}")
        print(f"Raw content: {response.data}")

print("\n" + "=" * 80)
print("ENDPOINT TEST COMPLETE")
print("=" * 80)
