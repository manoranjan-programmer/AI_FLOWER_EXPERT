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

import threading

# ---------------------------------------------------------------------------
# Module state – lazy loaded on demand
# ---------------------------------------------------------------------------
_models_dir: Path = Path(__file__).parent / "models"
_faiss_index = None
_documents: list[str] = []
_flower_docs_by_norm_name: dict[str, str] = {}
_embeddings: Optional[np.ndarray] = None
_embed_model = None          # SentenceTransformer instance
_flower_lookup: dict[str, dict] = {}
_norm_flower_map: dict[str, str] = {}
_mongo_client: Optional[pymongo.MongoClient] = None
_mongo_coll = None
_mongo_history_coll = None

_faiss_lock = threading.Lock()
_embedding_lock = threading.Lock()
_docs_lock = threading.Lock()
_lookup_lock = threading.Lock()
_kb_lock = threading.Lock()          # orchestrated knowledge-base lock
_kb_ready = False                    # True once all three resources confirmed loaded


def normalize_flower_name(name: str) -> str:
    """Strictly normalize flower names: lowercase, trim, strip spaces, hyphens, and underscores."""
    if not name:
        return ""
    return name.strip().lower().replace("-", "").replace(" ", "").replace("_", "")


# ---------------------------------------------------------------------------
# Individual lazy getters (load once, cache forever, log once)
# ---------------------------------------------------------------------------

def get_flower_documents() -> list[str]:
    """Lazy-load flower documents thread-safely from local file or MongoDB Atlas."""
    global _documents, _flower_docs_by_norm_name
    if _documents:
        return _documents
    with _docs_lock:
        if _documents:
            return _documents

        docs_path = _models_dir / "flower_documents.json"
        if docs_path.exists():
            logger.info("Loading Flower Documents from local JSON file...")
            try:
                with open(docs_path, "r", encoding="utf-8") as f:
                    _documents = json.load(f)
                for doc in _documents:
                    m = re.search(r"(?:Flower\s*Name|Flower|flower_name)\s*:\s*([^\n]+)", doc, re.IGNORECASE)
                    if m:
                        raw_name = m.group(1).strip()
                        _flower_docs_by_norm_name[normalize_flower_name(raw_name)] = doc
                logger.info("Flower Documents Loaded from file (%d documents)", len(_documents))
                return _documents
            except Exception as exc:
                logger.warning("Error reading flower_documents.json: %s", exc)

        logger.info("flower_documents.json not found at %s. Attempting to load from MongoDB Atlas...", docs_path)
        _ensure_mongo_connected()
        if _mongo_coll is not None:
            try:
                mongo_docs = list(_mongo_coll.find({}))
                if mongo_docs:
                    loaded_docs = []
                    for mdoc in mongo_docs:
                        mdoc.pop("_id", None)
                        fl_name = (
                            mdoc.get("flower") or mdoc.get("Flower") or
                            mdoc.get("flower_name") or mdoc.get("Flower Name") or
                            mdoc.get("name") or mdoc.get("Name") or ""
                        )
                        doc_str = build_flower_context(mdoc)
                        if not doc_str and fl_name:
                            doc_str = f"Flower Name: {fl_name}\nDescription: Botanical flower species {fl_name}."
                        if doc_str:
                            loaded_docs.append(doc_str)
                            if fl_name:
                                _flower_docs_by_norm_name[normalize_flower_name(fl_name)] = doc_str
                    if loaded_docs:
                        _documents = loaded_docs
                        logger.info("Successfully loaded %d flower documents from MongoDB collection '%s'.", len(_documents), os.getenv("MONGO_COLLECTION", "Flower_Knowledge_Base"))
                        return _documents
            except Exception as exc:
                logger.warning("Failed to fetch documents from MongoDB Atlas: %s", exc)

        lookup = get_flower_lookup()
        if lookup:
            logger.info("Building flower documents from local flower_lookup.json...")
            loaded_docs = []
            for name, data in lookup.items():
                doc_str = build_flower_context(data)
                if doc_str:
                    loaded_docs.append(doc_str)
                    _flower_docs_by_norm_name[normalize_flower_name(name)] = doc_str
            if loaded_docs:
                _documents = loaded_docs
                logger.info("Loaded %d flower documents from flower_lookup.json.", len(_documents))

    return _documents


def get_embedding_model():
    """Lazy-load SentenceTransformer embedding model thread-safely. Logs once."""
    global _embed_model
    if _embed_model is not None:
        return _embed_model
    with _embedding_lock:
        if _embed_model is not None:
            return _embed_model
        logger.info("Loading Embeddings...")
        from sentence_transformers import SentenceTransformer
        model_name = "BAAI/bge-small-en-v1.5"
        _embed_model = SentenceTransformer(model_name)
        logger.info("Embeddings Loaded")
    return _embed_model


def get_faiss_index():
    """Lazy-load FAISS index thread-safely from file, or dynamically build in-memory index from documents."""
    global _faiss_index
    if _faiss_index is not None:
        return _faiss_index
    with _faiss_lock:
        if _faiss_index is not None:
            return _faiss_index
        index_path = _models_dir / "flower_faiss.index"
        if index_path.exists():
            logger.info("Loading FAISS index from local file...")
            try:
                import faiss
                _faiss_index = faiss.read_index(str(index_path))
                logger.info("FAISS Loaded from file")
                return _faiss_index
            except Exception as exc:
                logger.warning("Failed to load local flower_faiss.index: %s", exc)

        logger.info("flower_faiss.index not found on disk. Building in-memory FAISS vector index...")
        docs = get_flower_documents()
        embed_model = get_embedding_model()
        if docs and embed_model is not None:
            try:
                import faiss
                embeddings = embed_model.encode(docs, normalize_embeddings=True, convert_to_numpy=True).astype("float32")
                dim = embeddings.shape[1]
                idx = faiss.IndexFlatIP(dim)
                idx.add(embeddings)
                _faiss_index = idx
                logger.info("In-memory FAISS vector index successfully created (%d vectors, dim=%d).", len(docs), dim)
                return _faiss_index
            except Exception as exc:
                logger.warning("Failed to build in-memory FAISS index: %s", exc)

    return _faiss_index


def get_flower_lookup() -> dict[str, dict]:
    """Lazy-load flower_lookup.json thread-safely."""
    global _flower_lookup, _norm_flower_map
    if _flower_lookup:
        return _flower_lookup
    with _lookup_lock:
        if _flower_lookup:
            return _flower_lookup
        lookup_path = _models_dir / "flower_lookup.json"
        if lookup_path.exists():
            with open(lookup_path, "r", encoding="utf-8") as f:
                _flower_lookup = json.load(f)
            _norm_flower_map = {
                name.lower(): name
                for name in _flower_lookup.keys()
            }
    return _flower_lookup


# ---------------------------------------------------------------------------
# Orchestrated dependency-aware knowledge base initialiser
# ---------------------------------------------------------------------------

def get_knowledge_base() -> tuple:
    """
    Dependency-aware lazy initialiser for the full knowledge stack.

    Load order (strict dependency chain):
      1. Flower Documents  – needed for context
      2. Embedding Model   – needed for FAISS queries
      3. FAISS Index       – needs embeddings to be ready first

    Returns (documents, embed_model, faiss_index).
    Raises RuntimeError with a clear message if any component failed to load.
    Logs each resource exactly ONCE. Subsequent calls return cached objects immediately.
    """
    global _kb_ready
    if _kb_ready:
        return _documents, _embed_model, _faiss_index

    with _kb_lock:
        if _kb_ready:
            return _documents, _embed_model, _faiss_index

        docs = get_flower_documents()
        embed = get_embedding_model()
        faiss_idx = get_faiss_index()

        missing = []
        if not docs:
            missing.append("Flower Documents")
        if embed is None:
            missing.append("Embedding Model")
        if faiss_idx is None:
            missing.append("FAISS Index")

        if missing:
            raise RuntimeError(
                f"Knowledge base failed to load: {', '.join(missing)}. "
                "Ensure flower_documents.json, flower_faiss.index, and "
                "BAAI/bge-small-en-v1.5 are available."
            )

        _kb_ready = True
        logger.info("Knowledge Base Ready")

    return _documents, _embed_model, _faiss_index


def load(models_dir: Path) -> None:
    """Initialize models directory and MongoDB connection. Heavy models load lazily on demand."""
    global _models_dir, _mongo_client, _mongo_coll, _mongo_history_coll
    _models_dir = models_dir

    from dotenv import load_dotenv

    load_dotenv(models_dir.parent / ".env", override=True)

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
        except Exception as exc:
            logger.warning("MongoDB connection warning: %s", exc)
            _mongo_coll = None
            _mongo_history_coll = None


# ---------------------------------------------------------------------------
# Public API – MongoDB Retrieval
# ---------------------------------------------------------------------------

@lru_cache(maxsize=256)
def _get_flower_info_cached(key: str) -> str:
    """Internal LRU cached finder for raw JSON doc string from MongoDB/local lookup."""
    if _mongo_coll is not None:
        try:
            query = {
                "$or": [
                    {"Flower": re.compile(f"^{re.escape(key)}$", re.IGNORECASE)},
                    {"flower": re.compile(f"^{re.escape(key)}$", re.IGNORECASE)},
                    {"Flower": re.compile(re.escape(key), re.IGNORECASE)},
                    {"flower": re.compile(re.escape(key), re.IGNORECASE)},
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

    lookup = get_flower_lookup()
    lower_key = key.lower()
    if lower_key in lookup:
        return json.dumps(lookup[lower_key])

    normalized = _norm_flower_map.get(lower_key)
    if normalized and normalized in lookup:
        return json.dumps(lookup[normalized])

    for candidate, normalized_name in _norm_flower_map.items():
        if (candidate in lower_key or lower_key in candidate) and normalized_name in lookup:
            return json.dumps(lookup[normalized_name])

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
    """
    Execute FAISS vector search against the full knowledge stack.
    Always calls get_knowledge_base() to ensure documents, embeddings, and FAISS
    are fully loaded before searching. Raises RuntimeError (→ HTTP 503) if unavailable.
    """
    docs, embed_model, faiss_index = get_knowledge_base()

    if not query:
        return ()

    query_vec = embed_model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True
    ).astype("float32")

    fetch_k = min(len(docs), max(k * 4, 25))
    distances, indices = faiss_index.search(query_vec, fetch_k)

    results: list[str] = []
    seen_flowers: set[str] = set()

    for idx in indices[0]:
        if 0 <= idx < len(docs):
            doc = docs[idx]
            parsed = parse_flower_doc(doc)
            flower_id = (parsed.get("Flower Name") or parsed.get("Scientific Name") or "").strip().lower()
            if not flower_id:
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
    docs = get_flower_documents()
    if 0 <= doc_idx < len(docs):
        return docs[doc_idx]
    return ""


def get_flower_doc(flower_name: str) -> Optional[str]:
    """Return exact flower document by flower_name in O(1) time using normalized string matching."""
    if not flower_name:
        return None
    get_flower_documents()
    norm_key = normalize_flower_name(flower_name)
    return _flower_docs_by_norm_name.get(norm_key)


def get_flower_summary(doc_idx: int, flower_name: str = "") -> dict:
    """
    Parse structured fields from a flower document and MongoDB lookup.
    Returns a dictionary suitable for prediction cards containing both Title Case
    keys (for frontend knowledge cards) and snake_case keys (for APIs).
    """
    doc = get_document(doc_idx) if doc_idx >= 0 else ""
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


