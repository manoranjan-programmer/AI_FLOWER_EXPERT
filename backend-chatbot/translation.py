"""
translation.py
Offline translation using Helsinki-NLP Opus-MT models via HuggingFace Transformers.
No paid APIs, no internet required after the model is first downloaded.

Supported languages
-------------------
  ta  – Tamil
  hi  – Hindi
  ml  – Malayalam
  en  – English (no-op)

The models are downloaded on first use and cached by HuggingFace.
For fully offline operation, pre-download the models before deployment.

Model naming convention: Helsinki-NLP/opus-mt-en-<lang>
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Language code -> Helsinki-NLP model ID
LANGUAGE_MODELS: dict[str, str] = {
    "ta": "Helsinki-NLP/opus-mt-en-dra",   # Dravidian multilingual → includes Tamil
    "hi": "Helsinki-NLP/opus-mt-en-hi",    # Hindi
    "ml": "Helsinki-NLP/opus-mt-en-dra",   # Dravidian multilingual → includes Malayalam
    "te": "Helsinki-NLP/opus-mt-en-dra",   # Dravidian multilingual → includes Telugu
    "kn": "Helsinki-NLP/opus-mt-en-dra",   # Dravidian multilingual → includes Kannada
    "es": "Helsinki-NLP/opus-mt-en-es",    # Spanish
    "fr": "Helsinki-NLP/opus-mt-en-fr",    # French
    "de": "Helsinki-NLP/opus-mt-en-de",    # German
    "en": "",                              # no translation needed
}

# Prefix tokens required by opus-mt-en-dra for specific languages
LANGUAGE_PREFIXES: dict[str, str] = {
    "ta": ">>tam<<",   # Tamil
    "ml": ">>mal<<",   # Malayalam
    "te": ">>tel<<",   # Telugu
    "kn": ">>kan<<",   # Kannada
}

# Cache loaded pipelines: lang_code -> transformers pipeline
_pipelines: dict[str, object] = {}


def _get_pipeline(lang_code: str):
    """Lazy-load the translation pipeline for a given language code."""
    if lang_code in _pipelines:
        return _pipelines[lang_code]

    import torch
    from transformers import pipeline as hf_pipeline

    model_id = LANGUAGE_MODELS.get(lang_code)
    if not model_id:
        return None

    logger.info("Loading translation model '%s' for lang='%s' …", model_id, lang_code)
    device = 0 if torch.cuda.is_available() else -1
    pipe = hf_pipeline(
        "translation",
        model=model_id,
        tokenizer=model_id,
        framework="pt",
        device=device,
    )
    _pipelines[lang_code] = pipe
    logger.info("Translation model for '%s' loaded successfully.", lang_code)
    return pipe


def preload(default_langs: tuple[str, ...] = ("hi", "ta")) -> None:
    """Preload common translation models during app startup for zero first-request latency."""
    logger.info("Preloading translation pipelines for %s …", default_langs)
    for lang in default_langs:
        try:
            _get_pipeline(lang)
        except Exception as exc:
            logger.warning("Could not preload translation pipeline for lang='%s': %s", lang, exc)


def _translate_with_llm(text: str, target_lang: str) -> str:
    """Fallback LLM-based translation for any supported target language."""
    lang_names = {
        "ta": "Tamil",
        "hi": "Hindi",
        "ml": "Malayalam",
        "te": "Telugu",
        "kn": "Kannada",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "zh": "Chinese",
        "ja": "Japanese",
        "ar": "Arabic",
    }
    lang_name = lang_names.get(target_lang.lower(), target_lang)
    try:
        import chatbot
        prompt = (
            f"Translate the following botanical text accurately into {lang_name}.\n"
            f"Output ONLY the translated {lang_name} text without adding introductory remarks, explanations, or notes:\n\n{text}"
        )
        translated = chatbot.generate(prompt, max_tokens=256)
        return translated if (translated and translated.strip()) else text
    except Exception as exc:
        logger.error("LLM translation fallback error: %s", exc)
        return text


def translate(text: str, target_lang: str) -> str:
    """
    Translate *text* from English into *target_lang*.

    Parameters
    ----------
    text        : English source text
    target_lang : ISO 639-1 code

    Returns
    -------
    Translated string, or original text on fallback/error.
    """
    lang = target_lang.lower().strip()

    if lang == "en" or not lang or not text.strip():
        return text

    try:
        pipe = _get_pipeline(lang)
        if pipe is not None:
            prefix = LANGUAGE_PREFIXES.get(lang, "")
            lines = text.split("\n")

            non_empty_indices = []
            sources = []

            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped:
                    non_empty_indices.append(i)
                    source = f"{prefix} {stripped}".strip() if prefix else stripped
                    sources.append(source)

            if not sources:
                return text

            # Execute batch translation in ONE forward pass instead of N sequential loop passes
            results = pipe(sources, batch_size=len(sources), max_new_tokens=256)

            translated_lines = list(lines)
            for idx, res in zip(non_empty_indices, results):
                if isinstance(res, list) and len(res) > 0 and "translation_text" in res[0]:
                    translated_lines[idx] = res[0]["translation_text"]
                elif isinstance(res, dict) and "translation_text" in res:
                    translated_lines[idx] = res["translation_text"]

            return "\n".join(translated_lines)
    except Exception as exc:
        logger.warning("HuggingFace pipeline translation failed for lang='%s': %s. Using LLM fallback.", lang, exc)

    return _translate_with_llm(text, lang)
