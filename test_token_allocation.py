#!/usr/bin/env python3
"""
Test updated tokenization and response completion.
"""

import sys
from app import _calculate_dynamic_max_tokens, _analyze_query_complexity

print("=" * 80)
print("TESTING UPDATED TOKEN ALLOCATION FOR COMPLETE RESPONSES")
print("=" * 80)

# Test cases with different query types
test_cases = [
    ("Hey", "greeting"),
    ("How are you doing?", "simple"),
    ("I'm feeling really anxious and overwhelmed", "emotional"),
    ("Can you provide some resources for dealing with depression?", "resource_request"),
    ("What are some techniques for managing stress?", "informational"),
    (
        "I'm struggling with anxiety and need help understanding my symptoms",
        "emotional",
    ),
]

print("\nToken Allocation Results:")
print("-" * 50)

for message, expected_type in test_cases:
    analysis = _analyze_query_complexity(message)
    tokens = _calculate_dynamic_max_tokens(message)

    print(f"Query: '{message[:40]}...'")
    print(f"  Type: {analysis['type']} (expected: {expected_type})")
    print(f"  Complexity Score: {analysis['score']}")
    print(f"  Allocated Tokens: {tokens}")
    print(f"  Emotional Intensity: {analysis['emotional_intensity']}")
    print(f"  Word Count: {analysis['word_count']}")
    print()

print("=" * 80)
print("TOKEN ALLOCATION SUMMARY")
print("=" * 80)
print("Previous limits: greeting=200, simple=250, emotional=600, resource=800")
print("Updated limits:  greeting=350, simple=400, emotional=900, resource=1200")
print("Overall max limit increased from 800 to 1200 tokens")
print("Minimum tokens increased from 150 to 200")
print()
print("This should provide much more room for complete responses!")
print("=" * 80)
