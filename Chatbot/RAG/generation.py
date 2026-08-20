"""
Generate a structured answer (answer + optional follow-up + running summary)
grounded in retrieved NICE guideline chunks.
"""

import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

from RAG.retrivement import query_chunks

client = OpenAI(api_key=os.getenv("API_KEY"))

GREETING_KEYWORDS = {"hi", "hello", "hey", "greetings", "good morning", "good afternoon",
                      "good evening", "howdy", "what's up", "sup"}

GREETING_RESPONSE = (
    "Hello! I'm T2D Care AI, your Type 2 diabetes assistant. "
    "I answer questions about Type 2 diabetes management based on the NICE guideline (NG28). "
    "I can help with topics like:\n"
    "• Blood glucose targets & HbA1c\n"
    "• Medication options (metformin, SGLT2 inhibitors, etc.)\n"
    "• Lifestyle advice (diet, exercise)\n"
    "• Monitoring & complication management\n\n"
    "Go ahead and ask me anything about Type 2 diabetes!"
)

WELCOME_MESSAGE = (
    "Hi! Ask me anything about Type 2 diabetes management based on the NICE guideline.\n"
    "I can help with topics like medication, lifestyle advice, monitoring, and more.\n"
    "Type 'quit' to exit.\n"
)

SYSTEM_PROMPT = """You are a clinical assistant answering questions about the NICE guideline
on type 2 diabetes management in adults, using the provided context chunks and the
conversation summary so far.

Respond ONLY with a JSON object (no markdown, no preamble) with exactly these keys:
- "answer": your answer to the user's latest message, grounded in the context. If the
  context does not cover the topic, say so plainly here instead of guessing.
- "follow_up": a single short clarifying question if (and only if) the user's message is
  ambiguous or missing details needed for a safe, specific answer (e.g. which medicine,
  which comorbidity, which stage of treatment). Otherwise set this to null.
- "summary": an updated one-to-three sentence running summary of the conversation so far
  (previous summary + this exchange), so future turns have context without needing full
  chat history.
- "in_scope": true if the user's question is related to type 2 diabetes management,
  false otherwise.

Rules:
- Only ask a follow_up when it's genuinely needed to give a safe, correct answer.
- If clarification_limit_reached is true, do NOT ask a follow_up even if one would
  normally help — answer with your best interpretation instead, noting the assumption.
- Never fabricate information not present in the context.
- If the question is not related to type 2 diabetes management, set in_scope to false,
  set answer to a polite redirect message, and set follow_up to null.
"""

OUT_OF_SCOPE_ANSWER = (
    "That question is outside my scope. I'm T2D Care AI — I specifically answer questions "
    "about Type 2 diabetes management based on the NICE guideline (NG28).\n\n"
    "I can help with:\n"
    "• Blood glucose targets & HbA1c\n"
    "• Medication options (metformin, SGLT2 inhibitors, etc.)\n"
    "• Lifestyle advice (diet, exercise)\n"
    "• Monitoring & complication management\n\n"
    "Feel free to ask me anything about Type 2 diabetes!"
)

DISTANCE_THRESHOLD = 0.7  # above this, the best chunk isn't relevant enough to answer from

NO_INFO_ANSWER = (
    "I don't have enough information in the guideline to answer that confidently. "
    "Could you rephrase your question or ask about something more specific to type 2 diabetes management?"
)

TEXT_PREVIEW_LENGTH = 200  # chars of chunk text shown in the dashboard trace

# Keywords that suggest the question is likely in scope (fast pre-check before LLM)
DIABETES_KEYWORDS = {
    "diabetes", "diabetic", "glucose", "insulin", "hba1c", "metformin",
    "blood sugar", "glycemic", "glycaemic", "type 2", "t2d", "t2dm",
    "hyperglycemia", "hyperglycaemia", "hypoglycemia", "hypoglycaemia",
    "medication", "nice guideline", "diet", "lifestyle", "weight", "cardiovascular",
    "kidney", "retinopathy", "neuropathy", "cholesterol", "blood pressure",
}


def is_likely_in_scope(message: str) -> bool:
    """Quick keyword check — if any diabetes-related term is found, assume in scope."""
    lowered = message.lower()
    return any(kw in lowered for kw in DIABETES_KEYWORDS)


def build_context(hits: list[dict]) -> str:
    """Build context from a single chunk (the top match)."""
    if not hits:
        return ""
    top = hits[0]
    return top["text"]


def build_retrieval_query(message: str, previous_summary: str) -> str:
    if not previous_summary:
        return message
    return f"{previous_summary} {message}"


def generate_response(
    message: str,
    history: list[dict] | None = None,
    previous_summary: str = "",
    clarification_count: int = 0,
    max_clarifications: int = 5,
    top_k: int = 5,
    model: str = "gpt-4o-mini",
) -> dict:
    """
    message: the user's latest message
    history: full turn list (optional, only used to give the model recent raw
              context alongside the summary — safe to pass [] if you rely on summary only)
    previous_summary: running summary from the session state
    clarification_count: how many follow-ups have been asked so far this session
    Returns: {"answer", "follow_up", "summary", "sources", "in_scope"}
    """

    # --- Greeting detection ---
    stripped = message.strip().lower().rstrip("!?.,")
    if stripped in GREETING_KEYWORDS and not previous_summary:
        return {
            "answer": GREETING_RESPONSE,
            "follow_up": None,
            "summary": "",
            "sources": [],
            "in_scope": True,
            "trace": {"question": message, "skipped": "greeting"},
        }

    # --- Fast out-of-scope pre-check ---
    if not is_likely_in_scope(message) and not previous_summary:
        return {
            "answer": OUT_OF_SCOPE_ANSWER,
            "follow_up": None,
            "summary": previous_summary,
            "sources": [],
            "in_scope": False,
            "trace": {"question": message, "skipped": "out_of_scope_pre_check"},
        }

    retrieval_query = build_retrieval_query(message, previous_summary)
    hits = query_chunks(retrieval_query, top_k=top_k)

    best_distance = hits[0]["distance"] if hits else None
    validation_passed = best_distance is not None and best_distance <= DISTANCE_THRESHOLD

    trace = {
        "question": message,
        "retrieved_chunks": [
            {
                "chunk_id": h["id"],
                "text": h["text"],
                "distance": h["distance"],
            }
            for h in hits
        ],
        "selected_chunk_id": hits[0]["id"] if hits else None,
        "validation": {
            "threshold": DISTANCE_THRESHOLD,
            "best_distance": best_distance,
            "passed": validation_passed,
        },
    }

    # Short-circuit: if even the best match is too far, don't bother calling the LLM.
    if not validation_passed:
        return {
            "answer": NO_INFO_ANSWER,
            "follow_up": None,
            "summary": previous_summary,
            "sources": trace["retrieved_chunks"],
            "in_scope": True,  # assume in scope but guideline just doesn't cover it
            "trace": trace,
        }

    context = build_context(hits)
    clarification_limit_reached = clarification_count >= max_clarifications

    user_prompt = f"""Previous summary: {previous_summary or "(none yet)"}
clarification_limit_reached: {clarification_limit_reached}

Context:
{context}

User's latest message: {message}

Respond with only the JSON object described in the system prompt."""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-4:])  # a little raw recent context helps tone/continuity
    messages.append({"role": "user", "content": user_prompt})

    response = client.chat.completions.create(
        model=model,
        max_tokens=600,
        temperature=0.2,
        messages=messages,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"answer": raw, "follow_up": None, "summary": previous_summary, "in_scope": True}

    # If the LLM itself flagged the question as out of scope, override the answer.
    if not parsed.get("in_scope", True):
        return {
            "answer": OUT_OF_SCOPE_ANSWER,
            "follow_up": None,
            "summary": previous_summary,
            "sources": trace["retrieved_chunks"],
            "in_scope": False,
            "trace": trace,
        }

    return {
        "answer": parsed.get("answer", ""),
        "follow_up": parsed.get("follow_up") or None,
        "summary": parsed.get("summary", previous_summary),
        "sources": trace["retrieved_chunks"],
        "in_scope": True,
        "trace": trace,
    }


if __name__ == "__main__":
    print(WELCOME_MESSAGE)

    history = []
    summary = ""
    clar_count = 0

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not msg:
            continue

        if msg.lower() in ("quit", "exit"):
            print("Goodbye! Stay healthy.")
            break

        result = generate_response(
            msg,
            history=history,
            previous_summary=summary,
            clarification_count=clar_count,
        )

        print(f"\nBot: {result['answer']}")

        if result.get("follow_up"):
            print(f"Follow-up: {result['follow_up']}")
            clar_count += 1
        else:
            clar_count = 0

        summary = result["summary"]

        if result.get("in_scope", True):
            history.append({"role": "user", "content": msg})
            history.append({"role": "assistant", "content": result["answer"]})

        print()