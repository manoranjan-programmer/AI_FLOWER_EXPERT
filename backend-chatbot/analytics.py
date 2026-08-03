"""
analytics.py
Asynchronous Chatbot Analytics System for Flower AI Expert.

Exposes:
  - AnalyticsLogger: ThreadPool-backed background MongoDB logging system.
  - APIRouter prefix="/api/analytics":
      GET /api/analytics/kpis             – Overview KPIs & summary stats
      GET /api/analytics/performance      – Latency & usage trends over time
      GET /api/analytics/predictions      – Top searched flowers & prediction distribution
      GET /api/analytics/user-activity   – User sessions & activity logs
      GET /api/analytics/chat-logs        – Searchable, filterable chat interaction records
      GET /api/analytics/classification-logs – Searchable image prediction records
      GET /api/analytics/error-logs       – Error breakdown & diagnostics
      GET /api/analytics/feedback         – User feedback stats & comments
      POST /api/analytics/feedback        – Log like/dislike user feedback
      GET /api/analytics/export           – Export analytics data as JSON or CSV
"""

from __future__ import annotations

import asyncio
import csv
import datetime
import io
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel

try:
    import pymongo
except ImportError:
    pymongo = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MongoDB Configuration & Collection Connections
# ---------------------------------------------------------------------------
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME: str = os.getenv("MONGO_DB", "test")

# Collection names
CHAT_ANALYTICS_COLL = "Chatbot_Performance_Analytics"
CLASSIFY_ANALYTICS_COLL = "Classification_Analytics"
USER_ACTIVITY_COLL = "User_Activity"
FEEDBACK_ANALYTICS_COLL = "Chatbot_Feedback"

# Module-level singleton MongoDB client connection & DB instance
_mongo_client: Optional[pymongo.MongoClient] = None
_mongo_db = None
_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="AnalyticsLogger")


def _get_db():
    """Retrieve singleton MongoDB database instance using active connection pool."""
    global _mongo_client, _mongo_db
    if pymongo is None:
        return None

    if _mongo_db is not None:
        return _mongo_db

    # 1. Re-use knowledge module MongoDB client connection if available
    try:
        import knowledge
        if getattr(knowledge, "_mongo_client", None) is not None:
            _mongo_client = knowledge._mongo_client
            _mongo_db = _mongo_client[MONGO_DB_NAME]
            return _mongo_db
    except Exception:
        pass

    # 2. Initialize a singleton connection pool
    try:
        _mongo_client = pymongo.MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=3000,
            maxPoolSize=20,
            minPoolSize=2,
        )
        _mongo_db = _mongo_client[MONGO_DB_NAME]
        return _mongo_db
    except Exception as exc:
        logger.warning("MongoDB Analytics connection error: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _get_utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _estimate_tokens(text: str) -> int:
    """Rough estimation of token count from character count."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _extract_device_info(request: Optional[Request]) -> Dict[str, Any]:
    """Extract browser/device info and IP from FastAPI request headers."""
    if request is None:
        return {"user_agent": "Unknown", "ip": "Unknown"}
    
    user_agent = request.headers.get("user-agent", "Unknown")
    client_ip = request.client.host if request.client else "Unknown"
    
    # Simple browser detection from user agent
    browser = "Other"
    ua_lower = user_agent.lower()
    if "edg" in ua_lower:
        browser = "Edge"
    elif "chrome" in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower:
        browser = "Safari"

    os_type = "Unknown"
    if "windows" in ua_lower:
        os_type = "Windows"
    elif "mac" in ua_lower or "darwin" in ua_lower:
        os_type = "macOS"
    elif "linux" in ua_lower:
        os_type = "Linux"
    elif "android" in ua_lower:
        os_type = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_type = "iOS"

    return {
        "user_agent": user_agent,
        "browser": browser,
        "os": os_type,
        "ip": client_ip,
    }


# ---------------------------------------------------------------------------
# Asynchronous Background Write Logging Engine
# ---------------------------------------------------------------------------
class AnalyticsLogger:
    @staticmethod
    def _write_doc(collection_name: str, doc: dict) -> None:
        """Internal synchronous worker function executed in ThreadPool."""
        try:
            db = _get_db()
            if db is not None:
                db[collection_name].insert_one(doc)
        except Exception as exc:
            logger.warning("Failed writing analytics doc to '%s': %s", collection_name, exc)

    @classmethod
    def log_chat(
        cls,
        session_id: str,
        user_prompt: str,
        ai_response: str,
        flower_context: str = "",
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        response_format: str = "json",
        generation_time_ms: float = 0.0,
        retrieval_time_ms: float = 0.0,
        total_processing_time_ms: float = 0.0,
        model_name: str = "Flower_AI_Bot",
        status: str = "success",
        error_info: str = "",
        request: Optional[Request] = None,
        transcript: Optional[List[dict]] = None,
    ) -> None:
        """Submit chat interaction logging to ThreadPool without blocking response."""
        device_info = _extract_device_info(request)
        est_prompt_tokens = _estimate_tokens(user_prompt)
        est_completion_tokens = _estimate_tokens(ai_response)
        
        doc = {
            "session_id": session_id or "session_general",
            "conversation_id": f"conv_{int(time.time() * 1000)}",
            "user_id": user_id or "anonymous",
            "username": username or "Guest User",
            "email": email or "guest@flower.ai",
            "flower_context": flower_context or "General Botany",
            "user_prompt": user_prompt,
            "ai_response": ai_response,
            "response_format": response_format,
            "generation_time_ms": round(generation_time_ms, 2),
            "retrieval_time_ms": round(retrieval_time_ms, 2),
            "total_processing_time_ms": round(total_processing_time_ms, 2),
            "model_name": model_name,
            "token_usage": {
                "prompt_tokens": est_prompt_tokens,
                "completion_tokens": est_completion_tokens,
                "total_tokens": est_prompt_tokens + est_completion_tokens,
            },
            "timestamp": _get_utc_now_iso(),
            "status": status,
            "error_info": error_info,
            "device_info": device_info,
            "transcript": transcript or [],
        }

        _executor.submit(cls._write_doc, CHAT_ANALYTICS_COLL, doc)
        cls.log_activity(
            action="chat",
            user_id=user_id,
            username=username,
            email=email,
            session_id=session_id,
            details=f"Prompt: {user_prompt[:40]}...",
            request=request,
        )

    @classmethod
    def log_classification(
        cls,
        session_id: str,
        predicted_flower: str,
        confidence: float,
        classification_time_ms: float,
        total_processing_time_ms: float,
        filename: str = "",
        content_type: str = "image/jpeg",
        file_size_bytes: int = 0,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        model_name: str = "EfficientNet_Flower_Classifier",
        status: str = "success",
        error_info: str = "",
        request: Optional[Request] = None,
    ) -> None:
        """Submit image prediction logging to ThreadPool."""
        device_info = _extract_device_info(request)
        doc = {
            "session_id": session_id,
            "user_id": user_id or "anonymous",
            "username": username or "Guest User",
            "email": email or "guest@flower.ai",
            "uploaded_image_metadata": {
                "filename": filename or "uploaded_image.jpg",
                "content_type": content_type or "image/jpeg",
                "size_bytes": file_size_bytes,
                "size_kb": round(file_size_bytes / 1024, 2) if file_size_bytes else 0,
            },
            "predicted_flower": predicted_flower,
            "classifier_confidence": round(confidence, 2),
            "classification_time_ms": round(classification_time_ms, 2),
            "total_processing_time_ms": round(total_processing_time_ms, 2),
            "model_name": model_name,
            "timestamp": _get_utc_now_iso(),
            "status": status,
            "error_info": error_info,
            "device_info": device_info,
        }

        _executor.submit(cls._write_doc, CLASSIFY_ANALYTICS_COLL, doc)
        cls.log_activity(
            action="predict",
            user_id=user_id,
            username=username,
            email=email,
            session_id=session_id,
            details=f"Identified {predicted_flower} ({round(confidence, 1)}%)",
            request=request,
        )

    @classmethod
    def log_activity(
        cls,
        action: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        session_id: Optional[str] = None,
        details: str = "",
        request: Optional[Request] = None,
    ) -> None:
        """Log user auth, navigation, or interaction activity."""
        device_info = _extract_device_info(request)
        doc = {
            "user_id": user_id or "anonymous",
            "username": username or "Guest User",
            "email": email or "guest@flower.ai",
            "action": action,
            "session_id": session_id or "",
            "details": details,
            "timestamp": _get_utc_now_iso(),
            "device_info": device_info,
        }
        _executor.submit(cls._write_doc, USER_ACTIVITY_COLL, doc)

    @classmethod
    def log_feedback(
        cls,
        session_id: str,
        feedback_type: str,  # "like" | "dislike"
        feedback_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        prompt: str = "",
        response: str = "",
        flower_name: str = "General Botany",
        rating: int = 0,
        selected_reasons: Optional[List[str]] = None,
        custom_comment: str = "",
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        classifier_confidence: Optional[float] = None,
        ai_response_time_ms: Optional[float] = None,
        classification_time_ms: Optional[float] = None,
        model_name: str = "Flower_AI_Bot",
        request_status: str = "success",
        feedback_status: str = "new",
        request: Optional[Request] = None,
    ) -> None:
        """Log comprehensive user feedback on AI responses asynchronously."""
        device_info = _extract_device_info(request)
        fb_id = feedback_id or f"fb_{int(time.time() * 1000)}"
        doc = {
            "feedback_id": fb_id,
            "session_id": session_id or "session_general",
            "conversation_id": conversation_id or f"conv_{int(time.time() * 1000)}",
            "user_id": user_id or "anonymous",
            "username": username or "Guest User",
            "email": email or "guest@flower.ai",
            "timestamp": _get_utc_now_iso(),
            "flower_name": flower_name or "General Botany",
            "user_prompt": prompt,
            "ai_response": response,
            "feedback_type": "dislike" if rating <= 3 else "like",  # derived from rating
            "rating": max(0, min(5, int(rating or 0))),  # 1 to 5 stars
            "selected_reasons": selected_reasons or [],
            "custom_comment": custom_comment,
            "classifier_confidence": classifier_confidence,
            "ai_response_time_ms": ai_response_time_ms,
            "classification_time_ms": classification_time_ms,
            "model_name": model_name,
            "request_status": request_status,
            "browser_info": device_info.get("browser", "Unknown"),
            "device_info": device_info,
            "feedback_status": feedback_status,  # "new" | "reviewed" | "resolved"
        }
        _executor.submit(cls._write_doc, FEEDBACK_ANALYTICS_COLL, doc)


# ---------------------------------------------------------------------------
# FastAPI Router for Analytics Dashboard & Feedback Management API
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class FeedbackSubmission(BaseModel):
    feedback_id: Optional[str] = None
    session_id: Optional[str] = "session_general"
    conversation_id: Optional[str] = None
    user_id: Optional[str] = "anonymous"
    username: Optional[str] = "Guest User"
    email: Optional[str] = "guest@flower.ai"
    flower_name: Optional[str] = "General Botany"
    user_prompt: Optional[str] = ""
    ai_response: Optional[str] = ""
    feedback_type: Optional[str] = "like"   # "like" | "dislike"
    rating: Optional[int] = 0               # 0 to 5 stars
    selected_reasons: Optional[List[str]] = []
    custom_comment: Optional[str] = ""
    classifier_confidence: Optional[float] = None
    ai_response_time_ms: Optional[float] = None
    classification_time_ms: Optional[float] = None
    model_name: Optional[str] = "Flower_AI_Bot"
    request_status: Optional[str] = "success"
    feedback_status: Optional[str] = "new"


@router.post("/feedback")
async def submit_feedback(request: Request):
    """
    Submit and store user feedback directly into MongoDB Chatbot_Feedback collection.
    Accepts any JSON body — no strict validation — to prevent 422 errors.
    """
    from fastapi import HTTPException

    # Parse raw JSON body — no Pydantic validation, accepts any shape
    try:
        body = await request.json()
    except Exception as parse_err:
        logger.warning("Failed to parse feedback JSON body: %s", parse_err)
        raise HTTPException(status_code=400, detail="Invalid JSON body in feedback request.")

    def _str(v, default=""):
        if v is None:
            return default
        return str(v).strip() or default

    def _int_clamp(v, lo=0, hi=5, default=0):
        try:
            return max(lo, min(hi, int(v or default)))
        except (TypeError, ValueError):
            return default

    def _list(v, default=None):
        if isinstance(v, list):
            return [str(i) for i in v if i is not None]
        return default or []

    ts_now = f"fb_{int(time.time() * 1000)}"
    fb_id = _str(body.get("feedback_id"), ts_now)
    device_info = _extract_device_info(request)
    rating = _int_clamp(body.get("rating"), 0, 5, 0)
    feedback_type = "dislike" if rating <= 3 else "like"

    doc = {
        "feedback_id": fb_id,
        "session_id": _str(body.get("session_id"), "session_general"),
        "conversation_id": _str(body.get("conversation_id"), f"conv_{int(time.time() * 1000)}"),
        "user_id": _str(body.get("user_id"), "anonymous"),
        "username": _str(body.get("username"), "Guest User"),
        "email": _str(body.get("email"), "guest@flower.ai"),
        "timestamp": _get_utc_now_iso(),
        "flower_name": _str(body.get("flower_name"), "General Botany"),
        "user_prompt": _str(body.get("user_prompt"), ""),
        "ai_response": _str(body.get("ai_response"), ""),
        "feedback_type": feedback_type,
        "rating": rating,
        "selected_reasons": _list(body.get("selected_reasons")),
        "custom_comment": _str(body.get("custom_comment"), ""),
        "classifier_confidence": body.get("classifier_confidence"),
        "ai_response_time_ms": body.get("ai_response_time_ms"),
        "classification_time_ms": body.get("classification_time_ms"),
        "model_name": _str(body.get("model_name"), "Flower_AI_Bot"),
        "request_status": _str(body.get("request_status"), "success"),
        "browser_info": device_info.get("browser", "Unknown"),
        "device_info": device_info,
        "feedback_status": _str(body.get("feedback_status"), "new"),
    }

    # Direct synchronous MongoDB insert — guarantees feedback reaches the DB
    try:
        db = _get_db()
        if db is None:
            logger.error("MongoDB unavailable: cannot save feedback doc %s", fb_id)
            raise HTTPException(status_code=503, detail="Database unavailable. Please try again later.")
        db[FEEDBACK_ANALYTICS_COLL].insert_one(doc)
        logger.info("Feedback %s (%s) saved to MongoDB '%s'", fb_id, doc["feedback_type"], FEEDBACK_ANALYTICS_COLL)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to insert feedback %s into MongoDB: %s", fb_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {str(exc)}")

    return {
        "status": "ok",
        "feedback_id": fb_id,
        "message": "Feedback saved successfully to MongoDB Chatbot_Feedback",
    }


@router.get("/kpis")
async def get_kpis():
    """Retrieve top-level Executive Dashboard KPIs."""
    db = _get_db()
    if db is None:
        # Fallback dummy/empty response if DB unavailable
        return {
            "total_users": 0,
            "total_chats": 0,
            "total_predictions": 0,
            "avg_confidence": 0.0,
            "avg_response_time_ms": 0.0,
            "avg_classification_time_ms": 0.0,
            "like_count": 0,
            "dislike_count": 0,
            "satisfaction_rate": 100.0,
            "error_count": 0,
        }

    try:
        # User count
        users_coll = os.getenv("MONGO_USERS_COLLECTION", "Users")
        total_users = db[users_coll].count_documents({}) if users_coll in db.list_collection_names() else 0
        if total_users == 0:
            distinct_users = db[CHAT_ANALYTICS_COLL].distinct("user_id")
            total_users = len([u for u in distinct_users if u != "anonymous"]) or 1

        total_chats = db[CHAT_ANALYTICS_COLL].count_documents({})
        total_predictions = db[CLASSIFY_ANALYTICS_COLL].count_documents({})

        # Averages for chats
        chat_avg_pipeline = [
            {"$group": {
                "_id": None,
                "avg_response_time": {"$avg": "$total_processing_time_ms"},
                "avg_generation_time": {"$avg": "$generation_time_ms"},
                "avg_retrieval_time": {"$avg": "$retrieval_time_ms"},
                "error_count": {"$sum": {"$cond": [{"$eq": ["$status", "error"]}, 1, 0]}},
            }}
        ]
        chat_stats = list(db[CHAT_ANALYTICS_COLL].aggregate(chat_avg_pipeline))
        chat_res = chat_stats[0] if chat_stats else {}

        # Averages for classifications
        classify_avg_pipeline = [
            {"$group": {
                "_id": None,
                "avg_confidence": {"$avg": "$classifier_confidence"},
                "avg_classification_time": {"$avg": "$classification_time_ms"},
                "error_count": {"$sum": {"$cond": [{"$eq": ["$status", "error"]}, 1, 0]}},
            }}
        ]
        classify_stats = list(db[CLASSIFY_ANALYTICS_COLL].aggregate(classify_avg_pipeline))
        classify_res = classify_stats[0] if classify_stats else {}

        # Feedback stats
        likes = db[FEEDBACK_ANALYTICS_COLL].count_documents({"rating": "like"})
        dislikes = db[FEEDBACK_ANALYTICS_COLL].count_documents({"rating": "dislike"})
        total_feedback = likes + dislikes
        satisfaction_rate = round((likes / total_feedback) * 100, 1) if total_feedback > 0 else 100.0

        chat_errors = chat_res.get("error_count", 0)
        classify_errors = classify_res.get("error_count", 0)

        return {
            "total_users": max(total_users, 1),
            "total_chats": total_chats,
            "total_predictions": total_predictions,
            "avg_confidence": round(classify_res.get("avg_confidence", 98.5) or 98.5, 1),
            "avg_response_time_ms": round(chat_res.get("avg_response_time", 250.0) or 250.0, 1),
            "avg_generation_time_ms": round(chat_res.get("avg_generation_time", 200.0) or 200.0, 1),
            "avg_retrieval_time_ms": round(chat_res.get("avg_retrieval_time", 50.0) or 50.0, 1),
            "avg_classification_time_ms": round(classify_res.get("avg_classification_time", 180.0) or 180.0, 1),
            "like_count": likes,
            "dislike_count": dislikes,
            "satisfaction_rate": satisfaction_rate,
            "error_count": chat_errors + classify_errors,
        }
    except Exception as exc:
        logger.error("Error building KPIs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/performance")
async def get_performance_trends(days: int = Query(7, ge=1, le=90)):
    """Retrieve time-series performance data (chats count, avg latency, streaming breakdown)."""
    db = _get_db()
    if db is None:
        return {"trends": []}

    try:
        # Group chats by date string YYYY-MM-DD
        pipeline = [
            {"$addFields": {
                "date_str": {"$substr": ["$timestamp", 0, 10]}
            }},
            {"$group": {
                "_id": "$date_str",
                "chats": {"$sum": 1},
                "avg_response_time_ms": {"$avg": "$total_processing_time_ms"},
                "avg_generation_time_ms": {"$avg": "$generation_time_ms"},
                "avg_retrieval_time_ms": {"$avg": "$retrieval_time_ms"},
                "stream_count": {"$sum": {"$cond": [{"$eq": ["$response_format", "stream"]}, 1, 0]}},
                "json_count": {"$sum": {"$cond": [{"$eq": ["$response_format", "json"]}, 1, 0]}},
                "total_tokens": {"$sum": "$token_usage.total_tokens"},
            }},
            {"$sort": {"_id": 1}}
        ]
        chat_trends = list(db[CHAT_ANALYTICS_COLL].aggregate(pipeline))

        # Group classifications by date
        class_pipeline = [
            {"$addFields": {
                "date_str": {"$substr": ["$timestamp", 0, 10]}
            }},
            {"$group": {
                "_id": "$date_str",
                "predictions": {"$sum": 1},
                "avg_classification_time_ms": {"$avg": "$classification_time_ms"},
                "avg_confidence": {"$avg": "$classifier_confidence"},
            }},
            {"$sort": {"_id": 1}}
        ]
        class_trends = {item["_id"]: item for item in db[CLASSIFY_ANALYTICS_COLL].aggregate(class_pipeline)}

        combined = []
        for c in chat_trends:
            date_key = c["_id"]
            cl = class_trends.get(date_key, {})
            combined.append({
                "date": date_key,
                "chats": c["chats"],
                "predictions": cl.get("predictions", 0),
                "avg_response_time_ms": round(c.get("avg_response_time_ms", 0), 1),
                "avg_generation_time_ms": round(c.get("avg_generation_time_ms", 0), 1),
                "avg_retrieval_time_ms": round(c.get("avg_retrieval_time_ms", 0), 1),
                "avg_classification_time_ms": round(cl.get("avg_classification_time_ms", 0), 1),
                "avg_confidence": round(cl.get("avg_confidence", 0), 1),
                "stream_count": c.get("stream_count", 0),
                "json_count": c.get("json_count", 0),
                "total_tokens": c.get("total_tokens", 0),
            })

        return {"trends": combined}
    except Exception as exc:
        logger.error("Error retrieving performance trends: %s", exc)
        return {"trends": []}


@router.get("/predictions")
async def get_predictions_distribution():
    """Retrieve search frequency and confidence distribution by flower type."""
    db = _get_db()
    if db is None:
        return {"flower_distribution": [], "confidence_histogram": []}

    try:
        # Distribution by predicted flower
        pipeline = [
            {"$group": {
                "_id": "$predicted_flower",
                "count": {"$sum": 1},
                "avg_confidence": {"$avg": "$classifier_confidence"},
                "avg_time_ms": {"$avg": "$classification_time_ms"},
            }},
            {"$sort": {"count": -1}},
            {"$limit": 15}
        ]
        raw_flowers = list(db[CLASSIFY_ANALYTICS_COLL].aggregate(pipeline))
        flowers = [
            {
                "flower": f["_id"] or "Unknown",
                "count": f["count"],
                "avg_confidence": round(f["avg_confidence"] or 0, 1),
                "avg_time_ms": round(f["avg_time_ms"] or 0, 1),
            }
            for f in raw_flowers
        ]

        # Confidence Histogram brackets (<80, 80-90, 90-95, 95-98, 98-100)
        conf_pipeline = [
            {"$bucket": {
                "groupBy": "$classifier_confidence",
                "boundaries": [0, 80, 90, 95, 98, 101],
                "default": "Other",
                "output": {
                    "count": {"$sum": 1}
                }
            }}
        ]
        conf_raw = list(db[CLASSIFY_ANALYTICS_COLL].aggregate(conf_pipeline))
        range_labels = {
            0: "< 80%",
            80: "80% - 89%",
            90: "90% - 94%",
            95: "95% - 97%",
            98: "98% - 100%",
        }
        histogram = [
            {"range": range_labels.get(item["_id"], str(item["_id"])), "count": item["count"]}
            for item in conf_raw if isinstance(item["_id"], (int, float))
        ]

        return {
            "flower_distribution": flowers,
            "confidence_histogram": histogram,
        }
    except Exception as exc:
        logger.error("Error retrieving prediction distribution: %s", exc)
        return {"flower_distribution": [], "confidence_histogram": []}


@router.get("/user-activity")
async def get_user_activity(limit: int = 50):
    """Retrieve user activity timeline and engaged users list."""
    db = _get_db()
    if db is None:
        return {"activities": [], "active_users": []}

    try:
        activities = list(
            db[USER_ACTIVITY_COLL]
            .find({}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )

        user_summary_pipeline = [
            {"$group": {
                "_id": "$email",
                "username": {"$first": "$username"},
                "user_id": {"$first": "$user_id"},
                "action_count": {"$sum": 1},
                "last_active": {"$max": "$timestamp"},
                "device": {"$first": "$device_info.browser"},
            }},
            {"$sort": {"last_active": -1}},
            {"$limit": 20}
        ]
        users = list(db[USER_ACTIVITY_COLL].aggregate(user_summary_pipeline))
        formatted_users = [
            {
                "email": u["_id"],
                "username": u.get("username", "Botanist User"),
                "user_id": u.get("user_id", "anonymous"),
                "actions": u.get("action_count", 0),
                "last_active": u.get("last_active", ""),
                "browser": u.get("device", "Unknown"),
            }
            for u in users
        ]

        return {
            "activities": activities,
            "active_users": formatted_users,
        }
    except Exception as exc:
        logger.error("Error fetching user activity: %s", exc)
        return {"activities": [], "active_users": []}


@router.get("/chat-logs")
async def get_chat_logs(
    query: Optional[str] = None,
    flower: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """Filterable and searchable chat records."""
    db = _get_db()
    if db is None:
        return {"logs": [], "total": 0}

    try:
        filter_doc = {}
        if flower:
            filter_doc["flower_context"] = {"$regex": flower, "$options": "i"}
        if status:
            filter_doc["status"] = status
        if query:
            filter_doc["$or"] = [
                {"user_prompt": {"$regex": query, "$options": "i"}},
                {"ai_response": {"$regex": query, "$options": "i"}},
                {"username": {"$regex": query, "$options": "i"}},
            ]

        total = db[CHAT_ANALYTICS_COLL].count_documents(filter_doc)
        logs = list(
            db[CHAT_ANALYTICS_COLL]
            .find(filter_doc, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        return {"logs": logs, "total": total}
    except Exception as exc:
        logger.error("Error fetching chat logs: %s", exc)
        return {"logs": [], "total": 0}


@router.get("/classification-logs")
async def get_classification_logs(
    flower: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """Filterable image prediction records."""
    db = _get_db()
    if db is None:
        return {"logs": [], "total": 0}

    try:
        filter_doc = {}
        if flower:
            filter_doc["predicted_flower"] = {"$regex": flower, "$options": "i"}
        if status:
            filter_doc["status"] = status

        total = db[CLASSIFY_ANALYTICS_COLL].count_documents(filter_doc)
        logs = list(
            db[CLASSIFY_ANALYTICS_COLL]
            .find(filter_doc, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        return {"logs": logs, "total": total}
    except Exception as exc:
        logger.error("Error fetching classification logs: %s", exc)
        return {"logs": [], "total": 0}


@router.get("/error-logs")
async def get_error_logs(limit: int = 50):
    """Fetch recent backend errors from chat and classification analytics."""
    db = _get_db()
    if db is None:
        return {"errors": []}

    try:
        chat_errors = list(
            db[CHAT_ANALYTICS_COLL]
            .find({"status": "error"}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        classify_errors = list(
            db[CLASSIFY_ANALYTICS_COLL]
            .find({"status": "error"}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )

        all_errors = chat_errors + classify_errors
        all_errors.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return {"errors": all_errors[:limit]}
    except Exception as exc:
        logger.error("Error fetching error logs: %s", exc)
        return {"errors": []}


@router.get("/feedback")
async def get_feedback_logs(
    feedback_type: Optional[str] = Query(None, regex="^(like|dislike)$"),
    rating: Optional[int] = Query(None, ge=1, le=5),
    reason: Optional[str] = None,
    flower: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    """Retrieve filtered feedback logs with comprehensive satisfaction metrics and complaint breakdowns."""
    db = _get_db()
    if db is None:
        return {
            "feedback": [],
            "stats": {
                "likes": 0,
                "dislikes": 0,
                "total": 0,
                "satisfaction_rate": 100.0,
                "avg_star_rating": 5.0,
                "reasons_breakdown": {},
                "star_counts": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
                "flower_feedback": {},
            },
        }

    try:
        query_filter = {}
        if feedback_type:
            query_filter["$or"] = [
                {"feedback_type": feedback_type},
                {"rating": feedback_type},
            ]
        if rating is not None:
            query_filter["rating"] = rating
        if reason:
            query_filter["selected_reasons"] = {"$regex": reason, "$options": "i"}
        if flower:
            query_filter["flower_name"] = {"$regex": flower, "$options": "i"}
        if status:
            query_filter["feedback_status"] = status
        if search:
            query_filter["$or"] = [
                {"user_prompt": {"$regex": search, "$options": "i"}},
                {"ai_response": {"$regex": search, "$options": "i"}},
                {"custom_comment": {"$regex": search, "$options": "i"}},
                {"prompt": {"$regex": search, "$options": "i"}},
                {"feedback_text": {"$regex": search, "$options": "i"}},
            ]

        # Fetch records
        feedback_items = list(
            db[FEEDBACK_ANALYTICS_COLL]
            .find(query_filter, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )

        # Aggregate metrics across all feedback documents
        all_docs = list(db[FEEDBACK_ANALYTICS_COLL].find({}, {"_id": 0}))
        
        likes_count = 0
        dislikes_count = 0
        star_total = 0
        star_count_num = 0
        reasons_map = {}
        star_counts = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        flower_map = {}

        for doc in all_docs:
            fb_t = doc.get("feedback_type") or doc.get("rating")
            if fb_t == "like":
                likes_count += 1
            elif fb_t == "dislike":
                dislikes_count += 1

            r_num = doc.get("rating")
            if isinstance(r_num, int) and 1 <= r_num <= 5:
                star_total += r_num
                star_count_num += 1
                star_counts[str(r_num)] = star_counts.get(str(r_num), 0) + 1

            reasons = doc.get("selected_reasons", [])
            for r in reasons:
                reasons_map[r] = reasons_map.get(r, 0) + 1

            fl_name = doc.get("flower_name") or "General Botany"
            if fl_name not in flower_map:
                flower_map[fl_name] = {"like": 0, "dislike": 0}
            if fb_t in ["like", "dislike"]:
                flower_map[fl_name][fb_t] = flower_map[fl_name].get(fb_t, 0) + 1

        total_fb = likes_count + dislikes_count
        satisfaction_rate = round((likes_count / total_fb) * 100, 1) if total_fb > 0 else 100.0
        avg_star_rating = round(star_total / star_count_num, 1) if star_count_num > 0 else 5.0

        return {
            "feedback": feedback_items,
            "stats": {
                "likes": likes_count,
                "dislikes": dislikes_count,
                "total": len(all_docs),
                "satisfaction_rate": satisfaction_rate,
                "avg_star_rating": avg_star_rating,
                "reasons_breakdown": reasons_map,
                "star_counts": star_counts,
                "flower_feedback": flower_map,
            },
        }
    except Exception as exc:
        logger.error("Error fetching feedback logs: %s", exc)
        return {
            "feedback": [],
            "stats": {
                "likes": 0,
                "dislikes": 0,
                "total": 0,
                "satisfaction_rate": 100.0,
                "avg_star_rating": 5.0,
                "reasons_breakdown": {},
                "star_counts": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
                "flower_feedback": {},
            },
        }


class FeedbackStatusUpdate(BaseModel):
    status: str  # "new" | "reviewed" | "resolved"
    admin_notes: Optional[str] = None


@router.put("/feedback/{feedback_id}")
async def update_feedback_status(feedback_id: str, data: FeedbackStatusUpdate):
    """Update feedback status ('new', 'reviewed', 'resolved') in MongoDB Chatbot_Feedback collection."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    try:
        update_fields = {"feedback_status": data.status}
        if data.admin_notes is not None:
            update_fields["admin_notes"] = data.admin_notes

        result = db[FEEDBACK_ANALYTICS_COLL].update_one(
            {"feedback_id": feedback_id},
            {"$set": update_fields}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Feedback entry not found")

        return {"status": "ok", "message": f"Feedback status updated to '{data.status}'"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error updating feedback status: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export")
async def export_analytics(
    type: str = Query("chats", regex="^(chats|feedback)$"),
    format: str = Query("json", regex="^(json|csv)$")
):
    """Export chat or feedback analytics records in JSON or CSV format."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    try:
        if type == "feedback":
            records = list(db[FEEDBACK_ANALYTICS_COLL].find({}, {"_id": 0}).limit(2000))
            if format == "csv":
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow([
                    "Feedback ID", "Session ID", "User ID", "Email", "Timestamp",
                    "Flower Name", "User Prompt", "AI Response", "Type", "Rating (Stars)",
                    "Selected Reasons", "Custom Comment", "Status"
                ])
                for r in records:
                    reasons_str = "; ".join(r.get("selected_reasons", []))
                    writer.writerow([
                        r.get("feedback_id", ""),
                        r.get("session_id", ""),
                        r.get("user_id", ""),
                        r.get("email", ""),
                        r.get("timestamp", ""),
                        r.get("flower_name", ""),
                        r.get("user_prompt", "").replace("\n", " "),
                        r.get("ai_response", "").replace("\n", " ")[:150],
                        r.get("feedback_type", r.get("rating", "")),
                        r.get("rating", 0),
                        reasons_str,
                        r.get("custom_comment", r.get("feedback_text", "")).replace("\n", " "),
                        r.get("feedback_status", "new"),
                    ])
                return Response(
                    content=output.getvalue(),
                    media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=chatbot_feedback_export.csv"}
                )
            return {"data": records}

        # Default chats export
        chat_records = list(db[CHAT_ANALYTICS_COLL].find({}, {"_id": 0}).limit(1000))
        
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Session ID", "User ID", "Email", "Flower Context", "Prompt",
                "Response", "Total Time (ms)", "Gen Time (ms)", "Timestamp", "Status"
            ])
            for r in chat_records:
                writer.writerow([
                    r.get("session_id", ""),
                    r.get("user_id", ""),
                    r.get("email", ""),
                    r.get("flower_context", ""),
                    r.get("user_prompt", "").replace("\n", " "),
                    r.get("ai_response", "").replace("\n", " ")[:100],
                    r.get("total_processing_time_ms", 0),
                    r.get("generation_time_ms", 0),
                    r.get("timestamp", ""),
                    r.get("status", ""),
                ])
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=chatbot_analytics_export.csv"}
            )
        
        return {"data": chat_records}
    except Exception as exc:
        logger.error("Error exporting analytics: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
