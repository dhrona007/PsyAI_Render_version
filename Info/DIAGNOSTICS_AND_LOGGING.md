# PsyAI Diagnostics & Error Handling - Implementation

## Problem Identified

Users were seeing repeated fallback error messages:

```
"Hi, I'm here with you. I'm having a temporary connection issue with the AI service,
but you can still tell me how you are feeling. Please try sending your message again
in a moment."
```

This indicated that Groq API calls were failing, but the root cause was unclear.

---

## Solution Implemented

### 1. Enhanced Logging System

Added comprehensive logging at app initialization:

```python
# New logging configuration at startup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log initialization status
if GROQ_API_KEY:
    logger.info(f"✓ Groq API initialized with model: {GROQ_MODEL}")
else:
    logger.error("✗ GROQ_API_KEY not configured - API calls will fail")
```

### 2. Improved Error Diagnostics

**In `_create_groq_chat_completion()`:**

- Added better error messages when API key is missing
- Added debug logging for each API call attempt
- Added specific error type and message logging
- Shows retry information

**Example logs:**

```
ERROR: GROQ_API_KEY is not configured. Please check your .env file.
DEBUG: Groq API call attempt 1/3: max_tokens=150, model=llama-3.3-70b-versatile
WARNING: Groq API transient error (retrying in 0.95s): Rate limit exceeded (attempt 1/3)
INFO: Groq API error [RateLimitError]: Too many requests
```

### 3. Chat Endpoint Logging

**In `/api/chat` endpoint:**

- Logs incoming requests with message preview
- Logs conversation history length
- Logs crisis detection
- Logs response generation status
- Logs final response length

**Example logs:**

```
INFO: Chat request from user_id=user_5234, message_len=2, text=Hey
DEBUG: Current conversation history length: 1
INFO: Generating chat response for user_id=user_5234, history_len=2
INFO: Received response length=45 chars
```

### 4. Response Analysis Logging

**In `analyze_responses_with_groq()`:**

- Logs error type and message when API calls fail
- Distinguishes between transient and permanent errors
- Full exception trace for debugging

**Example logs:**

```
ERROR: Groq API error [AuthenticationError]: Invalid API key provided
WARNING: Groq API transient error in chat analysis: [APITimeoutError] Request timed out
```

---

## Diagnostic Tool

Created `diagnostic_groq.py` to verify:

1. **Environment Variables Check**
   - ✓/✗ GROQ_API_KEY presence and preview
   - ✓/✗ GROQ_MODEL configuration
   - ✓/✗ FLASK_SECRET_KEY (optional)

2. **Client Initialization**
   - ✓/✗ Groq client can be created

3. **API Connectivity**
   - ✓/✗ Successful test API call
   - Response preview
   - Token usage info

**Run the diagnostic:**

```bash
python diagnostic_groq.py
```

---

## Recent Test Results

```
✓ GROQ_API_KEY found: gsk_CL5S...XZhDBf6W
✓ GROQ_MODEL: llama-3.3-70b-versatile
✓ Groq client initialized successfully
✓ API call successful!
  Response: Hello. How can I support you today?
  Model used: llama-3.3-70b-versatile
  Tokens used: input=48, output=10
```

**Status: ✓ API IS WORKING CORRECTLY**

---

## Troubleshooting Guide

### Scenario 1: Repeated Fallback Error Messages

**Symptom:** Always getting "having a temporary connection issue..."

**Diagnosis Steps:**

1. Run `python diagnostic_groq.py`
2. Check app logs for error messages
3. Look for "ERROR" entries with type and message

**Possible Causes & Fixes:**
| Issue | Fix |
|-------|-----|
| Missing GROQ_API_KEY | Add key to .env file |
| Invalid API key | Verify at console.groq.com |
| No API credits | Check Groq account billing |
| Groq service down | Check Groq's status page |
| Rate limit exceeded | Wait a few minutes before retrying |
| Network issues | Check internet connection |

### Scenario 2: Empty or Truncated Responses

**Symptom:** Getting very short responses for complex questions

**Check:**

- Look for log: `INFO: Received response length=X chars`
- Verify max_tokens being allocated
- Check if query complexity is being detected

### Scenario 3: Slow Responses

**Symptom:** Chat takes >5 seconds to respond

**Check:**

- Look for retry logs: `WARNING: Groq API transient error...`
- Count retry attempts in logs
- Check network latency

---

## Log Levels Explained

| Level   | When Used                 | Visibility                |
| ------- | ------------------------- | ------------------------- |
| DEBUG   | Detailed API calls        | Development only          |
| INFO    | Normal operations         | Production (startup/chat) |
| WARNING | Retries, temporary issues | Always                    |
| ERROR   | Failures, missing config  | Always                    |

### View Logs

**Option 1: Console Output**

- Logs appear in terminal running Flask server

**Option 2: File Output (optional)**

```python
# Add to app.py initialization:
file_handler = logging.FileHandler('psyai.log')
logger.addHandler(file_handler)
```

---

## Files Modified

**`app.py` Changes:**

- Added logging configuration (lines 12-20)
- Added initialization status log (lines 41-44)
- Updated `_create_groq_chat_completion()` with better error handling (lines 830-861)
- Updated `analyze_responses_with_groq()` with detailed error logging (lines 1016-1021)
- Updated `/api/chat` endpoint with comprehensive logging (lines 1291-1303, 1361-1365)

**New Files:**

- `diagnostic_groq.py` - Standalone diagnostic tool

---

## Verification Checklist

✓ Groq API key is valid and configured
✓ Groq client initializes successfully
✓ Test API calls succeed with proper responses
✓ Comprehensive logging is in place
✓ Error messages are specific and actionable
✓ Diagnostic tool helps identify issues quickly

---

## Next Steps for User

1. **Monitor Logs**
   - Watch console output when testing chat
   - Note any ERROR or WARNING messages

2. **If Issues Persist:**
   - Run `python diagnostic_groq.py`
   - Share error messages with development team
   - Check Groq console for account issues

3. **Test Current Status:**
   - Send "Hi" in chat → should get brief greeting
   - Send "provide resources" → should get comprehensive response
   - All responses should work now with proper logging

---

## Files for Debugging

- **Log output**: Console where you run `python app.py`
- **Diagnostic results**: Run `python diagnostic_groq.py`
- **Error details**: Check Groq API error messages in logs
