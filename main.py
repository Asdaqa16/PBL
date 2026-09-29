from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import os
import logging
from typing import List, Dict, Optional


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("API_KEY", "demo_key")
CALLBACK_URL = os.getenv("CALLBACK_URL")

app = FastAPI(title="Agentic Honeypot API", version="1.0")


sessions = {}

def get_session(session_id: str):
    if session_id not in sessions:
        sessions[session_id] = {
            "messages": [],
            "intelligence": {},
            "finalized": False
        }
    return sessions[session_id]

def save_session(session_id: str, session: dict):
    sessions[session_id] = session


def agent_step(session: dict, incoming_text: str):
    
    session["messages"].append(incoming_text)

    
    if "upi" in incoming_text.lower():
        session["intelligence"]["upiIds"] = ["demo-upi@bank"]

   
    should_finalize = len(session["messages"]) >= 3

    return {
        "reply": f"Echo: {incoming_text}",
        "should_finalize": should_finalize,
        "agent_notes": "Mock agent logic used (demo mode)."
    }


class Message(BaseModel):
    sender: str
    text: str
    timestamp: int


class HoneypotRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: Optional[List[dict]] = None
    metadata: Optional[Dict] = None


@app.get("/")
def health():
    return {"status": "backend running (demo mode)"}


@app.post("/api/honeypot")
def honeypot(
    body: HoneypotRequest,
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
):

    
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    session_id = body.sessionId
    incoming_text = body.message.text

    
    session = get_session(session_id)

    
    agent_output = agent_step(session, incoming_text)

    
    save_session(session_id, session)

    
    if agent_output["should_finalize"] and not session.get("finalized"):
        session["finalized"] = True
        logger.info("Session %s finalized (demo mode)", session_id)

    return {
        "status": "success",
        "reply": agent_output["reply"],
        "demo_note": "Redis and advanced agent logic will be integrated in future."
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
