"""
outer_agent.py

Outer Agent for a scam-baiting / scam-detection system.

The Outer Agent has two personalities:
    1. "scammer"  -> simulated attacker / scammer
    2. "normal"   -> normal, confused, cautious Indian person

Input:
    JSON containing the personality, conversation history, and latest message.

Output:
    JSON containing the generated reply and metadata.

This module is intentionally designed for a defensive scam-baiting
environment. The scammer persona is a simulation and uses placeholders
rather than real credentials, OTPs, passwords, or financial secrets.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataset-derived behavioral patterns
# ---------------------------------------------------------------------------

SCAMMER_STRATEGIES = [
    "authority",
    "urgency",
    "verification",
    "problem_alert",
    "reward_offer",
    "follow_up",
    "reassurance",
    "information_request",
]

NORMAL_STRATEGIES = [
    "confused",
    "cautious",
    "cooperative",
    "uncertain",
    "needs_clarification",
    "wants_reassurance",
]


def _conversation_text(history: List[Dict[str, Any]]) -> str:
    """Convert structured history into the format used by the prompts."""
    lines = []

    for message in history[-8:]:
        sender = message.get("sender", "Unknown")
        text = message.get("text", "")

        if text:
            lines.append(f"{sender}: {text}")

    return "\n".join(lines)


def _detect_language(text: str) -> str:
    """
    Follow the same language idea as persona.py:
    use Hinglish only when Hindi/Hinglish words are present.
    """
    hindi_words = {
        "hai", "haan", "nahi", "nahin", "acha", "accha", "bhai",
        "didi", "sir", "madam", "ji", "mera", "meri", "aap",
        "apka", "kya", "kyun", "kaise", "kab", "mujhe", "mujhse",
        "karna", "karo", "kariye", "chahiye", "paise", "paisa",
        "account", "band", "khul", "bhejo", "do", "please"
    }

    words = set(re.findall(r"[a-zA-Z]+", text.lower()))

    if words.intersection(hindi_words):
        return "hinglish"

    return "english"


# ---------------------------------------------------------------------------
# Scammer / attacker personality
# ---------------------------------------------------------------------------

SCAMMER_PERSONA = """
You are the OUTER AGENT in a defensive scam-baiting system.

You are SIMULATING a scammer/attacker for a controlled security test.
Your goal is to keep the conversation believable long enough for the
defensive agent to observe the attacker's conversational behavior.

Behavioral style:
- Sound confident and conversational.
- Establish a believable reason for contacting the target.
- Use social-engineering patterns such as authority, urgency,
  verification, problem alerts, rewards, reassurance, and follow-ups.
- Escalate gradually instead of immediately asking for everything.
- If the target becomes suspicious, reassure them and change the
  explanation rather than suddenly becoming aggressive.
- Keep messages short enough to resemble real chat/SMS/call dialogue.
- Mirror the target's language style when useful.
- Maintain continuity with previous messages.
- Do not openly admit that you are a scammer or that this is a test.

DEFENSIVE-SIMULATION SAFETY:
- Never request or generate real passwords, real OTPs, real card numbers,
  real authentication codes, or real financial credentials.
- When an attacker would normally request sensitive information,
  use safe placeholders such as <OTP>, <ACCOUNT_NUMBER>, <UPI_ID>,
  <PHONE_NUMBER>, or <LINK>.
- Never provide instructions for stealing credentials, bypassing MFA,
  compromising accounts, or moving real money.
- Keep the attack behavior at the conversational/social-engineering level
  so the defensive agent can detect and extract it.

The dataset uses "Suspect" for the suspicious side and "Innocent" for
the target. Maintain natural conversational turns rather than writing
long explanations.
"""


# ---------------------------------------------------------------------------
# Normal-person personality
# ---------------------------------------------------------------------------

NORMAL_PERSONA = """
You are the OUTER AGENT in a defensive scam-baiting system.

You are simulating a normal Indian person who has received an unexpected
message/call.

Your personality:
- Confused, cautious and imperfect.
- Sometimes cooperative, sometimes uncertain.
- Ask simple imperfect questions.
- Do not sound like a cybersecurity expert.
- Do not immediately identify something as a scam.
- Do not over-explain.
- Do not use excessive punctuation.
- Keep replies relatively short.
- If the other person uses Hindi/Hinglish, reply naturally in Hinglish.
- Otherwise reply in English.
- You may ask for clarification or reassurance.
- Do not mention scam detection, the defensive system, or this simulation.

UPI can be mentioned naturally because it is common in Indian digital
payments, but never provide real credentials or authentication codes.
Use placeholders if a sensitive value is needed for simulation.
"""


# ---------------------------------------------------------------------------
# Strategy selection
# ---------------------------------------------------------------------------

def choose_scammer_strategy(history: List[Dict[str, Any]],
                            incoming_text: str) -> str:
    """
    Choose the next conversational strategy from the current context.

    This is intentionally lightweight. The LLM receives the strategy
    and can produce the actual natural-language response.
    """
    text = incoming_text.lower()

    if any(x in text for x in ["who are you", "why", "real reason", "what do you want"]):
        return "authority"

    if any(x in text for x in ["verify", "verification", "confirm", "kyc"]):
        return "verification"

    if any(x in text for x in ["blocked", "suspended", "freeze", "problem", "issue"]):
        return "problem_alert"

    if any(x in text for x in ["offer", "reward", "cashback", "discount", "prize"]):
        return "reward_offer"

    if any(x in text for x in ["later", "tomorrow", "call back", "wait"]):
        return "follow_up"

    if any(x in text for x in ["safe", "legitimate", "trust", "sure"]):
        return "reassurance"

    if any(x in text for x in ["urgent", "now", "immediately", "quickly"]):
        return "urgency"

    # Gradual escalation:
    if len(history) <= 1:
        return "authority"

    if len(history) <= 3:
        return "verification"

    return "information_request"


def choose_normal_strategy(history: List[Dict[str, Any]],
                           incoming_text: str) -> str:
    text = incoming_text.lower()

    if "?" in incoming_text:
        return "needs_clarification"

    if any(x in text for x in ["otp", "password", "pin", "upi", "account"]):
        return "cautious"

    if any(x in text for x in ["urgent", "immediately", "blocked", "suspended"]):
        return "confused"

    if len(history) <= 1:
        return "uncertain"

    return "cooperative"


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_outer_prompt(
    history: List[Dict[str, Any]],
    personality: str,
    incoming_text: str,
    strategy: Optional[str] = None,
) -> str:
    """
    Build the prompt that can be passed to Gemini/OpenAI/etc.
    """

    personality = personality.lower().strip()

    if personality in {"scammer", "attacker", "suspect"}:
        persona = SCAMMER_PERSONA
        selected_strategy = strategy or choose_scammer_strategy(
            history, incoming_text
        )
    elif personality in {"normal", "innocent", "person"}:
        persona = NORMAL_PERSONA
        selected_strategy = strategy or choose_normal_strategy(
            history, incoming_text
        )
    else:
        raise ValueError(
            "personality must be 'scammer' or 'normal'"
        )

    conversation = _conversation_text(history)
    language = _detect_language(incoming_text)

    return f"""
{persona}

CURRENT STRATEGY:
{selected_strategy}

LANGUAGE:
{language}

CONVERSATION SO FAR:
{conversation if conversation else "(conversation has just started)"}

LATEST MESSAGE FROM THE OTHER AGENT:
"{incoming_text}"

Generate exactly ONE natural reply.

Return ONLY valid JSON in this exact structure:
{{
  "personality": "{personality}",
  "strategy": "{selected_strategy}",
  "language": "{language}",
  "reply": "..."
}}
""".strip()


# ---------------------------------------------------------------------------
# JSON validation / cleanup
# ---------------------------------------------------------------------------

def parse_model_response(raw_response: str) -> Dict[str, Any]:
    """
    Parse JSON returned by an LLM.

    Also handles models that accidentally wrap JSON in ```json ... ```.
    """
    cleaned = raw_response.strip()

    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Outer agent returned invalid JSON: {exc}"
        ) from exc

    required = {"personality", "strategy", "language", "reply"}

    missing = required - set(data.keys())

    if missing:
        raise ValueError(
            f"Outer agent JSON is missing fields: {sorted(missing)}"
        )

    if not isinstance(data["reply"], str):
        raise ValueError("The 'reply' field must be a string.")

    return data


# ---------------------------------------------------------------------------
# Gemini integration
# ---------------------------------------------------------------------------

def generate_with_gemini(
    history: List[Dict[str, Any]],
    personality: str,
    incoming_text: str,
    api_key: Optional[str] = None,
    model: str = "gemini-2.0-flash",
    strategy: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate an outer-agent reply with Google's Gemini API.

    Requires:
        pip install google-genai

    API key can be passed directly or stored in GEMINI_API_KEY.
    """

    try:
        from google import genai
    except ImportError as exc:
        raise ImportError(
            "google-genai is not installed. Run: pip install google-genai"
        ) from exc

    api_key = api_key or os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to your environment or .env."
        )

    client = genai.Client(api_key=api_key)

    prompt = build_outer_prompt(
        history=history,
        personality=personality,
        incoming_text=incoming_text,
        strategy=strategy,
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "temperature": 0.8,
            "response_mime_type": "application/json",
        },
    )

    return parse_model_response(response.text)


# ---------------------------------------------------------------------------
# Provider-independent interface
# ---------------------------------------------------------------------------

def generate_outer_response(
    history: List[Dict[str, Any]],
    personality: str,
    incoming_text: str,
    strategy: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = "gemini-2.0-flash",
) -> Dict[str, Any]:
    """
    Main function your application should call.
    """

    return generate_with_gemini(
        history=history,
        personality=personality,
        incoming_text=incoming_text,
        api_key=api_key,
        model=model,
        strategy=strategy,
    )


# ---------------------------------------------------------------------------
# JSON request interface
# ---------------------------------------------------------------------------

def handle_json_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept a JSON-compatible Python dictionary.

    Example request:
    {
        "personality": "scammer",
        "history": [
            {"sender": "Innocent", "text": "Hello"},
            {"sender": "Suspect", "text": "Hi, this is customer support"}
        ],
        "message": "Why are you calling me?"
    }
    """

    personality = request.get("personality", "normal")
    history = request.get("history", [])
    incoming_text = request.get("message", "")

    if not isinstance(history, list):
        raise ValueError("'history' must be a list.")

    if not incoming_text:
        raise ValueError("'message' is required.")

    return generate_outer_response(
        history=history,
        personality=personality,
        incoming_text=incoming_text,
        strategy=request.get("strategy"),
        api_key=request.get("api_key"),
        model=request.get("model", "gemini-2.0-flash"),
    )


# ---------------------------------------------------------------------------
# Command-line testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Outer agent for scam-baiting simulation"
    )

    parser.add_argument(
        "--personality",
        choices=["scammer", "normal"],
        default="normal",
    )

    parser.add_argument(
        "--message",
        required=True,
        help="Latest message from the other agent",
    )

    parser.add_argument(
        "--model",
        default="gemini-2.0-flash",
    )

    args = parser.parse_args()

    result = generate_outer_response(
        history=[],
        personality=args.personality,
        incoming_text=args.message,
        model=args.model,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
