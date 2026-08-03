"""
app.py
FastAPI entry point – Flower AI Expert.

Startup speed improvements:
  - classifier + knowledge base load in PARALLEL using asyncio.gather
  - chatbot (Ollama ping) is lightweight and fast
  - TF startup noise suppressed in classifier.py
  - No model downloads at runtime – everything is local

Endpoints
---------
  POST /predict   – upload flower image → name + confidence + card
  POST /chat      – chat about current flower
  POST /translate – offline translation
  GET  /health    – liveness probe
  GET  /flower    – current flower info
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
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
load_dotenv(Path(__file__).parent / ".env")

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

# Local modules – imported AFTER dotenv
import classifier
import chatbot
import knowledge
import translation
import auth
import analytics
from conversation import conversation_manager

BASE_DIR   = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"


# ---------------------------------------------------------------------------
# Hugging Face Public Model Downloader
# ---------------------------------------------------------------------------

def download_models(models_dir: Path) -> None:
    """
    Checks the public Hugging Face repository specified in HF_REPO_ID (.env)
    and downloads any missing model files into models_dir.
    Files that already exist locally are not re-downloaded.
    Does not require or use HF_TOKEN since the repository is public.
    """
    hf_repo_id = os.getenv("HF_REPO_ID", "").strip()
    if not hf_repo_id:
        logger.info("HF_REPO_ID is not set in environment (.env). Skipping Hugging Face model download.")
        return

    models_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Checking public Hugging Face repo '%s' for missing files...", hf_repo_id)

    try:
        from huggingface_hub import HfApi, hf_hub_download

        api = HfApi()
        repo_files = api.list_repo_files(repo_id=hf_repo_id)

        files_to_check = [
            f for f in repo_files
            if not f.startswith(".git") and f not in (".gitattributes", "README.md", "LICENSE", ".gitignore")
        ]

        if not files_to_check:
            logger.info("No model files found to sync in HF repository '%s'.", hf_repo_id)
            return

        downloaded_count = 0
        skipped_count = 0

        for file_name in files_to_check:
            target_path = models_dir / file_name

            if target_path.exists() and target_path.is_file() and target_path.stat().st_size > 0:
                logger.info("Local file exists, skipping download: %s", file_name)
                skipped_count += 1
                continue

            logger.info("Downloading missing file '%s' from public HF repo '%s'...", file_name, hf_repo_id)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            hf_hub_download(
                repo_id=hf_repo_id,
                filename=file_name,
                local_dir=models_dir,
            )
            logger.info("Successfully downloaded '%s' into %s", file_name, models_dir)
            downloaded_count += 1

        logger.info(
            "Hugging Face model sync completed. Downloaded: %d, Already existing: %d",
            downloaded_count,
            skipped_count,
        )

    except Exception as exc:
        logger.error("Failed to download model files from Hugging Face repo '%s': %s", hf_repo_id, exc)
        classifier_model_name = os.getenv("CLASSIFIER_MODEL_NAME", "flower_classifier.onnx").strip()
        critical_files = [
            classifier_model_name,
            "class_mapping.json",
            "flower_documents.json",
        ]
        missing_critical = [f for f in critical_files if not (models_dir / f).exists()]
        if missing_critical:
            raise RuntimeError(
                f"Missing critical model files {missing_critical} and Hugging Face download failed: {exc}"
            ) from exc
        logger.warning("Download error occurred, but existing local model files are present. Continuing startup.")


# ---------------------------------------------------------------------------
# Lifespan – parallel loading for maximum speed
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.perf_counter()
    logger.info("=== Flower AI Expert – starting up ===")

    loop = asyncio.get_event_loop()

    # ── Step 1: Ensure missing models are downloaded from HF Repo ─────────────
    logger.info("Checking Hugging Face repository for missing models …")
    await loop.run_in_executor(None, download_models, MODELS_DIR)

    # Pre-import transformers to prevent thread import race condition
    import transformers

    logger.info("Loading all models in parallel …")
    await asyncio.gather(
        loop.run_in_executor(None, classifier.load, MODELS_DIR),
        loop.run_in_executor(None, knowledge.load,  MODELS_DIR),
        loop.run_in_executor(None, chatbot.load),
        loop.run_in_executor(None, translation.preload),
    )

    elapsed = time.perf_counter() - t0
    logger.info("=== All models ready in %.1f s. Active Classifier: '%s'. Accepting requests. ===", elapsed, classifier.get_model_name())

    yield

    logger.info("=== Flower AI Expert – shutdown ===")
    chatbot.unload()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Flower AI Expert API",
    version="1.0.0",
    description="AI-powered flower identification and botanical chatbot.",
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

class PredictResponse(BaseModel):
    session_id: Optional[str] = None
    flower: str
    confidence: float
    summary: str
    card: dict

class ChatResponse(BaseModel):
    answer: str

class TranslateResponse(BaseModel):
    translated: str
    language: str

class FlowerInfoResponse(BaseModel):
    flower: Optional[str] = None
    summary: Optional[str] = None
    card: Optional[dict] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
async def health():
    """Liveness probe."""
    return {
        "status": "ok",
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


@app.post("/predict", response_model=PredictResponse, tags=["flower"])
async def predict(
    raw_request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(auth.require_authenticated_user),
):
    """Upload a flower image. Returns name, confidence, and botanical card."""

    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file received.")

    logger.info("=" * 60)
    logger.info("Received File")
    logger.info("Filename      : %s", file.filename)
    logger.info("Content Type  : %s", file.content_type)
    logger.info("Image Size    : %.2f KB", len(image_bytes) / 1024)
    logger.info("=" * 60)

    start_time = time.perf_counter()
    loop = asyncio.get_event_loop()

    user_id = current_user.get("user_id") if current_user else None
    user_name = current_user.get("name") if current_user else None
    user_email = current_user.get("email") if current_user else None

    try:
        flower_name, confidence, doc_idx = await loop.run_in_executor(
            None,
            classifier.predict,
            image_bytes,
        )
    except Exception as exc:
        logger.exception("Classifier Error")
        background_tasks.add_task(
            analytics.AnalyticsLogger.log_classification,
            session_id=f"session_err_{int(time.time() * 1000)}",
            predicted_flower="Unknown",
            confidence=0.0,
            classification_time_ms=0.0,
            total_processing_time_ms=(time.perf_counter() - start_time) * 1000,
            filename=file.filename or "",
            content_type=file.content_type or "",
            file_size_bytes=len(image_bytes),
            user_id=user_id,
            username=user_name,
            email=user_email,
            status="error",
            error_info=str(exc),
            request=raw_request,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Classifier error: {exc}"
        )

    classifier_time = time.perf_counter() - start_time
    logger.info("Classifier prediction time: %.3fs", classifier_time)
    logger.info("Prediction -> %s (%.2f%%)", flower_name, confidence)

    card = knowledge.get_flower_summary(doc_idx, flower_name)
    flower_info = knowledge.get_flower_info(flower_name)
    summary = flower_info.get("description") or card.get("description", "")

    sid = f"session_{flower_name.lower().replace(' ', '_')}_{int(time.time() * 1000)}"

    conversation_manager.set_flower(
        flower_name,
        summary,
        session_id=sid,
    )

    total_time = time.perf_counter() - start_time
    logger.info("Total /predict request time: %.3fs", total_time)

    # Schedule background tasks after HTTP response is sent immediately
    mime = file.content_type or "image/jpeg"
    image_b64 = f"data:{mime};base64," + base64.b64encode(image_bytes).decode("utf-8")

    background_tasks.add_task(
        knowledge.save_search_history,
        flower_name=flower_name,
        confidence=round(confidence, 2),
        summary=summary,
        card=card,
        filename=file.filename,
        session_id=sid,
        image_preview=image_b64,
        user_id=user_id,
        user_email=user_email,
    )

    background_tasks.add_task(
        analytics.AnalyticsLogger.log_classification,
        session_id=sid,
        predicted_flower=flower_name,
        confidence=confidence,
        classification_time_ms=classifier_time * 1000,
        total_processing_time_ms=total_time * 1000,
        filename=file.filename or "",
        content_type=file.content_type or "",
        file_size_bytes=len(image_bytes),
        user_id=user_id,
        username=user_name,
        email=user_email,
        status="success",
        request=raw_request,
    )

    return PredictResponse(
        session_id=sid,
        flower=flower_name,
        confidence=round(confidence, 2),
        summary=summary,
        card=card,
    )


@app.get("/history", tags=["history"])
async def get_history(request: Request, limit: int = 100):
    """Retrieve per-user flower search, predictions, image previews, and AI chat history saved in MongoDB Atlas."""
    user = auth.get_current_user(request)
    user_id = user.get("user_id") if user else None
    user_email = user.get("email") if user else None
    records = knowledge.get_search_history(limit=limit, user_id=user_id, user_email=user_email)
    return {"history": records}


class SaveHistoryRequest(BaseModel):
    session_id: Optional[str] = None
    flower: str
    confidence: Optional[float] = 98.5
    summary: Optional[str] = ""
    card: Optional[dict] = {}
    filename: Optional[str] = ""
    image_preview: Optional[str] = ""
    messages: Optional[list] = []


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
        "which flowers",
        "flowers that",
        "flowers for",
        "best flowers",
        "flower for",
        "bloom in",
        "attract",
        "indoor gardening",
        "garden",
        "season",
        "winter",
        "spring",
        "summer",
        "fall",
        "autumn",
        "recommend",
        "bouquet",
        "planting",
        "landscaping",
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

    # Decide whether this is a general query or direct flower follow-up
    if not flower_name or _is_general_question(user_message, flower_name):
        logger.info("General knowledge query detected. Using FAISS search.")
        search_k = _determine_search_k(user_message)
        try:
            context_docs = await asyncio.get_event_loop().run_in_executor(
                None,
                knowledge.search,
                user_message,
                search_k,
            )
        except Exception as exc:
            logger.warning("FAISS search failed: %s", exc)
            context_docs = [conversation_manager.current_summary or ""]
    else:
        logger.info("Follow-up question detected. Using direct flower lookup.")
        flower_info = knowledge.get_flower_info(flower_name)
        context_text = knowledge.build_flower_context(flower_info)
        if context_text:
            context_docs = [context_text]
        else:
            context_docs = [conversation_manager.current_summary or ""]

    retrieval_time = time.perf_counter() - start_time
    logger.info("Knowledge retrieval time: %.3fs", retrieval_time)

    # Snapshot history BEFORE adding the current user turn
    history = conversation_manager.get_history_as_dicts()
    conversation_manager.add_user_message(user_message)

    # Run LLM in thread pool so async endpoints stay responsive
    loop = asyncio.get_event_loop()
    try:
        llm_start = time.perf_counter()
        # Use chatbot's async wrapper which employs a shared ThreadPoolExecutor
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
    sid = conversation_manager.current_session_id or f"session_{flower_name.lower().replace(' ', '_')}" if flower_name else f"session_{int(time.time() * 1000)}"
    total_time = time.perf_counter() - start_time
    logger.info("Total /chat request time: %.3fs", total_time)

    # Schedule background tasks after HTTP response is sent immediately
    background_tasks.add_task(
        knowledge.save_search_history,
        flower_name=flower_name or "AI Botanical Chat",
        confidence=98.5,
        summary=conversation_manager.current_summary or "Interactive AI Botanical Conversation",
        session_id=sid,
        messages=conversation_manager.get_history_as_dicts(),
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
    """Chat about flowers or plant care with real-time ChatGPT-style token streaming."""
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    flower_name = conversation_manager.current_flower or ""
    start_time = time.perf_counter()

    if not flower_name or _is_general_question(user_message, flower_name):
        logger.info("General knowledge query detected. Using FAISS search.")
        search_k = _determine_search_k(user_message)
        try:
            context_docs = await asyncio.get_event_loop().run_in_executor(
                None,
                knowledge.search,
                user_message,
                search_k,
            )
        except Exception as exc:
            logger.warning("FAISS search failed: %s", exc)
            context_docs = [conversation_manager.current_summary or ""]
    else:
        logger.info("Follow-up question detected. Using direct flower lookup.")
        flower_info = knowledge.get_flower_info(flower_name)
        context_text = knowledge.build_flower_context(flower_info)
        if context_text:
            context_docs = [context_text]
        else:
            context_docs = [conversation_manager.current_summary or ""]

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

            logger.info(
                "⏱️ [TIMING] Stream finished in %.2f ms | Total Request Time: %.2f ms | Length: %d chars",
                total_stream_time_ms,
                total_req_time_ms,
                len(clean_answer),
            )

            # Defer history saving & analytics logging to non-blocking task after stream finishes
            sid = conversation_manager.current_session_id or (f"session_{flower_name.lower().replace(' ', '_')}" if flower_name else f"session_chat_{int(time.time() * 1000)}")
            asyncio.create_task(asyncio.to_thread(
                knowledge.save_search_history,
                flower_name or "AI Botanical Chat",
                98.5,
                conversation_manager.current_summary or "Interactive AI Botanical Conversation",
                {},
                "",
                sid,
                conversation_manager.get_history_as_dicts(),
                None,
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


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
        log_level="info",
    )
