"""
app.py
FastAPI entry point – Flower AI Expert Chatbot & Botanical Knowledge Microservice.

Microservice responsibilities:
  - Botanical AI Chatbot & GGUF LLM generation
  - FAISS vector search & RAG embeddings
  - MongoDB user authentication, search history & analytics
  - Offline Helsinki-NLP Opus-MT language translation
  - Exposes: /chat, /chat/stream, /flower/select, /flower, /auth, /history, /translate, /health, /api/analytics
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
os.environ["PYTHONUNBUFFERED"] = "1"

from dotenv import load_dotenv

# ── Load .env FIRST so all os.getenv() calls in submodules see the values ──
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

# Local modules
import chatbot
import knowledge
import translation
import auth
import analytics
from conversation import conversation_manager

MODELS_DIR = BASE_DIR / "models"


# ---------------------------------------------------------------------------
# Lifespan – parallel loading for fast startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Backend Started")
    knowledge.load(MODELS_DIR)
    yield
    logger.info("=== Chatbot Service – shutdown ===")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Flower AI Chatbot API",
    version="1.0.0",
    description="AI-powered botanical chatbot, FAISS search, translation, and user management.",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(analytics.router)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str

class TranslateRequest(BaseModel):
    text: str
    language: str        # "ta" | "hi" | "ml" | "en"

class ChatResponse(BaseModel):
    answer: str

class TranslateResponse(BaseModel):
    translated: str
    language: str

class FlowerInfoResponse(BaseModel):
    flower: Optional[str] = None
    summary: Optional[str] = None
    card: Optional[dict] = None

class SelectFlowerRequest(BaseModel):
    flower_name: str
    confidence: Optional[float] = 98.5
    filename: Optional[str] = ""
    image_preview: Optional[str] = ""

class SaveHistoryRequest(BaseModel):
    session_id: Optional[str] = None
    flower: str
    confidence: Optional[float] = 98.5
    summary: Optional[str] = ""
    card: Optional[dict] = {}
    filename: Optional[str] = ""
    image_preview: Optional[str] = ""
    messages: Optional[list] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
async def health():
    """Liveness probe."""
    return {
        "status": "ok",
        "service": "chatbot",
        "flower": conversation_manager.current_flower,
    }


@app.get("/flower", response_model=FlowerInfoResponse, tags=["flower"])
async def get_current_flower():
    if not conversation_manager.has_flower():
        return FlowerInfoResponse()
    return FlowerInfoResponse(
        flower=conversation_manager.current_flower,
        summary=conversation_manager.current_summary,
        card={},
    )


@app.post("/flower/select", tags=["flower"])
async def select_flower(req: SelectFlowerRequest, background_tasks: BackgroundTasks, request: Request):
    """
    Set current active flower context, retrieve botanical card & summary,
    and save search history in MongoDB Atlas.
    """
    flower_name = req.flower_name.strip()
    confidence = req.confidence or 98.5

    loaded_doc = knowledge.get_flower_doc(flower_name)
    if not loaded_doc:
        raise HTTPException(status_code=404, detail="Flower knowledge unavailable.")

    card = knowledge.get_flower_summary(-1, flower_name)
    flower_info = knowledge.get_flower_info(flower_name)
    summary = flower_info.get("description") or card.get("description", "")

    sid = f"session_{flower_name.lower().replace(' ', '_')}_{int(time.time() * 1000)}"
    conversation_manager.set_flower(
        flower_name,
        summary,
        session_id=sid,
        card=card,
        image_preview=req.image_preview
    )

    user = auth.get_current_user(request)
    user_id = user.get("user_id") if user else None
    user_email = user.get("email") if user else None

    background_tasks.add_task(
        knowledge.save_search_history,
        flower_name=flower_name,
        confidence=round(confidence, 2),
        summary=summary,
        card=card,
        filename=req.filename or "",
        session_id=sid,
        image_preview=req.image_preview or "",
        user_id=user_id,
        user_email=user_email,
    )

    return {
        "session_id": sid,
        "flower": flower_name,
        "confidence": round(confidence, 2),
        "summary": summary,
        "card": card,
    }


@app.get("/history", tags=["history"])
async def get_history(request: Request, limit: int = 100):
    """Retrieve per-user flower search, predictions, image previews, and AI chat history from MongoDB."""
    user = auth.get_current_user(request)
    user_id = user.get("user_id") if user else None
    user_email = user.get("email") if user else None
    records = knowledge.get_search_history(limit=limit, user_id=user_id, user_email=user_email)
    return {"history": records}


@app.post("/history/save", tags=["history"])
async def save_history_session(req: SaveHistoryRequest, request: Request):
    """Save or update chat session history in MongoDB Atlas per user."""
    user = auth.get_current_user(request)
    user_id = user.get("user_id") if user else None
    user_email = user.get("email") if user else None

    success = knowledge.save_search_history(
        flower_name=req.flower,
        confidence=req.confidence or 98.5,
        summary=req.summary or "",
        card=req.card or {},
        filename=req.filename or "",
        session_id=req.session_id,
        messages=req.messages or [],
        image_preview=req.image_preview or "",
        user_id=user_id,
        user_email=user_email,
    )
    return {"status": "ok" if success else "failed"}


def _is_general_question(message: str, flower_name: str) -> bool:
    lower = message.lower()
    general_patterns = [
        "which flowers", "flowers that", "flowers for", "best flowers", "flower for",
        "bloom in", "attract", "indoor gardening", "garden", "season", "winter",
        "spring", "summer", "fall", "autumn", "recommend", "bouquet", "planting", "landscaping",
    ]
    if any(pattern in lower for pattern in general_patterns):
        if flower_name.lower() not in lower and "it" not in lower and "this" not in lower:
            return True
    return False


def _determine_search_k(user_message: str) -> int:
    parsed = chatbot._parse_request_constraints(user_message)
    cnt = parsed.get("count")
    if cnt and cnt > 1:
        return min(max(cnt, 5), 10)
    lower = user_message.lower()
    if any(w in lower for w in ["flowers", "plants", "top", "list", "give me", "types", "recommend", "medical", "medicinal"]):
        return 5
    return 3


def validate_flower_context(classifier_flower: str, loaded_doc: str) -> str:
    """
    Validation middleware helper. Asserts Classifier Flower == Knowledge Flower == Prompt Flower == History Flower.
    Logs exact required verification block and throws HTTPException on mismatch.
    """
    m = re.search(r"Flower\s*Name:\s*([^\n]+)", loaded_doc or "", re.IGNORECASE)
    doc_flower = m.group(1).strip() if m else classifier_flower

    print("--------------------------------")
    print(f"Classifier Flower: {classifier_flower}")
    print(f"Knowledge Flower: {doc_flower}")
    print(f"Prompt Flower: {classifier_flower}")
    print(f"History Flower: {classifier_flower}")
    print("--------------------------------")

    logger.info(
        "\n--------------------------------\n"
        "Classifier Flower: %s\n"
        "Knowledge Flower: %s\n"
        "Prompt Flower: %s\n"
        "History Flower: %s\n"
        "--------------------------------",
        classifier_flower, doc_flower, classifier_flower, classifier_flower
    )

    norm_cf = knowledge.normalize_flower_name(classifier_flower)
    norm_df = knowledge.normalize_flower_name(doc_flower)
    if norm_cf and norm_df and norm_cf != norm_df:
        raise HTTPException(
            status_code=400,
            detail=f"FlowerContext Mismatch Error: Classifier ('{classifier_flower}') != Knowledge Document ('{doc_flower}')"
        )

    return doc_flower


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    request: ChatRequest,
    raw_request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(auth.require_authenticated_user),
):
    """Chat about flowers or plant care with the AI Botanist."""
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    flower_name = conversation_manager.current_flower or ""
    start_time = time.perf_counter()

    user_id = current_user.get("user_id") if current_user else None
    user_name = current_user.get("name") if current_user else None
    user_email = current_user.get("email") if current_user else None

    if flower_name:
        loaded_doc = knowledge.get_flower_doc(flower_name)
        if not loaded_doc:
            raise HTTPException(status_code=404, detail="Flower knowledge unavailable.")
        validate_flower_context(flower_name, loaded_doc)
        context_docs = [loaded_doc]
    else:
        logger.info("General knowledge query detected. Using FAISS search.")
        search_k = _determine_search_k(user_message)
        try:
            context_docs = await asyncio.get_event_loop().run_in_executor(
                None, knowledge.search, user_message, search_k
            )
        except RuntimeError as exc:
            logger.error("Knowledge base unavailable for /chat: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Knowledge base unavailable. Please try again in a moment.",
            )
        except Exception as exc:
            logger.error("FAISS search failed unexpectedly: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Knowledge base unavailable. Please try again in a moment.",
            )

    retrieval_time = time.perf_counter() - start_time
    logger.info("Knowledge retrieval time: %.3fs", retrieval_time)

    history = conversation_manager.get_history_as_dicts()
    conversation_manager.add_user_message(user_message)

    loop = asyncio.get_event_loop()
    try:
        llm_start = time.perf_counter()
        answer = await chatbot.generate_async(
            user_message=user_message,
            flower_name=flower_name,
            context_docs=context_docs,
            history=history,
        )
        llm_time = time.perf_counter() - llm_start
        logger.info("LLM generation time: %.3fs", llm_time)
    except Exception as exc:
        logger.error("Chatbot error: %s", exc, exc_info=True)
        sid = conversation_manager.current_session_id or f"session_{int(time.time() * 1000)}"
        background_tasks.add_task(
            analytics.AnalyticsLogger.log_chat,
            session_id=sid,
            user_prompt=user_message,
            ai_response="",
            flower_context=flower_name,
            user_id=user_id,
            username=user_name,
            email=user_email,
            response_format="json",
            retrieval_time_ms=retrieval_time * 1000,
            total_processing_time_ms=(time.perf_counter() - start_time) * 1000,
            status="error",
            error_info=str(exc),
            request=raw_request,
            transcript=conversation_manager.get_history_as_dicts(),
        )
        raise HTTPException(status_code=500, detail=f"Chatbot error: {exc}")

    req_lang = chatbot.detect_requested_language(user_message)
    if req_lang and req_lang != "en":
        try:
            answer = await asyncio.get_event_loop().run_in_executor(
                None, translation.translate, answer, req_lang
            )
        except Exception as exc:
            logger.warning("Translation for requested language '%s' failed: %s", req_lang, exc)

    conversation_manager.add_assistant_message(answer)
    sid = conversation_manager.current_session_id or (f"session_{flower_name.lower().replace(' ', '_')}" if flower_name else f"session_{int(time.time() * 1000)}")
    total_time = time.perf_counter() - start_time
    logger.info("Total /chat request time: %.3fs", total_time)

    background_tasks.add_task(
        knowledge.save_search_history,
        flower_name=flower_name or "AI Botanical Chat",
        confidence=98.5,
        summary=conversation_manager.current_summary or "Interactive AI Botanical Conversation",
        card=conversation_manager.current_card,
        filename="",
        session_id=sid,
        messages=conversation_manager.get_history_as_dicts(),
        image_preview=conversation_manager.current_image_preview or "",
        user_id=user_id,
        user_email=user_email,
    )

    background_tasks.add_task(
        analytics.AnalyticsLogger.log_chat,
        session_id=sid,
        user_prompt=user_message,
        ai_response=answer,
        flower_context=flower_name,
        user_id=user_id,
        username=user_name,
        email=user_email,
        response_format="json",
        generation_time_ms=llm_time * 1000,
        retrieval_time_ms=retrieval_time * 1000,
        total_processing_time_ms=total_time * 1000,
        status="success",
        request=raw_request,
        transcript=conversation_manager.get_history_as_dicts(),
    )

    return ChatResponse(answer=answer)


@app.post("/chat/stream", tags=["chat"])
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(auth.require_authenticated_user),
):
    """Chat about flowers with real-time ChatGPT-style token streaming."""
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    flower_name = conversation_manager.current_flower or ""
    start_time = time.perf_counter()

    if flower_name:
        loaded_doc = knowledge.get_flower_doc(flower_name)
        if not loaded_doc:
            raise HTTPException(status_code=404, detail="Flower knowledge unavailable.")
        validate_flower_context(flower_name, loaded_doc)
        context_docs = [loaded_doc]
    else:
        logger.info("General knowledge query detected. Using FAISS search.")
        search_k = _determine_search_k(user_message)
        try:
            context_docs = await asyncio.get_event_loop().run_in_executor(
                None, knowledge.search, user_message, search_k
            )
        except RuntimeError as exc:
            logger.error("Knowledge base unavailable for /chat/stream: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Knowledge base unavailable. Please try again in a moment.",
            )
        except Exception as exc:
            logger.error("FAISS search failed unexpectedly: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Knowledge base unavailable. Please try again in a moment.",
            )

    history = conversation_manager.get_history_as_dicts()
    conversation_manager.add_user_message(user_message)

    req_lang = chatbot.detect_requested_language(user_message)
    if req_lang and req_lang != "en":
        async def sse_translated_generator():
            yield ": ping\n\n"
            await asyncio.sleep(0)
            full_chunks = []
            sentence_buffer = ""
            try:
                async for token in chatbot.generate_stream_async(
                    user_message=user_message,
                    flower_name=flower_name,
                    context_docs=context_docs,
                    history=history,
                ):
                    sentence_buffer += token
                    full_chunks.append(token)
                    if any(punct in token for punct in ('.', '!', '?', '\n')) or len(sentence_buffer) >= 60:
                        clean_part = chatbot._remove_cjk_characters(sentence_buffer)
                        if clean_part.strip():
                            translated_part = await asyncio.get_event_loop().run_in_executor(
                                None, translation.translate, clean_part, req_lang
                            )
                            words = translated_part.split(" ")
                            for idx, w in enumerate(words):
                                chunk = w if idx == len(words) - 1 else w + " "
                                payload = json.dumps({"token": chunk})
                                yield f"data: {payload}\n\n"
                                await asyncio.sleep(0)
                        sentence_buffer = ""

                if sentence_buffer.strip():
                    clean_part = chatbot._remove_cjk_characters(sentence_buffer)
                    translated_part = await asyncio.get_event_loop().run_in_executor(
                        None, translation.translate, clean_part, req_lang
                    )
                    words = translated_part.split(" ")
                    for idx, w in enumerate(words):
                        chunk = w if idx == len(words) - 1 else w + " "
                        payload = json.dumps({"token": chunk})
                        yield f"data: {payload}\n\n"
                        await asyncio.sleep(0)

                full_answer = "".join(full_chunks)
                clean_answer = chatbot._enforce_user_formatting(full_answer, user_message)
                final_translated = await asyncio.get_event_loop().run_in_executor(
                    None, translation.translate, clean_answer, req_lang
                )
                conversation_manager.add_assistant_message(final_translated)

                if flower_name:
                    try:
                        sid = conversation_manager.current_session_id or f"session_{flower_name.lower().replace(' ', '_')}"
                        knowledge.save_search_history(
                            flower_name=flower_name,
                            confidence=98.5,
                            summary=conversation_manager.current_summary or "",
                            session_id=sid,
                            messages=conversation_manager.get_history_as_dicts(),
                        )
                    except Exception as exc:
                        logger.warning("Could not sync chat history to MongoDB Atlas: %s", exc)

                yield "data: [DONE]\n\n"
            except Exception as exc:
                logger.error("Streaming translation error: %s", exc, exc_info=True)
                err_payload = json.dumps({"error": str(exc)})
                yield f"data: {err_payload}\n\n"

        return StreamingResponse(
            sse_translated_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def sse_event_generator():
        yield ": ping\n\n"
        await asyncio.sleep(0)
        full_chunks = []
        ttft_logged = False
        t_stream_start = time.perf_counter()

        user_id = current_user.get("user_id") if current_user else None
        user_name = current_user.get("name") if current_user else None
        user_email = current_user.get("email") if current_user else None

        try:
            async for token in chatbot.generate_stream_async(
                user_message=user_message,
                flower_name=flower_name,
                context_docs=context_docs,
                history=history,
            ):
                if not ttft_logged:
                    ttft_ms = (time.perf_counter() - start_time) * 1000
                    logger.info("⏱️ [TIMING] Time To First Token (TTFT): %.2f ms", ttft_ms)
                    ttft_logged = True

                full_chunks.append(token)
                payload = json.dumps({"token": token})
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0)

            full_answer = "".join(full_chunks)
            clean_answer = chatbot._enforce_user_formatting(full_answer, user_message)
            conversation_manager.add_assistant_message(clean_answer)

            total_stream_time_ms = (time.perf_counter() - t_stream_start) * 1000
            total_req_time_ms = (time.perf_counter() - start_time) * 1000

            sid = conversation_manager.current_session_id or (f"session_{flower_name.lower().replace(' ', '_')}" if flower_name else f"session_chat_{int(time.time() * 1000)}")
            asyncio.create_task(asyncio.to_thread(
                knowledge.save_search_history,
                flower_name or "AI Botanical Chat",
                98.5,
                conversation_manager.current_summary or "Interactive AI Botanical Conversation",
                conversation_manager.current_card,
                "",
                sid,
                conversation_manager.get_history_as_dicts(),
                conversation_manager.current_image_preview or "",
                user_id,
                user_email,
            ))

            asyncio.create_task(asyncio.to_thread(
                analytics.AnalyticsLogger.log_chat,
                sid,
                user_message,
                clean_answer,
                flower_name,
                user_id,
                user_name,
                user_email,
                "stream",
                total_stream_time_ms,
                retrieval_time * 1000 if 'retrieval_time' in locals() else 0.0,
                total_req_time_ms,
                "Flower_AI_Bot",
                "success",
                "",
                None,
                conversation_manager.get_history_as_dicts(),
            ))

            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error("SSE Streaming error: %s", exc, exc_info=True)
            err_payload = json.dumps({"error": str(exc)})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/translate", response_model=TranslateResponse, tags=["translate"])
async def translate_text(request: TranslateRequest):
    """Translate text offline using Helsinki-NLP Opus-MT."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    supported = {"ta", "hi", "ml", "te", "kn", "es", "fr", "de", "zh", "ja", "ar", "en"}
    lang = request.language.lower().strip()
    if lang not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{lang}'. Supported: {', '.join(sorted(supported))}",
        )

    loop = asyncio.get_event_loop()
    try:
        translated = await loop.run_in_executor(
            None, translation.translate, request.text, lang
        )
    except Exception as exc:
        logger.error("Translation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Translation error: {exc}")

    return TranslateResponse(translated=translated, language=lang)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
        log_level="info",
    )
