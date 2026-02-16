"""ThemePulse - FastAPI backend for live classroom theme extraction."""

import asyncio
import io
import logging
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

import qrcode
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from models import (
    CreateSessionRequest,
    CreateSessionResponse,
    SessionInfoResponse,
    SubmitResponseRequest,
    SubmitResponseResponse,
    SummaryPayload,
    Theme,
)
from openrouter import summarize_responses

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

sessions: dict[str, dict] = {}
# sessions[session_id] = {
#     "question": str,
#     "admin_token": str,
#     "responses": [{"id": str, "student_name": str, "answer": str, "ts": float}],
#     "last_summary": SummaryPayload | None,
#     "last_summarized_count": int,
#     "sse_queues": list[asyncio.Queue],
#     "created_at": float,
#     "summarizer_task": asyncio.Task | None,
# }

SESSION_EXPIRY_HOURS = 24
MIN_RESPONSES_FOR_SUMMARY = 3
SUMMARIZE_INTERVAL_SECONDS = 10


# ---------------------------------------------------------------------------
# Background summarizer
# ---------------------------------------------------------------------------

async def _summarizer_loop(session_id: str):
    """Background loop that auto-summarizes responses for a session."""
    logger.info("Summarizer started for session %s", session_id)
    while True:
        await asyncio.sleep(SUMMARIZE_INTERVAL_SECONDS)

        session = sessions.get(session_id)
        if session is None:
            logger.info("Session %s removed, stopping summarizer", session_id)
            return

        responses = session["responses"]
        count = len(responses)

        if count < MIN_RESPONSES_FOR_SUMMARY:
            continue

        if count == session["last_summarized_count"]:
            continue

        logger.info(
            "Summarizing session %s (%d responses, last summarized at %d)",
            session_id, count, session["last_summarized_count"],
        )

        result = await summarize_responses(
            question=session["question"],
            responses=[
                {"student_name": r["student_name"], "answer": r["answer"]}
                for r in responses
            ],
        )

        if result is None:
            logger.warning("Summarization failed for session %s", session_id)
            # Push an error event so the frontend knows
            error_payload = {
                "error": True,
                "message": "Summarization temporarily unavailable. Retrying...",
                "response_count": count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for q in session["sse_queues"]:
                await q.put(error_payload)
            continue

        summary = SummaryPayload(
            themes=[Theme(**t) for t in result["themes"]],
            response_count=count,
            model_used=result.get("model_used"),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        session["last_summary"] = summary
        session["last_summarized_count"] = count

        payload = summary.model_dump()
        for q in session["sse_queues"]:
            await q.put(payload)

        logger.info("Summary pushed for session %s (%d themes)", session_id, len(summary.themes))


def _ensure_summarizer(session_id: str):
    """Start the summarizer background task if not already running."""
    session = sessions[session_id]
    task = session.get("summarizer_task")
    if task is None or task.done():
        session["summarizer_task"] = asyncio.create_task(_summarizer_loop(session_id))


# ---------------------------------------------------------------------------
# Cleanup old sessions
# ---------------------------------------------------------------------------

async def _cleanup_loop():
    """Periodically remove expired sessions."""
    while True:
        await asyncio.sleep(3600)  # every hour
        now = time.time()
        expired = [
            sid for sid, s in sessions.items()
            if now - s["created_at"] > SESSION_EXPIRY_HOURS * 3600
        ]
        for sid in expired:
            task = sessions[sid].get("summarizer_task")
            if task and not task.done():
                task.cancel()
            del sessions[sid]
            logger.info("Cleaned up expired session %s", sid)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(_cleanup_loop())
    yield
    cleanup_task.cancel()
    # Cancel all summarizer tasks
    for s in sessions.values():
        task = s.get("summarizer_task")
        if task and not task.done():
            task.cancel()


app = FastAPI(title="ThemePulse API", version="1.0.0", lifespan=lifespan)

# CORS - allow frontend
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "sessions": len(sessions)}


@app.post("/api/sessions", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest, request: Request):
    session_id = str(uuid.uuid4())[:8]
    admin_token = secrets.token_urlsafe(16)

    base_url = os.environ.get("FRONTEND_URL", str(request.base_url).rstrip("/"))

    sessions[session_id] = {
        "question": req.question,
        "admin_token": admin_token,
        "responses": [],
        "last_summary": None,
        "last_summarized_count": 0,
        "sse_queues": [],
        "created_at": time.time(),
        "summarizer_task": None,
    }

    student_url = f"{base_url}/session/{session_id}"
    admin_url = f"{base_url}/session/{session_id}/admin?token={admin_token}"

    logger.info("Created session %s", session_id)
    return CreateSessionResponse(
        session_id=session_id,
        admin_token=admin_token,
        student_url=student_url,
        admin_url=admin_url,
    )


@app.get("/api/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionInfoResponse(
        session_id=session_id,
        question=session["question"],
        response_count=len(session["responses"]),
    )


@app.post("/api/sessions/{session_id}/responses", response_model=SubmitResponseResponse)
async def submit_response(session_id: str, req: SubmitResponseRequest):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    response_id = str(uuid.uuid4())[:8]
    session["responses"].append({
        "id": response_id,
        "student_name": req.student_name,
        "answer": req.answer,
        "ts": time.time(),
    })

    # Start summarizer if enough responses
    if len(session["responses"]) >= MIN_RESPONSES_FOR_SUMMARY:
        _ensure_summarizer(session_id)

    logger.info(
        "Response added to session %s by %s (total: %d)",
        session_id, req.student_name, len(session["responses"]),
    )
    return SubmitResponseResponse(
        message="Thank you for your response!",
        response_id=response_id,
    )


@app.get("/api/sessions/{session_id}/stream")
async def stream_summary(
    session_id: str,
    request: Request,
    admin_token: str = Query(...),
):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["admin_token"] != admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    queue: asyncio.Queue = asyncio.Queue()
    session["sse_queues"].append(queue)

    async def event_generator() -> AsyncGenerator:
        import json
        try:
            # Send the last summary immediately if available
            if session["last_summary"] is not None:
                yield {
                    "event": "summary",
                    "data": json.dumps(session["last_summary"].model_dump()),
                }

            # Send response count heartbeat
            yield {
                "event": "status",
                "data": json.dumps({
                    "response_count": len(session["responses"]),
                    "min_required": MIN_RESPONSES_FOR_SUMMARY,
                }),
            }

            while True:
                if await request.is_disconnected():
                    break

                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=5.0)
                    if "error" in payload:
                        yield {"event": "error", "data": json.dumps(payload)}
                    else:
                        yield {"event": "summary", "data": json.dumps(payload)}
                except asyncio.TimeoutError:
                    # Send periodic heartbeat with response count
                    yield {
                        "event": "status",
                        "data": json.dumps({
                            "response_count": len(session["responses"]),
                            "min_required": MIN_RESPONSES_FOR_SUMMARY,
                        }),
                    }
        finally:
            if queue in session["sse_queues"]:
                session["sse_queues"].remove(queue)

    return EventSourceResponse(event_generator())


@app.get("/api/sessions/{session_id}/qr")
async def get_qr_code(session_id: str, request: Request):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    base_url = os.environ.get("FRONTEND_URL", str(request.base_url).rstrip("/"))
    student_url = f"{base_url}/session/{session_id}"

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(student_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
