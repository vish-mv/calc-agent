"""HTTP wrapper exposing the calc agent as an AMP Docker API agent.

Endpoints:
    GET  /healthz  - liveness probe
    POST /chat     - chat with the agent: {"session_id": "...", "message": "..."}

Special message commands (for platform validation):
    !file  - read the file mounted at FILE_CHECK_PATH (default
             /config/instructions.txt) and return its contents. Used to verify
             console file mounts work across isolation tiers (runc/gVisor/Kata).
"""

import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from agent import build_agent

FILE_CHECK_PATH = os.getenv("FILE_CHECK_PATH", "/config/instructions.txt")

app = FastAPI(title="Calc Agent")

_executor = None
_executor_error = None


class ChatRequest(BaseModel):
    # Field names mirror the AMP standard chat contract (what the console's
    # try-it chat UI sends); extra fields are ignored by pydantic's default.
    session_id: str = "default"
    message: str
    context: dict = {}


class ChatResponse(BaseModel):
    response: str


def get_executor():
    """Build the agent once, lazily. A missing OPENAI_API_KEY must not crash
    the server - the /chat endpoint reports it instead, so deployment and the
    file-mount check stay testable without a key."""
    global _executor, _executor_error
    if _executor is None and _executor_error is None:
        try:
            _executor = build_agent()
        except Exception as exc:  # noqa: BLE001
            _executor_error = str(exc)
    return _executor, _executor_error


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    message = req.message.strip()

    if message == "!file":
        path = Path(FILE_CHECK_PATH)
        try:
            content = path.read_text()
            return ChatResponse(
                response=f"file mount OK ({FILE_CHECK_PATH}):\n{content}"
            )
        except OSError as exc:
            return ChatResponse(
                response=f"file mount check FAILED ({FILE_CHECK_PATH}): {exc}"
            )

    executor, error = get_executor()
    if executor is None:
        return ChatResponse(response=f"agent unavailable: {error}")

    result = executor.invoke({"input": message})
    return ChatResponse(response=result["output"])
