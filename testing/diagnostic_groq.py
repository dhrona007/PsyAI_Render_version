#!/usr/bin/env python3
"""
Diagnostic script to test Groq API connection and configuration.
Run this to debug why chat responses are failing.
"""

import sys
import os
from dotenv import load_dotenv
from groq import Groq

print("=" * 80)
print("PSYAI GROQ API DIAGNOSTIC TOOL")
print("=" * 80)
print()

# Load environment variables
load_dotenv()

print("1. ENVIRONMENT VARIABLES")
print("-" * 80)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

if GROQ_API_KEY:
    key_preview = (
        GROQ_API_KEY[:8] + "..." + GROQ_API_KEY[-8:]
        if len(GROQ_API_KEY) > 16
        else "***"
    )
    print(f"✓ GROQ_API_KEY found: {key_preview}")
else:
    print("✗ GROQ_API_KEY NOT FOUND - this is the problem!")
    print("  Please add GROQ_API_KEY to your .env file")
    sys.exit(1)

print(f"✓ GROQ_MODEL: {GROQ_MODEL}")

if FLASK_SECRET_KEY:
    print(f"✓ FLASK_SECRET_KEY found")
else:
    print("⚠ FLASK_SECRET_KEY not found (optional, using default)")

print()
print("2. GROQ CLIENT INITIALIZATION")
print("-" * 80)
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("✓ Groq client initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize Groq client: {e}")
    sys.exit(1)

print()
print("3. TEST API CALL")
print("-" * 80)
try:
    print("Sending test message to Groq API...")
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful mental health assistant. Keep responses brief.",
            },
            {"role": "user", "content": "Hi"},
        ],
        max_tokens=150,
        temperature=0.7,
    )

    ai_response = response.choices[0].message.content
    print(f"✓ API call successful!")
    print(
        f"  Response: {ai_response[:100]}..."
        if len(ai_response) > 100
        else f"  Response: {ai_response}"
    )
    print(f"  Model used: {response.model}")
    print(
        f"  Tokens used: input={response.usage.prompt_tokens}, output={response.usage.completion_tokens}"
    )

except Exception as e:
    print(f"✗ API call failed: {type(e).__name__}: {e}")
    print()
    print("TROUBLESHOOTING:")
    print("1. Check if your API key is valid at console.groq.com")
    print("2. Check if you have API credits available")
    print("3. Check your internet connection")
    print("4. Try checking Groq's status page for service issues")
    sys.exit(1)

print()
print("=" * 80)
print("✓ ALL DIAGNOSTICS PASSED - Groq API is working correctly!")
print("=" * 80)
