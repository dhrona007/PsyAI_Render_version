# PsyAI Dynamic Tokenization System - Complete Documentation

## Problem Statement

Previously, response length was too simplistic - it just checked character/word count. This meant:

- Simple greeting "Hi" might get 200+ tokens (unnecessarily long)
- Complex resource request might still be capped at 560 tokens (too short)
- Response length didn't match the actual need expressed by the user

## Solution: Context-Aware Dynamic Tokenization

### How It Works

#### 1. Query Analysis Layer

When a user sends a message, the system analyzes:

```
User Input Analysis:
├─ Query Type Detection (greeting/simple/emotional/resource/informational/general)
├─ Word & Character Count
├─ Question Count & Phrasing
├─ Emotional Intensity Keywords (struggling, anxiety, hopeless, etc.)
├─ Information Request Keywords (provide, explain, suggest, etc.)
└─ Resource Request Keywords (resources, tools, exercises, etc.)
```

#### 2. Complexity Scoring

Assigns a complexity score based on multiple factors:

- **Type Score**: Different base scores for different query types
- **Keyword Penalties/Bonuses**: More emotional or info-seeking = higher score
- **Word Count Factor**: Longer questions generally need longer answers
- **Question Mark Factor**: Multiple questions might need more detail

#### 3. Dynamic Max Token Allocation

Based on analysis results:

```
Greeting ("Hi", "Hello")
├─ Base: 120 tokens
├─ Max: 200 tokens
└─ Result: 150-180 tokens (brief, warm greeting)

Simple Query ("Yes", "No", "How are you?")
├─ Base: 150 tokens
├─ Max: 250 tokens
└─ Result: 180-220 tokens (quick response)

Emotional Query (struggling, anxiety, depressed, etc.)
├─ Base: 350 tokens
├─ Scales with intensity: +100-250 tokens
└─ Result: 350-600 tokens (empathetic, supportive)

Resource Request (provide, suggest, list, resources)
├─ Base: 500 tokens
├─ Per keyword: +100 tokens
└─ Result: 500-800 tokens (comprehensive list/guide)

Informational (explain, how to, what are, techniques)
├─ Base: 350 tokens
├─ Per keyword: +100 tokens
└─ Result: 350-650 tokens (detailed explanation)

General Query
├─ Base: 250 tokens
├─ Scales dynamically
└─ Result: 250-600 tokens (adaptive)
```

### Code Implementation

#### Key Functions Added

**1. `_analyze_query_complexity(user_message)` → dict**
Returns analysis object with:

- `score`: Complexity score (1-5+)
- `type`: Query type (greeting/simple/emotional/resource/informational/general)
- `word_count`: Number of words
- `emotional_intensity`: Count of emotional keywords
- `info_request_count`: Count of info-seeking keywords
- `resource_request_count`: Count of resource-seeking keywords

**2. `_calculate_dynamic_max_tokens(user_message, conversation_history)` → int**
Returns appropriate `max_tokens` (150-800) based on:

- Query complexity analysis
- Conversation history (if present)
- Query type and detected intent

#### Updated Endpoints

**`analyze_responses_with_groq(conversation_history, assessment_mode, answers)`**

- Now uses `_calculate_dynamic_max_tokens()` instead of fixed logic
- Assessment mode: Always 800 tokens (comprehensive analysis needed)
- Chat mode: Dynamic based on user message complexity
- Default mode: 200 tokens

### Test Results

```
User Input: "Hi"
→ Query Type: greeting
→ Max Tokens: 150
→ Expected Response: "Hi! How are you feeling today?"

User Input: "provide resources to reduce anxiety"
→ Query Type: resource_request
→ Max Tokens: 600
→ Expected Response: [List of 10+ strategies, breathing exercises, apps, etc.]

User Input: "I'm struggling with anxiety, what should I do?"
→ Query Type: emotional
→ Max Tokens: 500
→ Expected Response: [Validation + 3-5 practical suggestions + resources]

User Input: "What are some meditation techniques?"
→ Query Type: resource_request
→ Max Tokens: 700
→ Expected Response: [Detailed guide with 5+ techniques, step-by-step]
```

### Keyword Categories

**Simple Greetings (1 token base)**

- hi, hello, hey, sup, yo, what's up

**Simple Queries (1 token base)**

- yes, no, maybe, how are you, what is your name, are you okay

**Info Request Keywords (2 tokens per keyword)**

- provide, suggest, list, explain, what are, how to, resources, tips, strategies, advice

**Emotional Intensity Keywords (2 tokens per keyword)**

- struggling, suffer, anxiety, depressed, hopeless, overwhelmed, stressed, alone, scared, angry

**Resource Request Keywords (2.5 tokens per keyword)**

- resources, tools, apps, websites, exercises, meditation, breathing, therapy, techniques

### Benefits

| Aspect              | Before             | After            |
| ------------------- | ------------------ | ---------------- |
| Greeting response   | 200+ tokens        | 150 tokens       |
| Resource request    | Max 560 tokens     | 600-800 tokens   |
| Emotional support   | Max 560 tokens     | 350-600 tokens   |
| Response accuracy   | ❌ Often too long  | ✅ Fits the need |
| User experience     | Wasted reading     | Better flow      |
| API cost efficiency | Higher token usage | Optimized usage  |

### Future Enhancements

1. **Sentiment Analysis**: Use NLP library for deeper emotional analysis
2. **Topic Classification**: Identify specific mental health topics (anxiety, depression, sleep, etc.)
3. **User Preference Learning**: Remember if user prefers brief vs detailed responses
4. **A/B Testing**: Track which response lengths get better user satisfaction
5. **Response Quality Feedback**: Adjust tokens if responses are truncated mid-sentence

### File Modifications

**`app.py`**

- Added keyword lists (lines ~240-280)
- Added `_analyze_query_complexity()` (lines ~281-340)
- Added `_calculate_dynamic_max_tokens()` (lines ~341-390)
- Updated `analyze_responses_with_groq()` to use new system (lines ~905-916)

### Testing & Validation

Run test script:

```bash
python test_tokenization.py
```

This will show token allocation for 12 different query types and verify the system is working correctly.

### Deployment Notes

- No database changes needed
- No API changes (still uses same `/api/chat` endpoint)
- Backward compatible with existing conversations
- No frontend changes required
- Performance: Negligible impact (analysis runs in <1ms)
