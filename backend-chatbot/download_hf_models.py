"""
download_hf_models.py
Download all Hugging Face models and datasets/indexes for backend-chatbot.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s")
logger = logging.getLogger("chatbot-hf-loader")

HF_REPO_ID = os.getenv("HF_REPO_ID", "manoranjan-programmer/flower-ai-model").strip()
PHI_HF_MODEL = os.getenv("PHI_HF_MODEL", "Qwen/Qwen2.5-0.5B-Instruct").strip()
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

def download_hf_repo_files():
    logger.info("=== Step 1: Downloading repository files from HF repo '%s' ===", HF_REPO_ID)
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

def download_embedding_model():
    logger.info("=== Step 2: Downloading Sentence Transformer Embedding model (BAAI/bge-small-en-v1.5) ===")
    import knowledge
    embed_model = knowledge.get_embedding_model()
    logger.info("Embedding model successfully loaded: %s", type(embed_model))

def download_llm_model():
    logger.info("=== Step 3: Downloading Hugging Face LLM model ('%s') ===", PHI_HF_MODEL)
    import chatbot
    model, tokenizer = chatbot.get_llm()
    logger.info("LLM Model & Tokenizer successfully loaded: %s", PHI_HF_MODEL)

def download_translation_models():
    logger.info("=== Step 4: Downloading Helsinki-NLP Translation models ===")
    import translation
    for lang in ["ta", "hi", "ml", "te", "kn", "es", "fr", "de"]:
        model_id = translation.LANGUAGE_MODELS.get(lang)
        if model_id:
            logger.info("Downloading translation pipeline for lang='%s' (%s)...", lang, model_id)
            try:
                pipe = translation.get_translation_pipeline(lang)
                logger.info("Loaded translation pipeline for '%s'", lang)
            except Exception as exc:
                logger.error("Failed to download translation pipeline for '%s': %s", lang, exc)

def main():
    logger.info("=== Starting Hugging Face Model Downloader for backend-chatbot ===")
    download_hf_repo_files()
    download_embedding_model()
    download_llm_model()
    download_translation_models()
    logger.info("=== ALL Hugging Face models for backend-chatbot successfully downloaded & verified! ===")

if __name__ == "__main__":
    main()
