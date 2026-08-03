"""
app.py
FastAPI Entry Point – Flower AI Expert Classifier Microservice.
Dedicated lightweight service for image prediction using ONNX Runtime.
Exposes ONLY:
  POST /predict
  GET  /health
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env FIRST
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

import classifier

MODELS_DIR = BASE_DIR / "models"


def download_classifier_models(models_dir: Path) -> None:
    """Sync ONNX classifier model and mapping JSON files from Hugging Face if missing."""
    hf_repo_id = os.getenv("HF_REPO_ID", "").strip()
    if not hf_repo_id:
        logger.info("HF_REPO_ID is not set in environment. Skipping Hugging Face download.")
        return

    models_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Checking public Hugging Face repo '%s' for classifier files...", hf_repo_id)

    classifier_model = os.getenv("CLASSIFIER_MODEL_NAME", "flower_classifier.onnx").strip()
    required_files = [classifier_model, "class_mapping.json", "flower_documents.json", "class_to_flower.json"]

    try:
        from huggingface_hub import hf_hub_download
        for fname in required_files:
            target = models_dir / fname
            if not target.exists() or target.stat().st_size == 0:
                logger.info("Downloading '%s' from HF repo '%s'...", fname, hf_repo_id)
                try:
                    hf_hub_download(repo_id=hf_repo_id, filename=fname, local_dir=models_dir)
                except Exception as exc:
                    logger.warning("Could not fetch '%s' from HF: %s", fname, exc)
            else:
                logger.info("Local classifier file exists: %s", fname)
    except Exception as exc:
        logger.error("Hugging Face model sync failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Backend Started")
    yield
    logger.info("=== Classifier Service – shutdown ===")


app = FastAPI(
    title="Flower AI Classifier API",
    version="1.0.0",
    description="Microservice for flower image classification.",
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


class FlowerContextModel(BaseModel):
    flower_name: str
    confidence: float
    session_id: str

class PredictResponse(BaseModel):
    flower_name: str
    confidence: float
    session_id: str
    flower_context: FlowerContextModel


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "classifier", "model": classifier.get_model_name()}


@app.post("/predict", response_model=PredictResponse, tags=["classification"])
async def predict(file: UploadFile = File(...)):
    """Upload a flower image file. Returns flower_name, confidence, session_id, and FlowerContext."""
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file received.")

    start_time = time.perf_counter()
    loop = asyncio.get_event_loop()

    try:
        flower_name, confidence, _ = await loop.run_in_executor(
            None,
            classifier.predict,
            image_bytes,
        )
    except Exception as exc:
        logger.exception("Classifier Prediction Error")
        raise HTTPException(status_code=500, detail=f"Classifier error: {exc}")

    elapsed = time.perf_counter() - start_time
    logger.info("Prediction completed in %.3fs -> %s (%.2f%%)", elapsed, flower_name, confidence)

    sid = f"session_{flower_name.lower().replace(' ', '_')}_{int(time.time() * 1000)}"
    ctx = FlowerContextModel(
        flower_name=flower_name,
        confidence=round(confidence, 2),
        session_id=sid
    )

    return PredictResponse(
        flower_name=flower_name,
        confidence=round(confidence, 2),
        session_id=sid,
        flower_context=ctx
    )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host=host, port=port)
