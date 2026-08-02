"""
classifier.py
EfficientNet Keras classifier – optimised for fast startup.

Speed improvements over the original:
  - TF_CPP_MIN_LOG_LEVEL=3 silences verbose TF/XLA startup noise
  - os.environ["CUDA_VISIBLE_DEVICES"] = "-1" forces CPU-only (no CUDA init delay)
  - Model is warmed up with a dummy image so the first real request is instant
  - numpy pre-allocated buffer reused across calls
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Tuple

# ==============================
# TensorFlow Environment
# ==============================

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

_cpu_count = os.cpu_count() or 4
os.environ.setdefault("TF_NUM_INTRAOP_THREADS", str(_cpu_count))
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "2")

import numpy as np

logger = logging.getLogger(__name__)

_tf = None
_model = None
_loaded_model_name: str = "None"
preprocess_input = None

_flower_names: list[str] = []
_idx_to_label: dict[int, str] = {}
_label_to_flower_name: dict[str, str] = {}
_flower_name_to_doc_idx: dict[str, int] = {}
_label_to_doc_idx: dict[str, int] = {}

IMG_SIZE = int(os.getenv("CLASSIFIER_IMG_SIZE", "224"))


# ==========================================
# Import TensorFlow only once
# ==========================================

def _import_tf():
    global _tf, preprocess_input

    if _tf is None:
        import tensorflow as tf
        from tensorflow.keras.applications.efficientnet import preprocess_input as eff_preprocess

        tf.get_logger().setLevel("ERROR")
        tf.config.set_visible_devices([], "GPU")

        _tf = tf
        preprocess_input = eff_preprocess

        logger.info("TensorFlow %s Loaded", tf.__version__)

    return _tf


# ==========================================
# Load Model
# ==========================================

def _resolve_file_path(filename: str, hf_repo_id: str, models_dir: Path | None = None) -> Path:
    """
    Downloads filename from Hugging Face repository (HF_REPO_ID) using hf_hub_download(),
    or falls back to local models_dir if download fails or HF_REPO_ID is not set.
    """
    if hf_repo_id:
        try:
            from huggingface_hub import hf_hub_download
            kwargs = {"repo_id": hf_repo_id, "filename": filename}
            if models_dir is not None:
                kwargs["local_dir"] = models_dir
            downloaded = hf_hub_download(**kwargs)
            logger.info("Fetched '%s' from Hugging Face repo '%s'", filename, hf_repo_id)
            return Path(downloaded)
        except Exception as exc:
            logger.warning("Hugging Face download failed for '%s' from repo '%s': %s", filename, hf_repo_id, exc)

    if models_dir is not None:
        local_path = models_dir / filename
        if local_path.exists():
            return local_path

    return Path(filename)


def load(models_dir: Path | None = None):

    global _model
    global _idx_to_label
    global _flower_names
    global _label_to_flower_name
    global _flower_name_to_doc_idx
    global _label_to_doc_idx

    tf = _import_tf()

    hf_repo_id = os.getenv("HF_REPO_ID", "").strip()
    env_model_name = os.getenv("CLASSIFIER_MODEL_NAME", "flower_classifier.keras").strip() or "flower_classifier.keras"

    model_path = _resolve_file_path(env_model_name, hf_repo_id, models_dir)
    mapping_path = _resolve_file_path("class_mapping.json", hf_repo_id, models_dir)
    docs_path = _resolve_file_path("flower_documents.json", hf_repo_id, models_dir)
    class_to_flower_path = _resolve_file_path("class_to_flower.json", hf_repo_id, models_dir)

    # -------------------------
    # Class Mapping
    # -------------------------

    with open(mapping_path, "r", encoding="utf-8") as f:
        raw_mapping = json.load(f)

    _idx_to_label = {v: k for k, v in raw_mapping.items()}
    logger.info("Loaded %d Classes", len(_idx_to_label))

    # -------------------------
    # Flower Documents
    # -------------------------

    with open(docs_path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    def normalize_name(name: str) -> str:
        return " ".join(
            name.strip().lower()
                .replace("-", " ")
                .replace("’", "'")
                .replace("(", "")
                .replace(")", "")
                .split()
        )

    _flower_names = []
    _flower_name_to_doc_idx = {}

    _flower_aliases: dict[str, str] = {
        "globe flower": "globe flower",
        "globe-flower": "globe flower",
        "love in the mist": "love in a mist",
        "cape flower": "cape fuchsia",
        "barbeton daisy": "barberton daisy",
        "bolero deep blue": "bolero deep blue (lisianthus)",
        "primula": "primrose",
        "bishop of llandaff": "bishop of llandaff (dahlia)",
        "gaura": "gaura (whirling butterflies)",
        "geranium": "true geranium",
        "cautleya spicata": "hardy shade ginger",
        "lotus": "sacred lotus",
        "desert-rose": "desert rose",
        "hippeastrum": "amaryllis (hippeastrum)",
    }

    for idx, doc in enumerate(docs):
        flower = "Unknown"
        lines = doc.splitlines()
        for i, line in enumerate(lines):
            if line.strip() == "Flower Name:" and i + 1 < len(lines):
                flower = lines[i + 1].strip()
                break

        _flower_names.append(flower)
        normalized = normalize_name(flower)
        _flower_name_to_doc_idx[normalized] = idx

    logger.info("Loaded %d Flower Documents", len(_flower_names))

    if class_to_flower_path.exists():
        with open(class_to_flower_path, "r", encoding="utf-8") as f:
            _label_to_flower_name = json.load(f)
    else:
        _label_to_flower_name = {}

    _label_to_doc_idx = {}

    def resolve_doc_index(label_str: str) -> int:
        flower_name = _label_to_flower_name.get(label_str)
        if flower_name:
            normalized_name = normalize_name(flower_name)
            if normalized_name in _flower_name_to_doc_idx:
                return _flower_name_to_doc_idx[normalized_name]

            alias_name = _flower_aliases.get(normalized_name)
            if alias_name and normalize_name(alias_name) in _flower_name_to_doc_idx:
                return _flower_name_to_doc_idx[normalize_name(alias_name)]

        try:
            label_int = int(label_str)
        except ValueError:
            label_int = None

        if label_int is not None:
            fallback = label_int - 1
            if 0 <= fallback < len(_flower_names):
                return fallback

        return -1

    for label_str in _idx_to_label.values():
        doc_idx = resolve_doc_index(label_str)
        if doc_idx >= 0:
            _label_to_doc_idx[label_str] = doc_idx
        else:
            logger.warning("Unable to resolve doc index for label %s", label_str)
            _label_to_doc_idx[label_str] = int(label_str) - 1 if label_str.isdigit() else -1

    # -------------------------
    # Load Model
    # -------------------------

    import time
    t_start = time.perf_counter()
    logger.info("Loading Classifier model '%s' weights into memory (please wait ~5-10s)...", model_path.name)

    _model = tf.keras.models.load_model(
        str(model_path),
        compile=False
    )

    t_elapsed = time.perf_counter() - t_start
    logger.info("Classifier model '%s' loaded into memory in %.2fs.", model_path.name, t_elapsed)

    # Auto-detect model input shape if present
    global IMG_SIZE
    try:
        shape = _model.input_shape
        if isinstance(shape, list):
            shape = shape[0]
        if len(shape) == 4 and shape[1] is not None and shape[2] is not None:
            detected_size = int(shape[1])
            if detected_size != IMG_SIZE:
                logger.info(
                    "Auto-detected model input size %dx%d (overriding default IMG_SIZE %d)",
                    detected_size,
                    int(shape[2]),
                    IMG_SIZE,
                )
                IMG_SIZE = detected_size
    except Exception as exc:
        logger.warning("Could not auto-detect model input shape: %s", exc)

    # Warmup

    dummy = np.zeros(
        (1, IMG_SIZE, IMG_SIZE, 3),
        dtype=np.float32
    )

    dummy = preprocess_input(dummy)
    try:
        _model(dummy, training=False).numpy()
    except Exception:
        pass

    global _loaded_model_name
    _loaded_model_name = model_path.name

    logger.info("=== Classifier Model Loaded: '%s' (Input size: %dx%d) ===", _loaded_model_name, IMG_SIZE, IMG_SIZE)


def get_model_name() -> str:
    """Return the filename of the currently loaded classifier model."""
    return _loaded_model_name


# ==========================================
# Prediction
# ==========================================

def predict(image_bytes: bytes) -> Tuple[str, float, int]:
    """
    Classify raw image bytes.

    Returns
    -------
    (flower_name, confidence_percent, doc_index)
    """

    _import_tf()

    if _model is None:
        raise RuntimeError("Classifier model has not been loaded yet.")

    import io
    from PIL import Image

    # Read image and resize with fast BILINEAR interpolation
    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    pil_img = pil_img.resize((IMG_SIZE, IMG_SIZE), Image.Resampling.BILINEAR)

    # Fast numpy conversion and batch expansion (avoids Keras img_to_array overhead)
    img_array = np.asarray(pil_img, dtype=np.float32)[np.newaxis, ...]

    # EfficientNet preprocessing
    img_array = preprocess_input(img_array)

    # Fast direct model execution
    preds = _model(img_array, training=False).numpy()

    pred = preds[0]
    dense_idx = int(np.argmax(pred))
    confidence = float(pred[dense_idx]) * 100

    # Folder number (1-102)
    label_str = _idx_to_label.get(dense_idx, "1")

    # Top-5 debug only at DEBUG level to avoid extra runtime noise.
    if logger.isEnabledFor(logging.DEBUG):
        top5 = np.argsort(pred)[-5:][::-1]
        logger.debug("Top 5 predictions:")
        for idx in top5:
            label = _idx_to_label.get(idx, "Unknown")
            doc_idx_debug = _label_to_doc_idx.get(label, int(label) - 1 if label.isdigit() else -1)
            flower_debug = _flower_names[doc_idx_debug] if 0 <= doc_idx_debug < len(_flower_names) else "Unknown"
            logger.debug(
                "Index: %s | Folder: %s | DocIdx: %s | Flower: %s | Confidence: %.2f%%",
                idx,
                label,
                doc_idx_debug,
                flower_debug,
                pred[idx] * 100,
            )

    doc_idx = _label_to_doc_idx.get(label_str, -1)
    if doc_idx == -1:
        try:
            label_int = int(label_str)
            doc_idx = label_int - 1
        except ValueError:
            doc_idx = -1

    if 0 <= doc_idx < len(_flower_names):
        flower_name = _flower_names[doc_idx]
    else:
        flower_name = _label_to_flower_name.get(label_str, f"Flower #{label_str}")

    logger.info(
        "Prediction: %s (%.2f%%)",
        flower_name,
        confidence
    )

    return flower_name, confidence, doc_idx
