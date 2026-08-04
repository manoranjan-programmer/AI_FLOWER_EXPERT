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

# ---------------------------------------------------------------------------
# Lifespan – lightweight startup (<200MB RAM)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Classifier Service Started")
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
