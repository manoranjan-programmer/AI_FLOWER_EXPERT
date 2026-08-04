"""
classifier.py
EfficientNet ONNX classifier – lightweight standalone inference engine.

Features:
  - Powered by ONNX Runtime (`onnxruntime`)
  - Automatic download & caching from Hugging Face repository
  - Input shape & channel order auto-detection (NHWC vs NCHW)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Tuple

import numpy as np
import onnxruntime as ort

logger = logging.getLogger(__name__)

_session: ort.InferenceSession | None = None
_input_name: str | None = None
_output_name: str | None = None
_is_channels_first: bool = False
_loaded_model_name: str = "None"

_flower_names: list[str] = []
_idx_to_label: dict[int, str] = {}
_label_to_flower_name: dict[str, str] = {}
_flower_name_to_doc_idx: dict[str, int] = {}
_label_to_doc_idx: dict[str, int] = {}

IMG_SIZE = int(os.getenv("CLASSIFIER_IMG_SIZE", "384"))


def preprocess_input(x: np.ndarray) -> np.ndarray:
    """EfficientNet preprocess_input pass-through."""
    return x


def _resolve_file_path(filename: str, hf_repo_id: str, models_dir: Path | None = None) -> Path:
    """Check local file existence first. Download from Hugging Face repository only if missing."""
    if models_dir is not None:
        local_path = models_dir / filename
        if local_path.exists():
            return local_path

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

    return Path(filename)


def load(models_dir: Path | None = None):
    global _session, _input_name, _output_name, _is_channels_first
    global _idx_to_label, _flower_names, _label_to_flower_name
    global _flower_name_to_doc_idx, _label_to_doc_idx
    global IMG_SIZE, _loaded_model_name

    hf_repo_id = os.getenv("HF_REPO_ID", "").strip()
    env_model_name = (
        os.getenv("CLASSIFIER_MODEL_NAME", "flower_classifier.onnx").strip()
        or "flower_classifier.onnx"
    )

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
    docs = []
    if docs_path.exists():
        try:
            with open(docs_path, "r", encoding="utf-8") as f:
                docs = json.load(f)
        except Exception as exc:
            logger.warning("Could not read %s: %s", docs_path, exc)

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

    if docs:
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
        logger.info("Loaded %d Flower Documents from JSON", len(_flower_names))
    else:
        logger.info("flower_documents.json not found; classifier fallback active.")

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
    # Load ONNX Model
    # -------------------------
    import time
    t_start = time.perf_counter()
    logger.info("Loading ONNX Classifier model '%s'...", model_path.name)

    opts = ort.SessionOptions()
    opts.intra_op_num_threads = max(1, min(4, (os.cpu_count() or 4) - 1 if (os.cpu_count() or 4) > 2 else 2))
    opts.inter_op_num_threads = 1
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    opts.log_severity_level = 3

    _session = ort.InferenceSession(
        str(model_path),
        sess_options=opts,
        providers=["CPUExecutionProvider"]
    )

    _input_meta = _session.get_inputs()[0]
    _input_name = _input_meta.name
    _output_name = _session.get_outputs()[0].name

    t_elapsed = time.perf_counter() - t_start
    logger.info("ONNX Classifier model '%s' loaded in %.2fs.", model_path.name, t_elapsed)

    shape = _input_meta.shape
    try:
        if len(shape) == 4:
            if shape[1] == 3:
                _is_channels_first = True
                if isinstance(shape[2], int) and shape[2] > 0:
                    IMG_SIZE = shape[2]
            elif shape[3] == 3 or shape[-1] == 3:
                _is_channels_first = False
                if isinstance(shape[1], int) and shape[1] > 0:
                    IMG_SIZE = shape[1]
            elif isinstance(shape[1], int) and isinstance(shape[2], int):
                IMG_SIZE = shape[1]
    except Exception as exc:
        logger.warning("Could not auto-detect ONNX model input shape: %s", exc)

    dummy = np.zeros((1, IMG_SIZE, IMG_SIZE, 3), dtype=np.float32)
    dummy = preprocess_input(dummy)
    if _is_channels_first:
        dummy_in = np.transpose(dummy, (0, 3, 1, 2))
    else:
        dummy_in = dummy
    try:
        _session.run([_output_name], {_input_name: dummy_in})
    except Exception:
        pass

    _loaded_model_name = model_path.name
    logger.info("=== ONNX Classifier Model Loaded: '%s' (Input size: %dx%d) ===", _loaded_model_name, IMG_SIZE, IMG_SIZE)


import threading

_classifier_lock = threading.Lock()
_models_dir: Path | None = Path(__file__).parent / "models"


def get_classifier():
    """Lazy-load ONNX classifier model thread-safely."""
    global _session
    if _session is None:
        with _classifier_lock:
            if _session is None:
                load(_models_dir)
    return _session


def predict(image_bytes: bytes) -> Tuple[str, float, int]:
    """
    Classify raw image bytes.
    Returns: (flower_name, confidence_percent, class_id)
    """
    get_classifier()

    import io
    from PIL import Image

    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    pil_img = pil_img.resize((IMG_SIZE, IMG_SIZE), Image.Resampling.BILINEAR)

    img_array = np.asarray(pil_img, dtype=np.float32)[np.newaxis, ...]
    img_array = preprocess_input(img_array)

    if _is_channels_first:
        img_input = np.transpose(img_array, (0, 3, 1, 2))
    else:
        img_input = img_array

    raw_outputs = _session.run([_output_name], {_input_name: img_input})
    preds = raw_outputs[0]

    pred = preds[0]
    dense_idx = int(np.argmax(pred))
    confidence = float(pred[dense_idx]) * 100

    label_str = _idx_to_label.get(dense_idx, "1")

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

    logger.info("Prediction: %s (%.2f%%, class_id=%d)", flower_name, confidence, doc_idx)

    return flower_name, confidence, doc_idx
