"""
FastAPI wrapper around the RAG chatbot, with server-side session state
(running summary + follow-up/clarification tracking) so the frontend only
needs to send session_id + message each turn.

Run with:
    uvicorn app:app --reload --port 8000
"""

from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from RAG.generation import generate_response

app = FastAPI(title="T2Dcare Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# session_id -> {"history": [...], "summary": "...", "clarification_count": int}
sessions: Dict[str, Dict] = {}

MAX_CLARIFICATIONS = 5


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    message: str
    follow_up: Optional[str] = None
    sources: list[dict] = []
    trace: dict = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if req.session_id not in sessions:
        sessions[req.session_id] = {
            "history": [],
            "summary": "",
            "clarification_count": 0,
        }

    session = sessions[req.session_id]
    session["history"].append({"role": "user", "content": req.message})

    try:
        result = generate_response(
            message=req.message,
            history=session["history"],
            previous_summary=session["summary"],
            clarification_count=session["clarification_count"],
            max_clarifications=MAX_CLARIFICATIONS,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    session["summary"] = result["summary"]

    reply = result["answer"]
    if result["follow_up"]:
        reply += f"\n\n{result['follow_up']}"
        session["clarification_count"] += 1
    else:
        session["clarification_count"] = 0

    session["history"].append({"role": "assistant", "content": reply})

    return ChatResponse(
        session_id=req.session_id,
        message=reply,
        follow_up=result["follow_up"],
        sources=result["sources"],
        trace=result.get("trace", {}),
    )