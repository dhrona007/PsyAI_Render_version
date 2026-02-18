from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import os
from dotenv import load_dotenv
import json
import random
from together import Together
from datetime import datetime, timedelta, timezone
from flask_socketio import SocketIO, emit
import logging

# Load environment variables
load_dotenv()

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static",
)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")
CORS(app)  # Allow all origins for all routes

socketio = SocketIO(app, cors_allowed_origins="*")  # Enable CORS for SocketIO

# Initialize Together client
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
client = Together(api_key=TOGETHER_API_KEY)

###############################################################################
# In-memory and file-backed state
###############################################################################

# Dictionary to store user chat history (in-memory for current session)
user_chat_history = {}

# Dictionary to store user assessment state (in-memory for current session)
user_assessment_state = {}

# Load mental health questions from JSON file
mental_health_questions = []

# Base directory for simple JSON storage of mood data per user
DATA_DIR = os.path.join("static", "data")
MOOD_DIR = os.path.join(DATA_DIR, "mood")

os.makedirs(MOOD_DIR, exist_ok=True)


def load_mental_health_questions():
    global mental_health_questions
    try:
        with open(
            os.path.join(DATA_DIR, "assessment_questions.json"),
            "r",
            encoding="utf-8",
        ) as f:
            mental_health_questions = json.load(f)
    except Exception as e:
        logging.error(f"Error loading assessment questions: {e}")
        mental_health_questions = []


load_mental_health_questions()


def get_user_id():
    """
    Helper to ensure a stable user identifier backed by the Flask session.
    """
    user_id = session.get("user_id")
    if not user_id:
        user_id = f"user_{random.randint(1000, 9999)}"
        session["user_id"] = user_id
    return user_id


# -----------------------------------------------------------------------------
# Simple crisis / safety detection
# -----------------------------------------------------------------------------

CRISIS_KEYWORDS = [
    "kill myself",
    "end my life",
    "no right to live",
    "no right to be alive",
    "suicide",
    "suicidal",
    "want to die",
    "dont want to live",
    "don't want to live",
    "hurt myself",
    "self harm",
    "self-harm",
    "cut myself",
]


def detect_crisis(user_text: str) -> dict:
    """
    Very simple phrase-based crisis detector.
    Returns a dict with:
      - risk_level: "none" | "high"
      - matched_phrases: list of matched keyword strings

    This is intentionally simple so it can be replaced later with a
    more advanced classifier if needed.
    """
    if not user_text:
        return {"risk_level": "none", "matched_phrases": []}

    text = user_text.lower()
    matched = [kw for kw in CRISIS_KEYWORDS if kw in text]

    if matched:
        return {"risk_level": "high", "matched_phrases": matched}

    return {"risk_level": "none", "matched_phrases": []}


def _user_mood_file(user_id):
    """
    Path to the JSON file that stores mood-related data for a user.
    Structure:
        {
          "entries": [...],
          "triggers": [...],
          "coping_plans": [...],
          "reminders": [...]
        }
    """
    safe_user_id = str(user_id).replace(os.sep, "_")
    return os.path.join(MOOD_DIR, f"{safe_user_id}.json")


def _load_user_mood_data(user_id):
    path = _user_mood_file(user_id)
    if not os.path.exists(path):
        return {
            "entries": [],
            "triggers": [],
            "coping_plans": [],
            "reminders": [],
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure all expected keys exist
        data.setdefault("entries", [])
        data.setdefault("triggers", [])
        data.setdefault("coping_plans", [])
        data.setdefault("reminders", [])
        return data
    except Exception as e:
        logging.error(f"Failed to load mood data for {user_id}: {e}")
        return {
            "entries": [],
            "triggers": [],
            "coping_plans": [],
            "reminders": [],
        }


def _save_user_mood_data(user_id, data):
    path = _user_mood_file(user_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Failed to save mood data for {user_id}: {e}")


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _parse_iso_datetime(value):
    if not value:
        return None
    try:
        normalized = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except Exception:
        return None


def _normalize_text(text):
    return str(text or "").strip().lower()


def _count_cue_matches(text, cue_list):
    return sum(1 for cue in cue_list if cue in text)


def _sanitize_text(value):
    text = str(value or "")
    replacements = {
        "Ã¢â‚¬â„¢": "'",
        "Äâ‚¬â„¢": "'",
        "â€™": "'",
        "â€˜": "'",
        "Ã¢â‚¬â€œ": "-",
        "â€“": "-",
        "â€”": "-",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


MOOD_POSITIVE_CUES = [
    "calm",
    "better",
    "grateful",
    "happy",
    "hopeful",
    "supported",
    "relieved",
    "okay",
    "good",
    "productive",
    "confident",
]

MOOD_NEGATIVE_CUES = [
    "sad",
    "down",
    "depressed",
    "hopeless",
    "overwhelmed",
    "stressed",
    "stress",
    "angry",
    "alone",
    "lonely",
    "worthless",
    "upset",
    "exhausted",
    "burned out",
    "numb",
    "crying",
]

MOOD_ANXIETY_CUES = [
    "anxious",
    "anxiety",
    "worried",
    "panic",
    "on edge",
    "restless",
    "fear",
    "afraid",
    "uneasy",
    "racing thoughts",
]

MOOD_LOW_ENERGY_CUES = [
    "tired",
    "fatigued",
    "drained",
    "low energy",
    "no energy",
    "sluggish",
]

MOOD_HIGH_ENERGY_CUES = [
    "energetic",
    "motivated",
    "active",
    "excited",
    "focused",
    "ready",
]

ASSESSMENT_ANSWER_SEVERITY = {
    "not at all": 0.0,
    "never": 0.0,
    "rarely": 0.5,
    "a little": 1.0,
    "several days": 1.0,
    "sometimes": 1.0,
    "moderately": 2.0,
    "more than half the days": 2.5,
    "often": 2.5,
    "very much": 3.0,
    "nearly every day": 3.5,
    "extremely": 4.0,
    "yes": 2.0,
    "no": 0.0,
}

ASSESSMENT_SAFETY_CUES = [
    "better off dead",
    "hurting yourself",
    "killing yourself",
    "end your life",
    "suicide",
    "self-harm",
]


def _build_auto_mood_entry_from_text(text, source):
    normalized = _normalize_text(text)
    if not normalized:
        return None

    positive_hits = _count_cue_matches(normalized, MOOD_POSITIVE_CUES)
    negative_hits = _count_cue_matches(normalized, MOOD_NEGATIVE_CUES)
    anxiety_hits = _count_cue_matches(normalized, MOOD_ANXIETY_CUES)
    low_energy_hits = _count_cue_matches(normalized, MOOD_LOW_ENERGY_CUES)
    high_energy_hits = _count_cue_matches(normalized, MOOD_HIGH_ENERGY_CUES)

    sentiment_delta = positive_hits - negative_hits
    mood_score = round(
        _clamp(
            5.0
            + (sentiment_delta * 0.8)
            - (anxiety_hits * 0.4)
            - (low_energy_hits * 0.25)
            + (high_energy_hits * 0.2),
            1.0,
            10.0,
        )
    )
    energy = round(
        _clamp(
            5.0 + (high_energy_hits * 1.2) - (low_energy_hits * 1.2) - (negative_hits * 0.2),
            1.0,
            10.0,
        )
    )
    anxiety = round(
        _clamp(
            3.0
            + (anxiety_hits * 1.5)
            + (max(0, negative_hits - positive_hits) * 0.5)
            - (positive_hits * 0.3),
            1.0,
            10.0,
        )
    )

    tags = []
    if anxiety_hits > 0:
        tags.append("anxiety")
    if negative_hits > positive_hits:
        tags.append("stress")
    if low_energy_hits > 0:
        tags.append("low-energy")
    if positive_hits > negative_hits:
        tags.append("positive")
    if not tags:
        tags.append("check-in")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "mood_score": mood_score,
        "energy": energy,
        "anxiety": anxiety,
        "tags": tags,
        "journal_text": str(text).strip()[:500],
        "source": source,
        "tracking_mode": "auto",
    }


def _extract_assessment_answer_value(answer_item):
    if isinstance(answer_item, dict):
        return _normalize_text(answer_item.get("answer", ""))
    return _normalize_text(answer_item)


def _extract_assessment_question_text(answer_item):
    if isinstance(answer_item, dict):
        return _normalize_text(answer_item.get("question", ""))
    return ""


def _assessment_answer_to_severity(answer_value):
    if not answer_value:
        return None
    if answer_value in ASSESSMENT_ANSWER_SEVERITY:
        return ASSESSMENT_ANSWER_SEVERITY[answer_value]

    # Fallback: approximate by digits if any score-like text was sent.
    try:
        numeric = float(answer_value)
        return _clamp(numeric, 0.0, 4.0)
    except Exception:
        return None


def _build_assessment_mood_entry(answer_items, assessment_type="general"):
    if not isinstance(answer_items, list) or not answer_items:
        return None

    severities = []
    high_risk_answered = False

    for item in answer_items:
        answer_value = _extract_assessment_answer_value(item)
        if not answer_value or answer_value == "no response":
            continue

        severity = _assessment_answer_to_severity(answer_value)
        if severity is not None:
            severities.append(severity)

        question_text = _extract_assessment_question_text(item)
        if any(cue in question_text for cue in ASSESSMENT_SAFETY_CUES) and severity and severity >= 2.0:
            high_risk_answered = True

    if not severities:
        return None

    avg_severity = sum(severities) / len(severities)
    mood_score = round(_clamp(9.0 - (avg_severity * 2.0), 1.0, 10.0))
    energy = round(_clamp(8.0 - (avg_severity * 1.4), 1.0, 10.0))
    anxiety = round(_clamp(2.0 + (avg_severity * 2.1), 1.0, 10.0))

    tags = ["assessment", f"assessment-{assessment_type}"]
    if high_risk_answered:
        mood_score = min(mood_score, 3)
        anxiety = max(anxiety, 8)
        tags.append("safety-check")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "mood_score": mood_score,
        "energy": energy,
        "anxiety": anxiety,
        "tags": tags,
        "journal_text": (
            f"Auto-generated from {assessment_type} assessment "
            f"({len(severities)} answered prompts)"
        ),
        "source": f"assessment_{assessment_type}",
        "tracking_mode": "auto",
    }


def _can_append_auto_entry(entries, source, min_interval_minutes):
    if not entries:
        return True
    now = datetime.utcnow()
    minimum_delta = timedelta(minutes=min_interval_minutes)
    for entry in reversed(entries):
        if (entry.get("source") or "manual") != source:
            continue
        previous_ts = _parse_iso_datetime(entry.get("timestamp"))
        if previous_ts is None:
            return True
        return (now - previous_ts) >= minimum_delta
    return True


def _append_mood_entry(user_id, entry):
    user_data = _load_user_mood_data(user_id)
    user_data["entries"].append(entry)
    _save_user_mood_data(user_id, user_data)
    return user_data


def _append_auto_mood_entry(user_id, entry, min_interval_minutes=10, force=False):
    if not entry:
        return False
    user_data = _load_user_mood_data(user_id)
    source = entry.get("source") or "auto"
    if not force and not _can_append_auto_entry(
        user_data.get("entries", []), source, min_interval_minutes
    ):
        return False
    user_data["entries"].append(entry)
    _save_user_mood_data(user_id, user_data)
    return True


def analyze_responses_with_together(
    conversation_history, assessment_mode=False, answers=None
):
    try:
        system_message = {
            "role": "system",
            "content": """You are MentaLyze, an AI-powered mental health chatbot dedicated to providing empathetic, supportive, and personalized emotional assistance 24/7. Your primary goal is to help users feel heard, understood, and guided toward improving their mental well-being in a safe and respectful manner.

Guidelines:

1. **Empathy and Compassion**  
- Always respond with warmth, kindness, and understanding.  
- Validate the user's feelings and experiences without judgment.  
- Use comforting language that encourages openness and trust.

2. **User Safety and Crisis Management**  
- If the user expresses suicidal thoughts, self-harm intentions, or severe distress, respond with immediate empathy and encourage them to seek professional help.  
- Provide emergency resources (hotline numbers, crisis centers) where appropriate.  
- If the user triggers the emergency alert, confirm the action and reassure them that help is on the way.  
- Never provide medical diagnosis or prescribe treatment.

3. **Personalized Support and Guidance**  
- Use information from mood tracking and assessment responses to tailor advice and coping strategies.  
- Suggest evidence-based coping mechanisms such as mindfulness, breathing exercises, journaling, or seeking social support.  
- Encourage users to engage in positive habits and self-care routines.

4. **Mental Health Assessment**  
- When conducting assessments, ask questions clearly and respectfully.  
- Adapt questions based on user responses to explore areas of concern more deeply.  
- Summarize assessment results in an understandable, non-clinical way, highlighting strengths and areas for improvement.  
- Remind users that assessments are informational and do not replace professional evaluation.

5. **Privacy and Confidentiality**  
- Respect user privacy; do not share or store personal information beyond what is necessary for session continuity.  
- Inform users that conversations are confidential but not a substitute for professional counseling.

6. **Limitations and Transparency**  
- Clearly communicate that you are an AI assistant and not a licensed therapist or doctor.  
- Encourage users to seek professional help for serious or persistent mental health issues.  
- Avoid making promises or guarantees about outcomes.

7. **Tone and Style**  
- Maintain a calm, gentle, and encouraging tone.  
- Avoid technical jargon; use simple, clear language.  
- Be patient and allow users to express themselves fully.

8. **Emergency Situations**  
- If the user indicates immediate danger to self or others, urge them to call emergency services or a trusted person right away.  
- Provide contact information for local or national crisis helplines when available.  
- Do not attempt to handle emergencies alone; always direct users to human support.

9. **Inclusivity and Accessibility**  
- Use inclusive language that respects diverse backgrounds, identities, and experiences.  
- Be mindful of cultural differences in expressing and coping with mental health issues.

Summary:  
You are a compassionate, responsible AI mental health companion. Your responses should always prioritize the userâ€™s emotional safety, provide helpful support, and encourage professional care when necessary. Your role is to listen, support, guide, and empower users on their mental health journey.

Begin each conversation by warmly welcoming the user and inviting them to share how they are feeling today.""",
        }
        if assessment_mode and answers:
            # Build a comprehensive assessment analysis prompt
            answers_text = "\n".join(
                [
                    f"{i + 1}. {answer}"
                    for i, answer in enumerate(answers)
                    if answer and answer != "No response"
                ]
            )
            prompt = f"""Please provide a personalized mental health analysis based on these assessment responses:

{answers_text}

Based on these responses, please:
1. Summarize the overall mental and emotional well-being picture
2. Identify key patterns, themes, and areas of concern
3. Highlight areas of strength and resilience
4. Suggest 3-5 practical, evidence-based coping strategies they could try
5. Provide warm, empathetic encouragement and next steps
6. Remind them that this is an informational assessment, not a diagnosis, and they should seek professional help for persistent concerns"""
            messages = [system_message, {"role": "user", "content": prompt}]
        elif conversation_history:
            prompt = "Continue this conversation:\n" + "\n".join(
                [msg["content"] for msg in conversation_history]
            )
            messages = [system_message, {"role": "user", "content": prompt}]
        else:
            messages = [
                system_message,
                {"role": "user", "content": "Hello, how can I assist you today?"},
            ]

        # Call Together API for response
        response = client.chat.completions.create(
            model="mistralai/Mistral-Small-24B-Instruct-2501",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error in analyze_responses_with_together: {e}", exc_info=True)
        return "Sorry, I encountered an error processing your request."


def analyze_mood_history_with_together(mood_entries):
    """
    Use the Together API to generate an empathetic reflection over a list of
    mood entries. This is separate from the chat/assessment prompt so that we
    can give the model very specific instructions.

    mood_entries: list of dicts with keys such as:
      - timestamp
      - mood_score
      - energy / anxiety / tags / journal_text
    """
    if not mood_entries:
        return "I don't have any recent mood entries to analyze yet."

    try:
        system_message = {
            "role": "system",
            "content": (
                "You are MentaLyze, an empathetic mental health companion. "
                "You are analyzing a user's recent mood journal entries. "
                "Your goal is to gently highlight patterns, recurring themes, and "
                "small, practical suggestions the user might try. "
                "Use warm, validating language and avoid clinical diagnoses. "
                "Clearly remind the user that you are an AI assistant and not a "
                "therapist, and that your reflections are not medical advice."
            ),
        }

        # Build a concise but informative summary of entries for the model
        lines = []
        for e in mood_entries:
            ts = e.get("timestamp")
            mood = e.get("mood_score")
            energy = e.get("energy")
            anxiety = e.get("anxiety")
            tags = ", ".join(e.get("tags", []))
            journal = e.get("journal_text", "")
            line = f"- [{ts}] mood={mood}, energy={energy}, anxiety={anxiety}, tags=[{tags}]\n  note: {journal}"
            lines.append(line)

        user_content = (
            "Here are the user's recent mood entries:\n\n"
            + "\n".join(lines)
            + "\n\nPlease:\n"
            "- Summarize overall patterns in mood, energy, and anxiety.\n"
            "- Gently point out possible triggers or themes based on the text.\n"
            "- Offer 3â€“5 small, concrete self-care or coping ideas.\n"
            "- Keep the tone warm and encouraging, and avoid sounding clinical.\n"
            "- End with a reminder to reach out to a mental health professional "
            "for persistent or severe difficulties."
        )

        messages = [system_message, {"role": "user", "content": user_content}]

        response = client.chat.completions.create(
            model="mistralai/Mistral-Small-24B-Instruct-2501",
            messages=messages,
            max_tokens=600,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(
            f"Error in analyze_mood_history_with_together: {e}", exc_info=True
        )
        return (
            "Sorry, I had trouble analyzing your mood history. "
            "You can still review your entries yourself to notice patterns "
            "in what helps and what makes things harder."
        )


@app.before_request
def make_session_permanent():
    session.permanent = True


@app.route("/", methods=["GET"])
def serve_index():
    return send_from_directory(os.getcwd(), "index.html")


@app.route("/api/start_detailed_assessment", methods=["POST"])
def start_detailed_assessment():
    """
    Start a detailed assessment for the current session user.
    We always key state by the stable session user_id so that
    subsequent /api/chat calls can correctly detect assessment mode.
    """
    user_id = get_user_id()

    user_assessment_state[user_id] = {
        "current_question_index": 0,
        "answered_questions": set(),
        "assessment_history": [],
        # Maintain the exact order of questions asked so that we can
        # support a "Previous" button on the frontend.
        "question_order": [0],
    }

    return jsonify(
        {
            "reply": mental_health_questions[0]["question"]
            if mental_health_questions
            else "No questions available.",
            "status": "detailed_assessment",
        }
    )


@app.route("/api/start_general_assessment", methods=["POST"])
def start_general_assessment():
    """
    Start a general assessment for the current session user.
    Uses the same user_id as /api/chat so assessment state is detected.
    """
    user_id = get_user_id()

    user_assessment_state[user_id] = {
        "current_question_index": 0,
        "answered_questions": set(),
        "assessment_history": [],
        "question_order": [0],
    }

    return jsonify(
        {
            "reply": mental_health_questions[0]["question"]
            if mental_health_questions
            else "No questions available.",
            "status": "general_assessment",
        }
    )


def select_next_question(user_message, answered_questions):
    scores = {}
    for question_index, question in enumerate(mental_health_questions):
        if question_index not in answered_questions:
            if any(keyword in user_message.lower() for keyword in question["options"]):
                scores[question_index] = scores.get(question_index, 0) + 1

    if scores:
        next_question_index = max(scores, key=scores.get)
        return next_question_index
    return None


@app.route("/api/assessment_prev", methods=["POST"])
def assessment_prev():
    """
    Step back to the previous assessment question for the current user.
    This updates the server-side assessment state (current index,
    answered set, and history) so that the next answer is correctly
    associated with the question the user is viewing.
    """
    user_id = get_user_id()
    state = user_assessment_state.get(user_id)
    if not state:
        return jsonify({"error": "No active assessment"}), 400

    question_order = state.get("question_order") or []
    assessment_history = state.get("assessment_history") or []
    answered_questions = state.get("answered_questions") or set()

    # Can't go back if there is only the first question
    if len(question_order) <= 1:
        return jsonify({"error": "No previous question"}), 400

    # Remove the current question from the order and history
    last_index = question_order.pop()

    if assessment_history and assessment_history[-1]["question_index"] == last_index:
        assessment_history.pop()
        answered_questions.discard(last_index)

    # Set the new current index to the previous question
    current_index = question_order[-1]
    state["current_question_index"] = current_index
    state["question_order"] = question_order
    state["assessment_history"] = assessment_history
    state["answered_questions"] = answered_questions

    # Find any previously given answer for this question (if user answered it earlier)
    previous_answer = None
    for item in assessment_history:
        if item["question_index"] == current_index:
            previous_answer = item.get("answer")
            break

    return jsonify(
        {
            "reply": mental_health_questions[current_index]["question"],
            "status": "assessment_prev",
            "previous_answer": previous_answer,
        }
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Invalid request"}), 400
    user_message = data["message"]

    # Always use the helper so user_id is consistent across all endpoints
    user_id = get_user_id()

    logging.info(f"Chat request from user_id: {user_id} with message: {user_message}")

    # Detect potential crisis language in the latest user message
    crisis_info = detect_crisis(user_message)

    history = user_chat_history.get(user_id, [])
    logging.info(f"Current conversation history length: {len(history)}")
    history.append({"role": "user", "content": user_message})

    auto_source = "assessment_chat" if user_id in user_assessment_state else "chat"
    auto_mood_entry = _build_auto_mood_entry_from_text(user_message, source=auto_source)
    _append_auto_mood_entry(user_id, auto_mood_entry, min_interval_minutes=8)

    if user_id in user_assessment_state:
        assessment_state = user_assessment_state[user_id]
        current_question_index = assessment_state["current_question_index"]
        answered_questions = assessment_state["answered_questions"]
        assessment_history = assessment_state["assessment_history"]
        question_order = assessment_state.setdefault(
            "question_order", [current_question_index]
        )

        assessment_history.append(
            {
                "question_index": current_question_index,
                "question": mental_health_questions[current_question_index]["question"],
                "answer": user_message,
            }
        )

        answered_questions.add(current_question_index)

        next_question_index = select_next_question(user_message, answered_questions)

        if next_question_index is not None:
            assessment_state["current_question_index"] = next_question_index
            question_order.append(next_question_index)
            return jsonify(
                {
                    "reply": mental_health_questions[next_question_index]["question"],
                    "status": "assessment",
                    "crisis": crisis_info,
                }
            )
        else:
            analysis = analyze_responses_with_together(
                conversation_history=None,
                assessment_mode=True,
                answers=[q["answer"] for q in assessment_history],
            )
            del user_assessment_state[user_id]
            return jsonify(
                {
                    "reply": analysis,
                    "status": "analysis",
                    "crisis": crisis_info,
                }
            )
    else:
        ai_response = analyze_responses_with_together(history)
        history.append({"role": "assistant", "content": ai_response})
        user_chat_history[user_id] = history
        return jsonify(
            {
                "reply": ai_response,
                "crisis": crisis_info,
            }
        )


###############################################################################
# Mood tracking APIs
###############################################################################


@app.route("/api/mood/log", methods=["POST"])
def log_mood():
    """
    Log a mood entry for the current user.
    Expected JSON body:
    {
      "mood_score": int 1-10,
      "energy": optional int 1-10,
      "anxiety": optional int 1-10,
      "tags": optional [string],
      "journal_text": optional string,
      "timestamp": optional ISO string; if omitted, current time is used
    }
    """
    user_id = get_user_id()
    data = request.get_json() or {}

    mood_score = data.get("mood_score")
    if mood_score is None:
        return jsonify({"error": "mood_score is required"}), 400

    try:
        mood_score = int(mood_score)
    except (TypeError, ValueError):
        return jsonify({"error": "mood_score must be an integer"}), 400

    energy = data.get("energy")
    if energy is not None and energy != "":
        try:
            energy = int(energy)
        except (TypeError, ValueError):
            return jsonify({"error": "energy must be an integer"}), 400
    else:
        energy = None

    anxiety = data.get("anxiety")
    if anxiety is not None and anxiety != "":
        try:
            anxiety = int(anxiety)
        except (TypeError, ValueError):
            return jsonify({"error": "anxiety must be an integer"}), 400
    else:
        anxiety = None

    timestamp_str = data.get("timestamp")
    if not timestamp_str:
        timestamp_str = datetime.utcnow().isoformat()

    source = _normalize_text(data.get("source") or "manual") or "manual"
    tracking_mode = "manual" if source == "manual" else "auto"

    entry = {
        "timestamp": timestamp_str,
        "mood_score": mood_score,
        "energy": energy,
        "anxiety": anxiety,
        "tags": data.get("tags") or [],
        "journal_text": data.get("journal_text", "").strip(),
        "source": source,
        "tracking_mode": tracking_mode,
    }

    user_data = _append_mood_entry(user_id, entry)

    # When mood is low, try to attach any matching coping plans
    coping_suggestions = []
    if mood_score <= 3:
        coping_suggestions = _match_coping_plans_for_entry(entry, user_data)

    return jsonify(
        {
            "message": "Mood entry logged successfully.",
            "entry": entry,
            "coping_suggestions": coping_suggestions,
        }
    )


def _match_coping_plans_for_entry(entry, user_data):
    """
    Try to find coping plans relevant to the current entry based on tags
    and trigger IDs.
    """
    tags = set(entry.get("tags") or [])
    triggers = user_data.get("triggers", [])
    coping_plans = user_data.get("coping_plans", [])

    # First, infer which triggers look relevant based on overlapping tags
    relevant_trigger_ids = set()
    for t in triggers:
        trigger_tags = set(t.get("tags") or [])
        if tags & trigger_tags:
            relevant_trigger_ids.add(t.get("id"))

    suggestions = []
    for plan in coping_plans:
        linked = set(plan.get("linked_trigger_ids") or [])
        if linked & relevant_trigger_ids or not linked:
            suggestions.append(
                {
                    "id": plan.get("id"),
                    "title": plan.get("title"),
                    "steps": plan.get("steps", []),
                }
            )
    return suggestions


@app.route("/api/mood/entries", methods=["GET"])
def get_mood_entries():
    """
    Return mood entries for the current user.
    Optional query param:
      - days: limit to last N days
    """
    user_id = get_user_id()
    days_param = request.args.get("days")

    user_data = _load_user_mood_data(user_id)
    entries = user_data.get("entries", [])

    if days_param:
        try:
            days = int(days_param)
            cutoff = datetime.utcnow() - timedelta(days=days)
            filtered = []
            for e in entries:
                ts = _parse_iso_datetime(e.get("timestamp"))
                if ts is None:
                    filtered.append(e)
                    continue
                if ts >= cutoff:
                    filtered.append(e)
            entries = filtered
        except (TypeError, ValueError):
            pass

    return jsonify(entries)


@app.route("/api/mood/triggers", methods=["GET", "POST"])
def mood_triggers():
    """
    GET: list triggers for current user
    POST: create or update triggers. Body:
      {
        "triggers": [
          {"id": "...", "label": "...", "description": "...", "tags": [...]}
        ]
      }
    The client can generate IDs, or omit them to let the backend assign one.
    """
    user_id = get_user_id()
    user_data = _load_user_mood_data(user_id)

    if request.method == "GET":
        return jsonify(user_data.get("triggers", []))

    body = request.get_json() or {}
    triggers = body.get("triggers")
    if not isinstance(triggers, list):
        return jsonify({"error": "triggers must be a list"}), 400

    existing = {t.get("id"): t for t in user_data.get("triggers", []) if t.get("id")}
    for t in triggers:
        trig_id = t.get("id") or f"trig_{random.randint(100000, 999999)}"
        t["id"] = trig_id
        existing[trig_id] = {
            "id": trig_id,
            "label": t.get("label", ""),
            "description": t.get("description", ""),
            "tags": t.get("tags") or [],
        }

    user_data["triggers"] = list(existing.values())
    _save_user_mood_data(user_id, user_data)
    return jsonify(user_data["triggers"])


@app.route("/api/mood/coping_plans", methods=["GET", "POST"])
def mood_coping_plans():
    """
    GET: list coping plans for current user
    POST: create or update coping plans. Body:
      {
        "coping_plans": [
          {
            "id": "...",
            "title": "...",
            "steps": ["...", "..."],
            "linked_trigger_ids": ["...", "..."]
          }
        ]
      }
    """
    user_id = get_user_id()
    user_data = _load_user_mood_data(user_id)

    if request.method == "GET":
        return jsonify(user_data.get("coping_plans", []))

    body = request.get_json() or {}
    plans = body.get("coping_plans")
    if not isinstance(plans, list):
        return jsonify({"error": "coping_plans must be a list"}), 400

    existing = {
        p.get("id"): p for p in user_data.get("coping_plans", []) if p.get("id")
    }
    for p in plans:
        plan_id = p.get("id") or f"plan_{random.randint(100000, 999999)}"
        p["id"] = plan_id
        existing[plan_id] = {
            "id": plan_id,
            "title": p.get("title", ""),
            "steps": p.get("steps") or [],
            "linked_trigger_ids": p.get("linked_trigger_ids") or [],
        }

    user_data["coping_plans"] = list(existing.values())
    _save_user_mood_data(user_id, user_data)
    return jsonify(user_data["coping_plans"])


@app.route("/api/mood/reminders", methods=["GET", "POST"])
def mood_reminders():
    """
    Smart reminder configuration.
    GET: return all reminders for current user.
    POST: replace reminders array. Body:
      {
        "reminders": [
          {
            "id": "...",
            "time_of_day": "21:00",
            "days_of_week": ["Mon", "Tue"],
            "type": "evening_reflection",
            "enabled": true
          }
        ]
      }
    The client is responsible for actually scheduling local/push notifications
    based on this configuration.
    """
    user_id = get_user_id()
    user_data = _load_user_mood_data(user_id)

    if request.method == "GET":
        return jsonify(user_data.get("reminders", []))

    body = request.get_json() or {}
    reminders = body.get("reminders")
    if not isinstance(reminders, list):
        return jsonify({"error": "reminders must be a list"}), 400

    # Normalize and assign IDs if needed
    normalized = []
    for r in reminders:
        rem_id = r.get("id") or f"rem_{random.randint(100000, 999999)}"
        normalized.append(
            {
                "id": rem_id,
                "time_of_day": r.get("time_of_day", ""),
                "days_of_week": r.get("days_of_week") or [],
                "type": r.get("type", "general"),
                "enabled": bool(r.get("enabled", True)),
            }
        )

    user_data["reminders"] = normalized
    _save_user_mood_data(user_id, user_data)
    return jsonify(user_data["reminders"])


@app.route("/api/mood/journal_prompt", methods=["GET"])
def mood_journal_prompt():
    """
    Return a guided journaling prompt based on the optional mood_score.
    """
    mood_param = request.args.get("mood_score")
    try:
        mood_score = int(mood_param) if mood_param is not None else None
    except (TypeError, ValueError):
        mood_score = None

    low_prompts = [
        "What made today feel especially hard, and how did you cope with it?",
        "What thoughts kept coming up for you today when you felt low?",
        "Is there someone or something that might bring you a bit of comfort right now?",
    ]
    neutral_prompts = [
        "What is one small thing that went okay or better than expected today?",
        "If you could send a kind message to yourself today, what would it say?",
    ]
    high_prompts = [
        "What went well today that youâ€™d like to remember later?",
        "What strengths did you use today that you feel proud of?",
    ]

    if mood_score is None:
        prompt_list = neutral_prompts
    elif mood_score <= 3:
        prompt_list = low_prompts
    elif mood_score >= 7:
        prompt_list = high_prompts
    else:
        prompt_list = neutral_prompts

    prompt = random.choice(prompt_list)
    return jsonify({"prompt": prompt})


@app.route("/api/mood/stats/overview", methods=["GET"])
def mood_stats_overview():
    """
    Return simple stats and series data for mood over time.
    Query params:
      - days: limit to last N days (default 30)
    """
    user_id = get_user_id()
    days_param = request.args.get("days", "30")
    try:
        days = int(days_param)
    except (TypeError, ValueError):
        days = 30

    user_data = _load_user_mood_data(user_id)
    entries = user_data.get("entries", [])

    cutoff = datetime.utcnow() - timedelta(days=days)
    series = []
    weekday_sums = {i: {"total": 0, "count": 0} for i in range(7)}
    source_breakdown = {}

    for e in entries:
        ts_str = e.get("timestamp")
        ts = _parse_iso_datetime(ts_str)
        if ts is None:
            continue
        if ts < cutoff:
            continue
        mood_score = e.get("mood_score")
        try:
            mood_score = float(mood_score)
        except (TypeError, ValueError):
            continue

        source = e.get("source") or "manual"
        source_breakdown[source] = source_breakdown.get(source, 0) + 1
        series.append(
            {
                "timestamp": ts.isoformat(),
                "mood_score": mood_score,
                "source": source,
            }
        )

        wd = ts.weekday()
        weekday_sums[wd]["total"] += mood_score
        weekday_sums[wd]["count"] += 1

    series.sort(key=lambda item: item["timestamp"])

    weekday_averages = []
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i in range(7):
        total = weekday_sums[i]["total"]
        count = weekday_sums[i]["count"]
        avg = total / count if count else None
        weekday_averages.append({"weekday": weekday_names[i], "average_mood": avg})

    overall_avg = sum(p["mood_score"] for p in series) / len(series) if series else None

    return jsonify(
        {
            "overall_average_mood": overall_avg,
            "daily_mood_series": series,
            "weekday_averages": weekday_averages,
            "source_breakdown": source_breakdown,
        }
    )


@app.route("/api/mood/ai_insights", methods=["GET"])
def mood_ai_insights():
    """
    Use the Together API to provide a reflective summary over the user's
    recent mood entries.
    Query params:
      - days: look back this many days (default 14)
    """
    user_id = get_user_id()
    days_param = request.args.get("days", "14")
    try:
        days = int(days_param)
    except (TypeError, ValueError):
        days = 14

    user_data = _load_user_mood_data(user_id)
    entries = user_data.get("entries", [])
    if not entries:
        return jsonify({"insights": "You haven't logged any mood entries yet."})

    cutoff = datetime.utcnow() - timedelta(days=days)
    recent_entries = []
    for e in entries:
        ts = _parse_iso_datetime(e.get("timestamp"))
        if ts is None:
            continue
        if ts >= cutoff:
            recent_entries.append(e)

    if not recent_entries:
        return jsonify(
            {
                "insights": (
                    "I don't see any mood entries in the selected time range yet. "
                    "Try logging your mood for a little while, then come back for insights."
                )
            }
        )

    insights = analyze_mood_history_with_together(recent_entries)
    return jsonify({"insights": insights})


@app.route("/api/mood/export", methods=["GET"])
def mood_export():
    """
    Export mood entries in a therapy-friendly structured format.
    Supported formats:
      - json (default)
      - csv
    Query params:
      - format: 'json' or 'csv'
      - days: only include last N days (optional)
    """
    import io
    import csv

    user_id = get_user_id()
    fmt = (request.args.get("format") or "json").lower()
    days_param = request.args.get("days")

    user_data = _load_user_mood_data(user_id)
    entries = user_data.get("entries", [])

    if days_param:
        try:
            days = int(days_param)
            cutoff = datetime.utcnow() - timedelta(days=days)
            filtered = []
            for e in entries:
                ts = _parse_iso_datetime(e.get("timestamp"))
                if ts is None:
                    filtered.append(e)
                    continue
                if ts >= cutoff:
                    filtered.append(e)
            entries = filtered
        except (TypeError, ValueError):
            pass

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "timestamp",
                "mood_score",
                "energy",
                "anxiety",
                "tags",
                "journal_text",
                "source",
                "tracking_mode",
            ]
        )
        for e in entries:
            writer.writerow(
                [
                    e.get("timestamp", ""),
                    e.get("mood_score", ""),
                    e.get("energy", ""),
                    e.get("anxiety", ""),
                    ";".join(e.get("tags", [])),
                    e.get("journal_text", "").replace("\n", " "),
                    e.get("source", "manual"),
                    e.get("tracking_mode", "manual"),
                ]
            )
        csv_data = output.getvalue()
        output.close()
        return (
            csv_data,
            200,
            {
                "Content-Type": "text/csv; charset=utf-8",
                "Content-Disposition": 'attachment; filename="mood_export.csv"',
            },
        )

    # Default: JSON with a small disclaimer
    return jsonify(
        {
            "disclaimer": (
                "This export is intended to help you and your mental health "
                "professional review patterns over time. It is not a clinical "
                "assessment or diagnosis."
            ),
            "entries": entries,
        }
    )


@app.route("/api/model_benchmark", methods=["GET"])
def get_model_benchmark():
    try:
        with open("static/data/model_benchmark.json", "r", encoding="utf-8") as f:
            benchmark_data = json.load(f)
        return jsonify(benchmark_data)
    except Exception as e:
        logging.error(f"Failed to load benchmark data: {e}")
        return jsonify(
            {"error": "Failed to load benchmark data", "message": str(e)}
        ), 500


@app.route("/api/assessment_questions", methods=["GET"])
def get_assessment_questions():
    try:
        assessment_type = _normalize_text(request.args.get("type") or "general")
        with open("static/data/assessment_questions.json", "r", encoding="utf-8") as f:
            questions = json.load(f)
        if assessment_type == "general":
            questions = [q for q in questions if q.get("general", True)]
        elif assessment_type == "detailed":
            questions = [q for q in questions if q.get("detailed", True)]

        sanitized_questions = []
        for q in questions:
            sanitized_q = dict(q)
            sanitized_q["question"] = _sanitize_text(sanitized_q.get("question", ""))
            sanitized_q["options"] = [
                _sanitize_text(option) for option in sanitized_q.get("options", [])
            ]
            sanitized_questions.append(sanitized_q)

        return jsonify(sanitized_questions)
    except Exception as e:
        logging.error(f"Failed to load assessment questions: {e}")
        return jsonify(
            {"error": "Failed to load assessment questions", "message": str(e)}
        ), 500


@app.route("/api/test_together", methods=["GET"])
def test_together():
    try:
        response = client.chat.completions.create(
            model="mistralai/Mistral-Small-24B-Instruct-2501",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
            temperature=0.7,
        )
        return jsonify({"response": response.choices[0].message.content})
    except Exception as e:
        logging.error(f"Error in test_together route: {e}", exc_info=True)
        return jsonify(
            {"error": "Failed to get response from Together API", "message": str(e)}
        ), 500


@app.route("/api/assessment_analysis", methods=["POST"])
def assessment_analysis():
    data = request.get_json() or {}
    raw_answers = data.get("answers", [])
    assessment_type = _normalize_text(data.get("assessment_type") or "general")

    logging.info(f"Assessment analysis requested with {len(raw_answers)} answers")
    logging.debug(f"Answers payload: {raw_answers}")

    if not isinstance(raw_answers, list) or not raw_answers:
        logging.warning("No answers provided for assessment analysis")
        return jsonify({"error": "No answers provided"}), 400

    try:
        user_id = get_user_id()
        answer_lines = []
        for item in raw_answers:
            if isinstance(item, dict):
                answer_text = _sanitize_text(item.get("answer", "")).strip()
                question_text = _sanitize_text(item.get("question", "")).strip()
                if not answer_text or answer_text.lower() == "no response":
                    continue
                if question_text:
                    answer_lines.append(f"{question_text} -> {answer_text}")
                else:
                    answer_lines.append(answer_text)
            else:
                answer_text = _sanitize_text(item).strip()
                if answer_text and answer_text.lower() != "no response":
                    answer_lines.append(answer_text)

        if not answer_lines:
            return jsonify({"error": "No valid answers provided"}), 400

        analysis = analyze_responses_with_together(
            conversation_history=None,
            assessment_mode=True,
            answers=answer_lines,
        )
        auto_entry = _build_assessment_mood_entry(
            raw_answers,
            assessment_type=assessment_type if assessment_type else "general",
        )
        mood_logged = _append_auto_mood_entry(
            user_id,
            auto_entry,
            min_interval_minutes=30,
        )
        logging.info("Assessment analysis generated successfully")
        return jsonify({"analysis": analysis, "mood_logged": mood_logged})
    except Exception as e:
        logging.error(f"Error in assessment_analysis: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/emergency_alert", methods=["POST"])
def emergency_alert():
    """
    Trigger an emergency alert for the current user.
    This endpoint is intended to be called by the frontend AFTER the user
    has explicitly confirmed they want to alert trusted contacts or seek help.

    Expected JSON body (can be extended later):
      {
        "message_context": "...",   # recent user message that raised concern
        "risk_level": "high",       # from detect_crisis()
        "channel": "chat" | "voice"
      }

    NOTE: For safety and privacy, this implementation currently only logs the
    alert event. You can integrate Twilio / email / other services here to
    actually notify trusted contacts once you have proper consent flows.
    """
    user_id = get_user_id()
    data = request.get_json() or {}
    message_context = data.get("message_context", "")
    risk_level = data.get("risk_level", "unknown")
    channel = data.get("channel", "unknown")

    logging.warning(
        "EMERGENCY ALERT | user_id=%s | channel=%s | risk=%s | context=%r",
        user_id,
        channel,
        risk_level,
        message_context,
    )

    # Placeholder for future integrations (SMS, email, etc.)
    # Example:
    #   notify_emergency_contacts(user_id, message_context, risk_level, channel)

    return jsonify({"status": "alert_logged"})


@socketio.on("connect")
def handle_connect():
    """
    Socket.IO client connected.
    Useful for debugging connection issues with the voice chat channel.
    """
    logging.info("Socket.IO client connected.")


@socketio.on("voice_message")
def handle_voice_message(data):
    """
    Handle incoming voice transcript messages from the client.
    This is intentionally wrapped in try/except so that any Together API
    or processing error still returns a response to the browser instead
    of failing silently.
    """
    try:
        user_id = get_user_id()

        message = data
        logging.info(f"Received voice message from {user_id}: {message!r}")

        if not message:
            emit(
                "bot_response",
                {
                    "reply": "Sorry, I did not receive any message from your microphone.",
                    "crisis": {"risk_level": "none", "matched_phrases": []},
                },
            )
            return

        # Detect potential crisis language in the latest voice transcript
        crisis_info = detect_crisis(message)

        auto_mood_entry = _build_auto_mood_entry_from_text(message, source="voice_chat")
        _append_auto_mood_entry(user_id, auto_mood_entry, min_interval_minutes=8)

        # Get user chat history or initialize
        history = user_chat_history.get(user_id, [])
        history.append({"role": "user", "content": message})

        # Process message with AI
        ai_response = analyze_responses_with_together(history)

        # Append AI response to history
        history.append({"role": "assistant", "content": ai_response})
        user_chat_history[user_id] = history

        # Emit response back to client, including crisis info so the
        # frontend can show emergency UI when needed.
        emit(
            "bot_response",
            {
                "reply": ai_response,
                "crisis": crisis_info,
            },
        )
    except Exception as e:
        logging.error("Error while handling voice_message", exc_info=True)
        emit(
            "bot_response",
            {
                "reply": (
                    "Sorry, I had trouble processing your voice message. "
                    "Please try sending the same message via text chat while this is being investigated."
                ),
                "crisis": {"risk_level": "none", "matched_phrases": []},
            },
        )


if __name__ == "__main__":
    # Render sets PORT at runtime; default to 5000 for local development.
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    socketio.run(app, host="0.0.0.0", port=port, debug=debug)

