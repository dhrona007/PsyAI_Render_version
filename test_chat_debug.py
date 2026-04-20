#!/usr/bin/env python3
"""
Test chat endpoint with detailed logging to identify the exact error.
"""

import sys
import logging
import json
from io import StringIO

# Configure logging to capture everything
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Import after logging is configured
from app import (
    analyze_responses_with_groq,
    _calculate_dynamic_max_tokens,
    _analyze_query_complexity,
    get_user_id,
)

print("=" * 80)
print("TESTING CHAT ENDPOINT WITH DETAILED LOGGING")
print("=" * 80)

# Test 1: Simple greeting
print("\n[TEST 1] Testing simple greeting: 'Hey'")
print("-" * 80)

user_message = "Hey"
conversation_history = []

try:
    print(f"Input: '{user_message}'")
    print(f"Conversation history: {conversation_history}")

    # Check query complexity
    complexity = _analyze_query_complexity(user_message)
    print(f"\nQuery complexity analysis:")
    print(json.dumps(complexity, indent=2))

    # Check token calculation
    max_tokens = _calculate_dynamic_max_tokens(user_message, conversation_history)
    print(f"\nCalculated max_tokens: {max_tokens}")

    # Call the chat function
    print("\nCalling analyze_responses_with_groq()...")
    response = analyze_responses_with_groq(conversation_history)

    print(f"\n✓ SUCCESS!")
    print(f"Response ({len(response)} chars):")
    print(f"  {response[:200]}...")

except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}: {str(e)}")
    import traceback

    traceback.print_exc()

# Test 2: Check building conversation history
print("\n\n[TEST 2] Testing with conversation history")
print("-" * 80)

conversation_history = [
    {"role": "user", "content": "Hey"},
    {"role": "assistant", "content": "Hi there! How can I help?"},
]

user_message = "I'm struggling with anxiety"

try:
    print(f"Input: '{user_message}'")
    print(f"Conversation history length: {len(conversation_history)}")

    complexity = _analyze_query_complexity(user_message)
    print(f"\nQuery complexity type: {complexity['type']}")
    print(f"Emotional intensity: {complexity['emotional_intensity']}")

    max_tokens = _calculate_dynamic_max_tokens(user_message, conversation_history)
    print(f"Calculated max_tokens: {max_tokens}")

    print("\nCalling analyze_responses_with_groq()...")
    response = analyze_responses_with_groq(conversation_history)

    print(f"\n✓ SUCCESS!")
    print(f"Response ({len(response)} chars):")
    print(f"  {response[:200]}...")

except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}: {str(e)}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 80)
print("DEBUG TEST COMPLETE")
print("=" * 80)
