"""
download_hf_models.py
Download all Hugging Face models and files for backend-classifier.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s")
logger = logging.getLogger("classifier-hf-loader")

HF_REPO_ID = os.getenv("HF_REPO_ID", "manoranjan-programmer/flower-ai-model").strip()
MODELS_DIR = BASE_DIR / "models"

FILES_TO_DOWNLOAD = [
    "flower_classifier.onnx",
    "class_mapping.json",
    "class_names.json",
    "class_to_flower.json",
    "flower_documents.json",
    "flower_embeddings.npy",
    "flower_faiss.index",
    "flower_lookup.json",
    "flower_training_data.json",
]

def main():
    logger.info("=== Downloading Hugging Face models for backend-classifier ===")
    logger.info("Repository: %s", HF_REPO_ID)
    logger.info("Target Directory: %s", MODELS_DIR)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import hf_hub_download

    for fname in FILES_TO_DOWNLOAD:
        target = MODELS_DIR / fname
        logger.info("Downloading '%s' from HF repo '%s'...", fname, HF_REPO_ID)
        try:
            downloaded = hf_hub_download(repo_id=HF_REPO_ID, filename=fname, local_dir=MODELS_DIR)
            logger.info("Successfully fetched '%s' -> %s", fname, downloaded)
        except Exception as exc:
            if target.exists() and target.stat().st_size > 0:
                logger.info("HF download note for '%s': %s (using local file)", fname, exc)
            else:
                logger.error("Failed to download '%s': %s", fname, exc)

    logger.info("=== Pre-loading ONNX Classifier Model ===")
    import classifier
    classifier.load(MODELS_DIR)
    logger.info("=== backend-classifier HF models successfully downloaded & verified ===")

if __name__ == "__main__":
    main()
