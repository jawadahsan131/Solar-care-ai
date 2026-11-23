from __future__ import annotations

import logging
import threading
import time
from functools import lru_cache
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, status
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.deps import AuthenticatedUser
from app.services.rag import rag_service

router = APIRouter(tags=["chat"])
logger = logging.getLogger("solar_care.chat")

RATE_LIMIT_WINDOW_SECONDS = 60
MAX_CHAT_REQUESTS_PER_WINDOW = 20
_chat_requests: dict[str, list[float]] = {}
_rate_limit_lock = threading.Lock()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    language: Literal["en", "roman_urdu"] = "en"

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    source_details: list[str]
    used_chunks: int


def _enforce_chat_rate_limit(user_id: str) -> None:
    now = time.monotonic()
    with _rate_limit_lock:
        recent = [
            timestamp
            for timestamp in _chat_requests.get(user_id, [])
            if now - timestamp < RATE_LIMIT_WINDOW_SECONDS
        ]
        if len(recent) >= MAX_CHAT_REQUESTS_PER_WINDOW:
            _chat_requests[user_id] = recent
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Chat limit reached. Please wait a minute and try again.",
            )
        recent.append(now)
        _chat_requests[user_id] = recent


@lru_cache(maxsize=1)
def _get_chat_gemini_client(api_key: str) -> genai.Client:
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=15_000),
    )


def _generate_answer(prompt: str) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("The chat service is not configured with a Gemini API key.")
    if not settings.gemini_model:
        raise RuntimeError("The chat service does not have a Gemini model configured.")
    client = _get_chat_gemini_client(settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )
    answer = (response.text or "").strip()
    if not answer:
        raise RuntimeError("Gemini returned an empty answer.")
    return answer


@router.post("/chat", response_model=ChatResponse)
async def chat_with_references(
    payload: ChatRequest,
    user: AuthenticatedUser,
) -> ChatResponse:
    _enforce_chat_rate_limit(user["id"])
    try:
        chunks = await run_in_threadpool(
            rag_service.retrieve,
            payload.message,
            k=5,
        )
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        logger.exception("RAG retrieval failed for user_id=%s", user["id"])
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reference search is temporarily unavailable. Please try again later.",
        ) from exc

    logger.info(
        "RAG retrieval user_id=%s scores_and_sources=%s",
        user["id"],
        [
            (chunk["source"], chunk["heading"], round(chunk["score"], 4))
            for chunk in chunks
        ],
    )
    if not chunks:
        answer = (
            "Is sawal ka jawab dene ke liye koi matching reference material nahi mila."
            if payload.language == "roman_urdu"
            else "I couldn't find matching reference material for that question."
        )
        return ChatResponse(
            answer=answer,
            sources=[],
            source_details=[],
            used_chunks=0,
        )

    prompt = rag_service.build_answer_prompt(
        payload.message,
        chunks,
        payload.language,
    )
    try:
        answer = await run_in_threadpool(_generate_answer, prompt)
    except (RuntimeError, errors.APIError, httpx.HTTPError, TimeoutError, OSError) as exc:
        logger.exception("Gemini chat request failed for user_id=%s", user["id"])
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The chat service is temporarily unavailable. Please try again later.",
        ) from exc

    sources = list(dict.fromkeys(chunk["source"] for chunk in chunks))
    source_details = list(
        dict.fromkeys(
            f'{chunk["source"]} → {chunk["heading"]}'
            for chunk in chunks
        )
    )
    return ChatResponse(
        answer=answer,
        sources=sources,
        source_details=source_details,
        used_chunks=len(chunks),
    )
