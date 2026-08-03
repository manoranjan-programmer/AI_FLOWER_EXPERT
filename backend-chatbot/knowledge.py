"""
knowledge.py
MongoDB & FAISS-based semantic retrieval service.

Exposes:
  - search(query, k) -> list[str]          top-k relevant document chunks
  - get_document(idx) -> str               raw document by index
  - get_flower_info(flower_name) -> dict  retrieves flower document from MongoDB using pymongo
  - build_flower_context(flower_info) -> str formatted context snippet from MongoDB attributes
  - get_flower_summary(doc_idx) -> dict    short structured summary for prediction cards
"""

from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import pymongo
except ImportError:
    pymongo = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (.env is already loaded by app.py)
# ---------------------------------------------------------------------------
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB: str = os.getenv("MONGO_DB", "test")
MONGO_COLLECTION: str = os.getenv("MONGO_COLLECTION", "Flower_Knowledge_Base")

# ---------------------------------------------------------------------------
# Module state – populated by load()
# ---------------------------------------------------------------------------
_faiss_index = None
_documents: list[str] = []
_flower_docs_by_norm_name: dict[str, str] = {}
_embeddings: Optional[np.ndarray] = None
_embed_model = None          # SentenceTransformer instance
_flower_lookup: dict[str, dict] = {}
_flower_lookup_by_norm_name: dict[str, dict] = {}
_norm_flower_map: dict[str, str] = {}
_mongo_client: Optional[pymongo.MongoClient] = None
_mongo_coll = None
_mongo_history_coll = None


def normalize_flower_name(name: str) -> str:
    """Strictly normalize flower names: lowercase, trim, strip spaces, hyphens, and underscores."""
    if not name:
        return ""
    return name.strip().lower().replace("-", "").replace(" ", "").replace("_", "")


def load(models_dir: Path) -> None:
    """Load all knowledge-base artefacts and initialize MongoDB pymongo connection."""
    global _faiss_index, _documents, _flower_docs_by_norm_name, _embeddings, _embed_model, _flower_lookup, _flower_lookup_by_norm_name, _norm_flower_map, _mongo_client, _mongo_coll, _mongo_history_coll

    import faiss
    from sentence_transformers import SentenceTransformer
    from dotenv import load_dotenv

    # Load environment variables
    env_path = models_dir.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    logger.info("=== Loading Knowledge Base from %s ===", models_dir)

    # ---- MongoDB Connection (optional/fallback) ---------------------------
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGO_DB", "test")
    mongo_coll_name = os.getenv("MONGO_COLLECTION", "Flower_Knowledge_Base")
    mongo_history_coll_name = os.getenv("MONGO_HISTORY_COLLECTION", "Flower_Search_History")

    if pymongo is not None:
        try:
            logger.info("Connecting to MongoDB Atlas (db: '%s') …", mongo_db_name)
            _mongo_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            db = _mongo_client[mongo_db_name]
            _mongo_coll = db[mongo_coll_name]
            _mongo_history_coll = db[mongo_history_coll_name]

            doc_count = _mongo_coll.count_documents({})
            logger.info("Connected to MongoDB collection '%s' (%d docs). Search History Collection: '%s'.", mongo_coll_name, doc_count, mongo_history_coll_name)

            if doc_count == 0:
                available_colls = db.list_collection_names()
                logger.info("Target collection '%s' has 0 docs. Checking available collections in '%s': %s", mongo_coll_name, mongo_db_name, available_colls)
                for coll in available_colls:
                    c = db[coll]
                    c_cnt = c.count_documents({})
                    if c_cnt > 0:
                        _mongo_coll = c
                        mongo_coll_name = coll
                        doc_count = c_cnt
                        logger.info("Auto-connected to collection '%s' with %d documents.", coll, doc_count)
                        break
        except Exception as exc:
            logger.warning("MongoDB connection warning (will use local fallbacks): %s", exc)
            _mongo_coll = None
            _mongo_history_coll = None
    else:
        logger.info("pymongo not installed – using local JSON files only.")

    # ---- FAISS Index -------------------------------------------------------
    index_path = models_dir / "flower_faiss.index"
    if index_path.exists():
        logger.info("Loading FAISS index from %s …", index_path)
        _faiss_index = faiss.read_index(str(index_path))
        logger.info("FAISS index loaded. Total vectors: %d", _faiss_index.ntotal)

    # ---- Documents ---------------------------------------------------------
    docs_path = models_dir / "flower_documents.json"
    _flower_docs_by_norm_name = {}
    if docs_path.exists():
        with open(docs_path, "r", encoding="utf-8") as f:
            _documents = json.load(f)
        for doc in _documents:
            m = re.search(r"Flower\s*Name:\s*([^\n]+)", doc, re.IGNORECASE)
            if m:
                raw_name = m.group(1).strip()
                _flower_docs_by_norm_name[normalize_flower_name(raw_name)] = doc
        logger.info("Loaded %d flower documents (indexed by normalized flower name: %d).", len(_documents), len(_flower_docs_by_norm_name))

    # ---- Embeddings (optional) ---------------------------------------------
    emb_path = models_dir / "flower_embeddings.npy"
    if emb_path.exists():
        _embeddings = np.load(str(emb_path))
        logger.info("Embeddings loaded: shape %s", _embeddings.shape)

    # ---- Flower lookup (fallback cache) ------------------------------------
    lookup_path = models_dir / "flower_lookup.json"
    _flower_lookup_by_norm_name = {}
    if lookup_path.exists():
        with open(lookup_path, "r", encoding="utf-8") as f:
            _flower_lookup = json.load(f)
        for name, data in _flower_lookup.items():
            _flower_lookup_by_norm_name[normalize_flower_name(name)] = data
            _norm_flower_map[name.lower()] = name
        logger.info("Loaded %d fallback flower lookup entries.", len(_flower_lookup))

    # ---- Sentence transformer ----------------------------------------------
    model_name = "BAAI/bge-small-en-v1.5"
    logger.info("Loading SentenceTransformer (%s) …", model_name)
    _embed_model = SentenceTransformer(model_name)
    logger.info("SentenceTransformer ready.")


# ---------------------------------------------------------------------------
# Public API – MongoDB Retrieval
# ---------------------------------------------------------------------------

@lru_cache(maxsize=256)
def _get_flower_info_cached(key: str) -> str:
    """Internal LRU cached finder for raw JSON doc string from local lookup/MongoDB."""
    if not key:
        return "{}"

    lower_key = key.strip().lower()

    # 1. Exact local lookup match (100% deterministic)
    if lower_key in _flower_lookup:
        return json.dumps(_flower_lookup[lower_key])

    normalized = _norm_flower_map.get(lower_key)
    if normalized and normalized in _flower_lookup:
        return json.dumps(_flower_lookup[normalized])

    # 2. MongoDB exact query
    if _mongo_coll is not None:
        try:
            query = {
                "$or": [
                    {"Flower": re.compile(f"^{re.escape(key)}$", re.IGNORECASE)},
                    {"flower": re.compile(f"^{re.escape(key)}$", re.IGNORECASE)},
                    {"flower_name": re.compile(f"^{re.escape(key)}$", re.IGNORECASE)},
                ]
            }
            doc = _mongo_coll.find_one(query)
            if doc:
                doc.pop("_id", None)
                normalized_doc = {}
                for k, v in doc.items():
                    clean_key = k.strip().lower().replace(" ", "_")
                    normalized_doc[clean_key] = v
                    normalized_doc[k] = v
                return json.dumps(normalized_doc)
        except Exception as exc:
            logger.warning("MongoDB query failed for '%s': %s", key, exc)

    # 3. Substring candidate match fallback
    for candidate, normalized_name in _norm_flower_map.items():
        if (candidate in lower_key or lower_key in candidate) and normalized_name in _flower_lookup:
            return json.dumps(_flower_lookup[normalized_name])

    return "{}"


def get_flower_info(flower_name: str) -> dict:
    """
    Retrieve flower document directly from MongoDB collection using pymongo.
    Searches by predicted flower name (case-insensitive) with LRU caching.
    """
    if not flower_name:
        return {}

    key = flower_name.strip()
    raw_json = _get_flower_info_cached(key)
    if raw_json and raw_json != "{}":
        try:
            return json.loads(raw_json)
        except Exception:
            pass
    return {}


def parse_flower_doc(doc_text: str) -> dict:
    """Parse key-value sections from a document in flower_documents.json."""
    if not doc_text:
        return {}

    headers = [
        "Flower Name:",
        "Scientific Name:",
        "Family:",
        "Native Region:",
        "Description:",
        "Flower Color:",
        "Blooming Season:",
        "Sunlight:",
        "Water:",
        "Fragrance:",
        "Toxicity:",
        "Pollinators:",
        "Medicinal Uses:",
        "Uses:",
    ]

    pattern = r"(" + "|".join([re.escape(h) for h in headers]) + r")"
    parts = re.split(pattern, doc_text)

    result = {}
    current_key = None
    for part in parts:
        part_str = part.strip()
        if not part_str:
            continue
        if part_str in headers:
            current_key = part_str.rstrip(":")
        elif current_key:
            result[current_key] = part_str
            current_key = None

    return result


def build_flower_context(flower_info: dict) -> str:
    """Build a comprehensive text snippet from flower document for prompt context."""
    if not flower_info:
        return ""

    field_mappings = [
        ("Flower", ["flower", "Flower", "Flower Name", "flower_name"]),
        ("Scientific Name", ["scientific_name", "Scientific Name", "scientific_name_"]),
        ("Family", ["family", "Family"]),
        ("Native Region", ["native_region", "Native Region"]),
        ("Color", ["color", "Color", "flower_color", "Flower Color"]),
        ("Season", ["season", "Season", "blooming_season", "Blooming Season"]),
        ("Sunlight", ["sunlight", "Sunlight"]),
        ("Water", ["water", "Water"]),
        ("Toxicity", ["toxicity", "Toxicity Level", "toxicity_level", "Toxicity"]),
        ("Pollinators", ["pollinators", "Pollinators"]),
        ("Fragrance", ["fragrance", "Fragrance"]),
        ("Description", ["description", "Description"]),
        ("Medicinal Uses", ["medicinal", "Medicinal Uses", "medicinal_uses"]),
        ("Uses", ["uses", "Uses", "common_uses"]),
        ("Cultural Significance", ["cultural", "Cultural Significance", "cultural_significance"]),
        ("Care Tips", ["care", "Care Tips", "care_tips"]),
    ]

    lines: list[str] = []
    for label, keys in field_mappings:
        val = None
        for k in keys:
            if k in flower_info and flower_info[k]:
                val = flower_info[k]
                break
        if not val:
            continue
        val_str = str(val).strip()
        if val_str:
            lines.append(f"{label}: {val_str}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Vector Search & Document Helpers
# ---------------------------------------------------------------------------

def _search_cached(query: str, k: int) -> tuple[str, ...]:
    if _faiss_index is None or _embed_model is None:
        raise RuntimeError("Knowledge base has not been loaded yet.")

    if not query:
        return ()

    query_vec = _embed_model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True
    ).astype("float32")

    fetch_k = min(len(_documents), max(k * 4, 25))
    distances, indices = _faiss_index.search(query_vec, fetch_k)

    results: list[str] = []
    seen_flowers: set[str] = set()

    for idx in indices[0]:
        if 0 <= idx < len(_documents):
            doc = _documents[idx]
            parsed = parse_flower_doc(doc)
            flower_id = (parsed.get("Flower Name") or parsed.get("Scientific Name") or "").strip().lower()
            if not flower_id:
                # Fallback extraction if parse_flower_doc doesn't match standard header
                m = re.search(r"Flower\s*Name:\s*([^\n]+)", doc, re.IGNORECASE)
                flower_id = m.group(1).strip().lower() if m else doc[:40].strip().lower()

            if flower_id not in seen_flowers:
                seen_flowers.add(flower_id)
                results.append(doc)
                if len(results) >= k:
                    break

    return tuple(results)


@lru_cache(maxsize=128)
def search(query: str, k: int = 1) -> list[str]:
    """Embed query and return top-k relevant document chunks with unique flower species."""
    normalized = query.strip().lower()
    if not normalized:
        return []
    return list(_search_cached(normalized, k))


def get_document(doc_idx: int) -> str:
    """Return full document by index."""
    if 0 <= doc_idx < len(_documents):
        return _documents[doc_idx]
    return ""


def get_flower_doc(flower_name: str) -> Optional[str]:
    """Return exact flower document by flower_name in O(1) time using normalized string matching."""
    if not flower_name:
        return None
    norm_key = normalize_flower_name(flower_name)
    return _flower_docs_by_norm_name.get(norm_key)


def get_flower_doc_by_name(flower_name: str) -> str:
    """Return exact flower document by flower_name directly from indexed flower_documents.json."""
    return get_flower_doc(flower_name) or ""


def get_flower_summary(doc_idx: int, flower_name: str = "") -> dict:
    """
    Parse structured fields from a flower document and MongoDB lookup.
    Returns a dictionary suitable for prediction cards containing both Title Case
    keys (for frontend knowledge cards) and snake_case keys (for APIs).
    """
    doc = get_document(doc_idx) if doc_idx >= 0 else ""
    if not doc and flower_name:
        doc = get_flower_doc(flower_name) or ""
    doc_parsed = parse_flower_doc(doc) if doc else {}

    target_name = flower_name or doc_parsed.get("Flower Name", "")
    info = get_flower_info(target_name) if target_name else {}

    def _get_val(*keys):
        for k in keys:
            if k in info and info[k] and str(info[k]).strip():
                return str(info[k]).strip()
            if k in doc_parsed and doc_parsed[k] and str(doc_parsed[k]).strip():
                return str(doc_parsed[k]).strip()
        return ""

    fl_name = _get_val("flower", "Flower Name", "flower_name") or flower_name or "Flower"
    sci_name = _get_val("scientific_name", "Scientific Name") or f"{fl_name} spp."
    desc = _get_val("description", "Description") or f"{fl_name} is a botanical species."
    uses = _get_val("uses", "Uses", "common_uses") or "Used for ornamental landscaping, gardening, and floral displays."
    med_uses = _get_val("medicinal", "Medicinal Uses", "medicinal_uses") or "Used traditionally in herbal remedies, teas, and soothing extracts."
    sunlight = _get_val("sunlight", "Sunlight") or "Full Sun to Partial Shade"
    water = _get_val("water", "Water") or "Moderate"
    care_tips = _get_val("care_tips", "Care Tips", "care") or f"Sunlight: {sunlight}. Water: {water}. Provide well-draining soil."
    cultural = _get_val("cultural_significance", "Cultural Significance", "cultural") or "Holds symbolic meaning of beauty, resilience, and natural harmony."
    native = _get_val("native_region", "Native Region") or "Native to temperate and subtropical regions worldwide."
    season = _get_val("season", "Blooming Season", "blooming_season") or "Spring through Summer."
    toxicity = _get_val("toxicity", "Toxicity", "Toxicity Level") or "Non-toxic to humans; keep domestic pets from ingesting plant stems."
    fragrance = _get_val("fragrance", "Fragrance") or "Mild"
    pollinators = _get_val("pollinators", "Pollinators") or "Bees, Butterflies"
    facts = _get_val("interesting_facts", "Interesting Facts", "facts") or f"Fragrance: {fragrance}. Attracts essential pollinators such as {pollinators}."

    return {
        # 11 Knowledge Card Exact Title Case Keys for Frontend UI
        "Flower Name": fl_name,
        "Scientific Name": sci_name,
        "Description": desc,
        "Uses": uses,
        "Medicinal Uses": med_uses,
        "Care Tips": care_tips,
        "Cultural Significance": cultural,
        "Native Region": native,
        "Blooming Season": season,
        "Toxicity Warning": toxicity,
        "Toxicity": toxicity,
        "Interesting Facts": facts,

        # Standard & legacy snake_case key aliases
        "flower": fl_name,
        "scientific_name": sci_name,
        "description": desc,
        "uses": uses,
        "common_uses": uses,
        "medicinal_uses": med_uses,
        "medicinal": med_uses,
        "care_tips": care_tips,
        "sunlight": sunlight,
        "water": water,
        "cultural_significance": cultural,
        "native_region": native,
        "blooming_season": season,
        "season": season,
        "toxicity": toxicity,
        "fragrance": fragrance,
        "pollinators": pollinators,
        "interesting_facts": facts,
    }


# ---------------------------------------------------------------------------
# MongoDB Search History Logger
# ---------------------------------------------------------------------------

def _ensure_mongo_connected() -> bool:
    global _mongo_client, _mongo_coll, _mongo_history_coll
    if _mongo_history_coll is not None:
        return True
    if pymongo is None:
        return False
    try:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        mongo_db_name = os.getenv("MONGO_DB", "test")
        mongo_history_coll_name = os.getenv("MONGO_HISTORY_COLLECTION", "Flower_Search_History")
        _mongo_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = _mongo_client[mongo_db_name]
        _mongo_history_coll = db[mongo_history_coll_name]
        return True
    except Exception as exc:
        logger.warning("MongoDB auto-reconnect warning: %s", exc)
        return False


def save_search_history(
    flower_name: str,
    confidence: float,
    summary: str = "",
    card: dict = None,
    filename: str = None,
    session_id: str = None,
    messages: list = None,
    image_preview: str = None,
    user_id: str = None,
    user_email: str = None,
) -> bool:
    """
    Saves user flower search, predictions, total AI responses, and image upload previews
    directly into MongoDB Atlas collection (specified by MONGO_HISTORY_COLLECTION, default: 'Flower_Search_History').
    Stores all records persistently per user.
    """
    if not _ensure_mongo_connected() or _mongo_history_coll is None:
        logger.warning("MongoDB search history collection is not available.")
        return False
    try:
        from datetime import datetime
        now = datetime.now()
        flower_title = flower_name or "AI Botanical Chat"
        sid = session_id or f"session_{flower_title.lower().replace(' ', '_')}"

        update_fields = {
            "session_id": sid,
            "flower": flower_title,
            "confidence": float(confidence if confidence is not None else 99.0),
            "summary": summary or "",
            "card": card or {},
            "scientific_name": (card.get("Scientific Name") or card.get("scientific_name") if card else ""),
            "filename": filename or "",
            "messages": messages or [],
            "timestamp": now.isoformat(),
            "searched_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if user_id:
            update_fields["user_id"] = user_id
        if user_email:
            update_fields["user_email"] = user_email

        # Only overwrite image_preview if a non-empty preview is supplied
        if image_preview:
            update_fields["image_preview"] = image_preview

        _mongo_history_coll.update_one(
            {"session_id": sid},
            {"$set": update_fields},
            upsert=True
        )
        logger.info("Successfully stored search history session '%s' for user '%s' in MongoDB.", sid, user_email or user_id or 'anonymous')
        return True
    except Exception as exc:
        logger.warning("Failed to save search history to MongoDB Atlas: %s", exc)
        return False


def get_search_history(limit: int = 100, user_id: str = None, user_email: str = None) -> list[dict]:
    """Retrieve per-user flower search and prediction records from MongoDB Atlas collection."""
    if not _ensure_mongo_connected() or _mongo_history_coll is None:
        return []
    try:
        query = {}
        if user_id or user_email:
            or_clauses = []
            if user_id:
                or_clauses.append({"user_id": user_id})
            if user_email:
                or_clauses.append({"user_email": user_email})
            query = {"$or": or_clauses}

        if limit and limit > 0:
            cursor = _mongo_history_coll.find(query).sort("_id", -1).limit(limit)
        else:
            cursor = _mongo_history_coll.find(query).sort("_id", -1)

        results = []
        for doc in cursor:
            doc.pop("_id", None)
            results.append(doc)
        return results
    except Exception as exc:
        logger.warning("Failed to fetch search history from MongoDB Atlas: %s", exc)
        return []


