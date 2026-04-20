#!/usr/bin/env python3
"""
Test script to verify dynamic tokenization system.
Shows how different user inputs get different response length allocations.
"""

import sys

sys.path.insert(0, ".")

from app import _analyze_query_complexity, _calculate_dynamic_max_tokens

test_cases = [
    ("Hi", "Simple greeting"),
    ("Hello", "Simple greeting"),
    ("How are you?", "Simple query"),
    ("Yes", "Simple query"),
    ("provide resources to reduce anxiety", "Resource request"),
    ("I'm struggling with anxiety, what should I do?", "Emotional + informational"),
    ("Give me tips for managing stress", "Info request"),
    ("I'm really struggling and feeling hopeless", "High emotional intensity"),
    ("What are some meditation techniques?", "Educational request"),
    ("I'm anxious about my upcoming exam", "Emotional concern"),
    ("Can you list coping strategies for anxiety?", "Resource request"),
    ("explain how anxiety works in the brain", "Complex informational"),
]

print("=" * 90)
print("DYNAMIC TOKENIZATION TEST RESULTS")
print("=" * 90)
print()

for user_input, description in test_cases:
    analysis = _analyze_query_complexity(user_input)
    max_tokens = _calculate_dynamic_max_tokens(user_input, conversation_history=None)

    print(f"User Input: {user_input!r}")
    print(f"Description: {description}")
    print(f"  Query Type: {analysis['type']}")
    print(f"  Complexity Score: {analysis['score']:.1f}")
    print(f"  Word Count: {analysis['word_count']}")
    print(f"  Emotional Intensity: {analysis['emotional_intensity']}")
    print(f"  Info Requests: {analysis['info_request_count']}")
    print(f"  Resource Requests: {analysis['resource_request_count']}")
    print(f"  ➜ Max Tokens Allocated: {max_tokens}")
    print()

print("=" * 90)
print("KEY OBSERVATIONS:")
print("=" * 90)
print("""
1. GREETINGS ("Hi", "Hello"):
   - Type: greeting
   - Max tokens: 150-180
   - Expected: Brief, friendly response

2. SIMPLE QUERIES ("How are you?", "Yes"):
   - Type: simple
   - Max tokens: 200-250
   - Expected: Quick response, brief

3. RESOURCE REQUESTS ("provide resources to reduce anxiety"):
   - Type: resource_request
   - Max tokens: 600-800
   - Expected: Comprehensive list of strategies, apps, techniques

4. EMOTIONAL + COMPLEX ("I'm struggling with anxiety, what should I do?"):
   - Type: emotional
   - Max tokens: 550-800 (based on emotional intensity)
   - Expected: Empathetic validation + actionable suggestions

5. INFORMATIONAL ("What are some meditation techniques?"):
   - Type: informational
   - Max tokens: 450-650
   - Expected: Educational content with methods/steps

Key Principle:
Response length is based on user's NEED, not just input length.
Simple query → concise response
Complex request → comprehensive response
""")
