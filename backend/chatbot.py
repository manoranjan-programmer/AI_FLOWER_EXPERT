"""
chatbot.py
Local LLM service for Flower AI Expert using Hugging Face Transformers.

Environment variables (.env):
  PHI_BACKEND      – "transformers"                        default: transformers
  PHI_HF_MODEL     – HuggingFace model ID                  default: Qwen/Qwen2.5-0.5B-Instruct
  PHI_MAX_TOKENS   – max tokens to generate                 default: 1024
  PHI_TEMPERATURE  – sampling temperature                   default: 0.7
  PHI_TOP_P        – nucleus sampling top_p                 default: 0.9
  HF_HOME          – cache dir for HuggingFace downloads    default: models/hf_cache
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import asyncio
import re
import time
import atexit

import knowledge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config  (read at import time — .env is already loaded by app.py)
# ---------------------------------------------------------------------------
PHI_BACKEND: str     = os.getenv("PHI_BACKEND", "transformers").lower()
PHI_HF_MODEL: str    = os.getenv("PHI_HF_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
PHI_MAX_TOKENS: int  = int(os.getenv("PHI_MAX_TOKENS", "1024"))
PHI_TEMPERATURE: float = float(os.getenv("PHI_TEMPERATURE", "0.3"))
PHI_TOP_P: float     = float(os.getenv("PHI_TOP_P", "0.9"))

import gc

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------
_backend: str   = ""
_model          = None   # AutoModelForCausalLM instance
_tokenizer      = None   # AutoTokenizer instance

# Executor for running blocking pipeline calls without blocking asyncio loop
_executor: ThreadPoolExecutor | None = None

# Quick answer keywords — common care questions to avoid full LLM calls
_FAST_KEYWORDS = (
    r"\bwater\b",
    r"\bsun(light|shine)?\b",
    r"\bsoil\b",
    r"\bprun(e|ing)\b",
    r"\bfertil(ize|iser|izer)?\b",
    r"\bpropagat(e|ion)\b",
    r"\brepot\b",
    r"\btox(ic|ity)\b",
)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are an expert AI botanist specializing in flowers and plant care.
STRICT RULES:
1. Language: Answer ONLY in clear English. Never output Chinese/CJK characters or foreign scripts.
2. No Category Headings: Do NOT prepend section titles like "Medicinal Uses:", "Preventative Uses:", "Therapeutic Uses:", or "Common Uses:".
3. Strict Formatting: Follow the user's requested count and format strictly. If 2 points requested, output exactly 2 numbered points. If 2 lines requested, output exactly 2 complete sentences without numbers or bullets. If a table is requested, output ONLY a markdown table.
4. Completeness: Ensure all sentences are complete and end with proper punctuation.
"""


import threading

# ---------------------------------------------------------------------------
# Lazy Loaders & Thread Locks
# ---------------------------------------------------------------------------
_llm_lock = threading.Lock()
_system_prompt_lock = threading.Lock()
_cached_system_prompt: str | None = None


def get_system_prompt() -> str:
    """Read system_prompt.txt on first request and cache string (thread-safe)."""
    global _cached_system_prompt
    if _cached_system_prompt is None:
        with _system_prompt_lock:
            if _cached_system_prompt is None:
                prompt_path = Path(__file__).parent / "knowledge" / "system_prompt.txt"
                if prompt_path.exists():
                    try:
                        _cached_system_prompt = prompt_path.read_text(encoding="utf-8").strip()
                    except Exception as exc:
                        logger.warning("Error reading system_prompt.txt: %s", exc)
                        _cached_system_prompt = SYSTEM_PROMPT.strip()
                else:
                    _cached_system_prompt = SYSTEM_PROMPT.strip()
    return _cached_system_prompt


def get_llm():
    """Lazy-load LLM model and tokenizer thread-safely."""
    global _backend, _model, _tokenizer, _executor
    if _model is None:
        with _llm_lock:
            if _model is None:
                if _executor is None:
                    max_workers = min(8, (os.cpu_count() or 4))
                    _executor = ThreadPoolExecutor(max_workers=max_workers)

                import torch
                from transformers import AutoTokenizer, AutoModelForCausalLM

                logger.info("=== Loading LLM Backend ===")
                logger.info("  Active Backend : transformers")
                logger.info("  Model Name     : %s", PHI_HF_MODEL)

                num_threads = max(1, min(2, (os.cpu_count() or 4)))
                torch.set_num_threads(num_threads)

                logger.info("Loading tokenizer for '%s'...", PHI_HF_MODEL)
                _tokenizer = AutoTokenizer.from_pretrained(
                    PHI_HF_MODEL,
                    trust_remote_code=True,
                )
                if _tokenizer.pad_token is None:
                    _tokenizer.pad_token = _tokenizer.eos_token

                torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
                device_map = "auto" if torch.cuda.is_available() else None

                logger.info("Loading model weights (device_map=%s, dtype=%s)...", device_map, torch_dtype)
                _model = AutoModelForCausalLM.from_pretrained(
                    PHI_HF_MODEL,
                    torch_dtype=torch_dtype,
                    device_map=device_map,
                    trust_remote_code=True,
                    low_cpu_mem_usage=True,
                )

                _backend = "transformers"
                gc.collect()
                logger.info("LLM Loaded")
    return _model, _tokenizer


def load() -> None:
    """No-op for zero startup memory overhead. Model loads on demand via get_llm()."""
    pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(
    user_message: str,
    flower_name: str = "",
    context_docs: list[str] = None,
    history: list[dict] = None,
    max_tokens: int | None = None,
) -> str:
    """Generate a response using the loaded Hugging Face Transformers LLM backend."""
    get_llm()

    parsed = _parse_request_constraints(user_message)
    if max_tokens:
        tokens_limit = max_tokens
    elif parsed.get('count') and parsed['count'] <= 3:
        tokens_limit = min(PHI_MAX_TOKENS, 180)
    else:
        tokens_limit = min(PHI_MAX_TOKENS, 380)

    # Provide enough context for complete answers
    compact_doc = "\n\n".join([d[:1200].strip() for d in (context_docs or [])[:5] if d.strip()])
    history_str = "\n".join([f"{h.get('role')}:{h.get('content')}" for h in (history or [])[-4:]])
    cache_key = f"bk={_backend}|flower={flower_name}|user={user_message.strip()}|ctx={compact_doc}|hist={history_str}|max_tok={tokens_limit}"

    return _generate_cached(cache_key, user_message, flower_name, compact_doc, history_str, tokens_limit)


@lru_cache(maxsize=128)
def _generate_cached(
    cache_key: str,
    user_message: str,
    flower_name: str,
    compact_doc: str,
    history_str: str,
    max_tokens: int,
) -> str:
    """Internal cached generator. Arguments must be hashable strings."""
    context_docs = [compact_doc] if compact_doc else []
    history = []
    if history_str:
        for line in history_str.splitlines():
            role, _, content = line.partition(":")
            history.append({"role": role, "content": content})

    fast = _fast_answer_from_knowledge(user_message, flower_name, context_docs)
    if fast:
        return fast

    return _generate_transformers(user_message, flower_name, context_docs, history, max_tokens)


_PLEASANTRY_MAP = [
    (r"^\s*(thank\s*you|thanks|thx|tq)\b", "You're very welcome! If you have any more questions about {flower} or plant care, feel free to ask!"),
    (r"^\s*(hi|hello|hey|greetings)\b", "Hello! How can I help you with {flower} or plant care today?"),
    (r"^\s*(bye|goodbye|see\s*ya)\b", "Goodbye! Happy gardening!"),
    (r"^\s*(ok|okay|great|awesome|cool|nice)\b", "Glad to help! Let me know if you need anything else about {flower}."),
]


def _fast_answer_from_knowledge(
    user_message: str,
    flower_name: str,
    context_docs: list[str],
) -> str | None:
    """
    Handles common conversational pleasantries (e.g. 'thank you', 'hi', 'bye') 
    instantly with a polite response ONLY if the message is purely a short greeting/thanks
    without a specific question. Returns None for technical or multi-word questions.
    """
    if not user_message:
        return None

    msg_lower = user_message.strip().lower()
    words = msg_lower.split()

    question_indicators = [
        'what', 'how', 'why', 'can', 'is', 'tell', 'show', 'give', 'where', 'when',
        'which', 'care', 'water', 'sun', 'soil', 'use', 'medicinal', 'poison', 'toxic',
        'petal', 'leaf', 'flower', 'plant', 'details', 'info', 'summary', 'season', 'detail'
    ]
    if len(words) > 3 or any(qi in msg_lower for qi in question_indicators):
        return None

    flower_display = flower_name.capitalize() if flower_name else "flowers"

    for pattern, response_template in _PLEASANTRY_MAP:
        if re.search(pattern, msg_lower):
            return response_template.format(flower=flower_display)

    return None


_WORD_TO_NUM = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
    '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
}

_WORD_NAMES = {
    1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
    6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten'
}

def _parse_request_constraints(user_message: str) -> dict:
    """
    Parses user request for 'table', 'lines', or 'points' formatting constraints.
    Returns dict with:
      - 'type': 'table' | 'lines' | 'points' | None
      - 'count': int | None
      - 'transformed_instruction': str | None
    """
    if not user_message:
        return {'type': None, 'count': None, 'transformed_instruction': None}

    msg_lower = user_message.lower()

    # 1. Table constraint
    if re.search(r'\b(?:table|tabular)\b', msg_lower):
        inst = "Format response ONLY as a Markdown table. Do not include introductory text, explanations, or headings outside the table."
        return {'type': 'table', 'count': None, 'transformed_instruction': inst}

    num_pattern = r'\b(one|two|three|four|five|six|seven|eight|nine|ten|single|10|[1-9])\b'

    # 2. Lines/sentences constraint
    if re.search(num_pattern + r'.{0,30}\b(?:lines?|sentences?)\b', msg_lower) or re.search(r'\b(?:in\s+)?(one|two|three|four|five|six|seven|eight|nine|ten|10|[1-9])\s+(?:lines?|sentences?)\b', msg_lower):
        m = re.search(num_pattern, msg_lower)
        num_str = m.group(1).lower() if m else 'one'
        count = _WORD_TO_NUM.get(num_str, 1)
        word = _WORD_NAMES.get(count, str(count))
        inst = f"Return exactly {word} complete sentences in English. Do not use bullet points, numbering, headings, or extra lines."
        return {'type': 'lines', 'count': count, 'transformed_instruction': inst}

    # 3. Points/uses/tips/facts constraint
    keywords = r'\b(?:points?|tips?|items?|reasons?|facts?|ways?|steps?|uses?|medicinal|benefits?|details?)\b'
    if re.search(num_pattern + r'.{0,40}' + keywords, msg_lower) or re.search(r'\b(one|single|1)\s+(?:\w+\s+)?(?:use|uses|tip|tips|fact|facts|point|points|medicinal)\b', msg_lower):
        m = re.search(num_pattern, msg_lower)
        num_str = m.group(1).lower() if m else 'one'
        count = _WORD_TO_NUM.get(num_str, 1)
        word = _WORD_NAMES.get(count, str(count))
        if count == 1:
            inst = "Return exactly ONE single sentence or point in English. Do NOT include category headings, titles, or prefixes like 'Medicinal Uses:'."
        else:
            inst = f"Return exactly {word} numbered points in English (1. and 2. on separate lines). Do NOT include category headings, titles, or prefixes like 'Medicinal Uses:'."
        return {'type': 'points', 'count': count, 'transformed_instruction': inst}

    return {'type': None, 'count': None, 'transformed_instruction': None}


def _build_messages(
    user_message: str,
    flower_name: str,
    context_docs: list[str],
    history: list[dict],
) -> list[dict]:
    """Build compact messages list with minimal tokens to optimize Time-To-First-Token."""
    sys_instruction = get_system_prompt().strip()
    if flower_name:
        sys_instruction += f"\nActive flower context: {flower_name}."

    messages = [{"role": "system", "content": sys_instruction}]

    # Include at most 2 history items
    if history:
        messages.extend(history[-2:])

    user_parts = []
    if context_docs:
        clean_ctx = "\n\n".join([d[:500].strip() for d in context_docs[:1] if d.strip()])
        if clean_ctx:
            user_parts.append(f"Botanical Reference:\n{clean_ctx}")

    parsed = _parse_request_constraints(user_message)
    if parsed['transformed_instruction']:
        user_parts.append(
            f"User Question:\n{user_message}\n\n"
            f"Strict Output Format:\n{parsed['transformed_instruction']}"
        )
    else:
        user_parts.append(f"User Question:\n{user_message}")

    messages.append({"role": "user", "content": "\n\n".join(user_parts)})
    return messages


_LANG_PATTERNS = [
    ("ta", r"\b(?:in\s+)?tamil\b"),
    ("hi", r"\b(?:in\s+)?hindi\b"),
    ("ml", r"\b(?:in\s+)?malayalam\b"),
    ("te", r"\b(?:in\s+)?telugu\b"),
    ("kn", r"\b(?:in\s+)?kannada\b"),
    ("es", r"\b(?:in\s+)?spanish\b"),
    ("fr", r"\b(?:in\s+)?french\b"),
    ("de", r"\b(?:in\s+)?german\b"),
    ("zh", r"\b(?:in\s+)?chinese\b"),
    ("ja", r"\b(?:in\s+)?japanese\b"),
]

def detect_requested_language(user_message: str) -> str | None:
    if not user_message:
        return None
    msg_lower = user_message.lower()
    for code, pattern in _LANG_PATTERNS:
        if re.search(pattern, msg_lower):
            return code
    return None


def _remove_cjk_characters(text: str) -> str:
    """Removes CJK (Chinese, Japanese, Korean) characters and punctuation, ensuring clean English output."""
    if not text:
        return text

    # Remove CJK Unified Ideographs, Kana, Hangul, CJK Symbols & Punctuation, Fullwidth Forms
    cleaned = re.sub(
        r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u3000-\u303f\uff00-\uffef]+',
        '',
        text
    )

    # Clean up trailing conjunctions or prepositions before period if CJK was at the end of a sentence
    cleaned = re.sub(
        r'\b(?:and|or|with|the|a|an|for|of|to|in|on|at)\s*[\.\!\?]',
        '.',
        cleaned,
        flags=re.IGNORECASE
    )

    # Clean up trailing conjunctions/prepositions at end of text
    cleaned = re.sub(
        r'\b(?:and|or|with|the|a|an|for|of|to|in|on|at)\s*$',
        '.',
        cleaned,
        flags=re.IGNORECASE
    )

    # Clean double spaces or spaces before punctuation
    cleaned = re.sub(r'\s+([\.\!\?,;:])', r'\1', cleaned)
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)

    return cleaned.strip()


def _clean_item_text(line: str) -> str:
    """Strips leading bullet/number markers, bold category headers, inline colons, and CJK characters."""
    if not line or not line.strip():
        return ""

    # 1. Remove non-English / CJK characters
    text = _remove_cjk_characters(line)
    if not text:
        return ""

    # Match optional leading marker (e.g. "1.", "1)", "a.", "b.", "*", "-", "•")
    marker_match = re.match(r'^(\s*(?:\d+[\.\)]|[a-zA-Z][\.\)]|[-*•]|\[\d+\])\s*)', text)
    marker = marker_match.group(1) if marker_match else ""
    content = text[len(marker):] if marker else text

    # Strip leading category labels with colons (bold or plain), e.g.:
    # "**Medicinal Uses:**", "Medical Uses:", "Medicinal Uses:", "**Preventative Uses:**", "Preventative Uses:", "Preventative Use:", "Common use:"
    cleaned = re.sub(
        r'^\s*(?:\*\*)?(?:Medicinal\s+Uses?|Medical\s+Uses?|Preventative\s+Uses?|Preventive\s+Uses?|Therapeutic\s+Uses?|Common\s+Uses?|Primary\s+Uses?|Secondary\s+Uses?|Health\s+Uses?|Other\s+Uses?|Care\s+Tips?|[A-Z][a-zA-Z0-9\s\-_/\'\"]{1,35}?)\s*(?:\*\*)?\s*:\s*',
        '',
        content,
        flags=re.IGNORECASE
    ).strip()

    cleaned = cleaned.lstrip('*_` ').strip()

    if marker:
        return f"{marker.strip()} {cleaned}"
    return cleaned


FALLBACK_MEDICINAL_FLOWERS = [
    ("Echinacea purpurea (Purple Coneflower)", "Known for its powerful immune-boosting, anti-inflammatory, and antioxidant properties."),
    ("Calendula officinalis (English Marigold)", "Widely used topically for wound healing, skin soothing, and anti-inflammatory remedies."),
    ("Taraxacum officinale (Dandelion)", "Rich in antioxidants, acts as a natural diuretic and digestive health aid."),
    ("Rosa (Rose)", "Used in traditional remedies for soothing skin, calming stress, and providing antioxidant support."),
    ("Bellis perennis (Daisy)", "Traditionally applied in poultices for wound healing and easing muscle aches."),
    ("Tulipa (Tulip)", "Historically used in poultices for insect bites and skin irritation soothing."),
    ("Iris pseudacorus (Yellow Iris)", "Historically used in traditional herbal medicine for its astringent and antiseptic qualities."),
    ("Trollius europaeus (Globe Flower)", "Traditionally valued in herbal remedies for soothing inflammation."),
]


def _deduplicate_list_items(lines: list[str]) -> list[str]:
    seen_keys: set[str] = set()
    result: list[str] = []
    fallback_idx = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        m = re.search(r'^(?:\d+[\.\)]|[-*•])?\s*(?:\*\*)?([A-Za-z\s]+?)(?:\*\*)?\s*[:\-\—]', stripped)
        if m:
            plant_name = m.group(1).strip().lower()
            genus_or_name = plant_name.split()[0] if plant_name else ""
        else:
            plant_name = ""
            genus_or_name = ""

        is_duplicate = False
        if plant_name and len(plant_name) > 3:
            if plant_name in seen_keys or (genus_or_name and len(genus_or_name) > 4 and genus_or_name in seen_keys):
                is_duplicate = True
            else:
                seen_keys.add(plant_name)
                if genus_or_name and len(genus_or_name) > 4:
                    seen_keys.add(genus_or_name)

        if is_duplicate:
            while fallback_idx < len(FALLBACK_MEDICINAL_FLOWERS):
                fb_name, fb_desc = FALLBACK_MEDICINAL_FLOWERS[fallback_idx]
                fallback_idx += 1
                fb_key = fb_name.split()[0].lower()
                if fb_key not in seen_keys:
                    seen_keys.add(fb_key)
                    marker_match = re.match(r'^(\s*(?:\d+[\.\)]|[-*•])\s*)', stripped)
                    marker = marker_match.group(1) if marker_match else ""
                    new_line = f"{marker}{fb_name} - {fb_desc}"
                    result.append(new_line)
                    break
        else:
            result.append(line)

    return result


def _enforce_user_formatting(text: str, user_message: str) -> str:
    """
    Post-processing enforcer:
    - Strips repetitive category heading prefixes (e.g. 'Medicinal Uses:', 'Preventative Uses:') from output lines.
    - Removes Chinese/CJK characters and ensures clean English output.
    - Deduplicates repeated flower species in output lists.
    - Strictly enforces exact requested line count or bullet point count structure if requested by user.
    """
    if not text:
        return text

    text = _remove_cjk_characters(text)
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        cleaned = _clean_item_text(line)
        if cleaned:
            cleaned_lines.append(cleaned)

    deduped_lines = _deduplicate_list_items(cleaned_lines)
    parsed = _parse_request_constraints(user_message)
    req_type = parsed.get("type")
    req_count = parsed.get("count")

    if req_type == "lines" and req_count and len(deduped_lines) > req_count:
        deduped_lines = deduped_lines[:req_count]

    elif req_type == "points" and req_count:
        if len(deduped_lines) > req_count:
            deduped_lines = deduped_lines[:req_count]
        formatted_points = []
        for idx, line in enumerate(deduped_lines, 1):
            clean_item = re.sub(r'^(?:\d+[\.\)]|[-*•])\s*', '', line).strip()
            if req_count == 1:
                formatted_points.append(clean_item)
            else:
                formatted_points.append(f"{idx}. {clean_item}")
        return "\n".join(formatted_points)

    return "\n".join(deduped_lines)

# Incompleteness detection
# ---------------------------------------------------------------------------

# Sentence-ending punctuation that signals a truly finished response
_COMPLETE_END = re.compile(
    r"[.!?]\s*(?:[\"']|\*+|_{1,2})?\s*$|\n\s*$",
    re.MULTILINE,
)

# Patterns that indicate the model stopped mid-thought
_INCOMPLETE_PATTERNS = re.compile(
    r"(?:"
    r"[,;:]\s*$"                        # ends with comma, semicolon, or colon
    r"|\b(?:and|but|or|so|because|"    # trailing conjunctions / prepositions
    r"for|with|to|of|in|on|at|"
    r"that|which|who|when|where|"
    r"including|such|like|also|"
    r"moreover|however|therefore"
    r")\s*$"
    r"|[-\u2013\u2014]\s*$"             # trailing dash (em or en)
    r"|\*\s*$"                          # lone bullet marker
    r"|\d+\.\s*$"                       # numbered list item with no text
    r"|^\s*[-*]\s*$"                    # empty bullet line
    r")",
    re.IGNORECASE | re.MULTILINE,
)


def _is_incomplete(text: str) -> bool:
    """
    Return True if the generated text appears to be cut off mid-response.
    Checks both the tail of the text and common truncation signals.
    """
    if not text or not text.strip():
        return True

    tail = text.rstrip()[-120:]  # examine last 120 chars only

    # Explicit truncation signals
    if _INCOMPLETE_PATTERNS.search(tail):
        return True

    # Does NOT end with a proper sentence-ending mark?
    if not _COMPLETE_END.search(tail):
        return True

    # Unbalanced markdown: open bold/italic/code markers
    if tail.count('**') % 2 != 0:
        return True
    if tail.count('`') % 2 != 0:
        return True

    return False


# ---------------------------------------------------------------------------
# Continuation helper (sync)
# ---------------------------------------------------------------------------

def _continue_generation(
    partial_text: str,
    user_message: str,
    flower_name: str,
    context_docs: list[str],
    history: list[dict],
    max_tokens: int,
) -> str:
    """
    Given a truncated partial_text, ask the model to continue from exactly
    where it stopped, then stitch the continuation onto the original text.
    """
    import torch

    # Build a continuation prompt: show the assistant's partial answer and
    # ask it to continue naturally without repeating what was already said.
    continuation_messages = [
        {
            "role": "system",
            "content": (
                SYSTEM_PROMPT
                + "\n\nYou are continuing an answer that was cut off. "
                "Output ONLY the continuation — do NOT repeat anything already written. "
                "Pick up from the exact point where the text ends and finish the response completely."
            ),
        },
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": partial_text},
        {
            "role": "user",
            "content": (
                "Your previous response was cut off. Continue from exactly where you stopped, "
                "completing all unfinished sentences, bullet points, and sections. "
                "Do not repeat anything already written."
            ),
        },
    ]

    prompt = _tokenizer.apply_chat_template(
        continuation_messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)

    with torch.inference_mode():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=max(PHI_TEMPERATURE, 0.3),  # slight warmth for fluency
            top_p=PHI_TOP_P,
            repetition_penalty=1.15,
            do_sample=True,
            pad_token_id=_tokenizer.pad_token_id,
            use_cache=True,
        )

    prompt_len = inputs["input_ids"].shape[1]
    continuation = _tokenizer.decode(
        outputs[0][prompt_len:], skip_special_tokens=True
    ).strip()

    # Stitch: preserve original text, add a space before continuation if needed
    joined = partial_text.rstrip()
    if continuation and not joined.endswith(' '):
        joined += ' '
    return joined + continuation


# ---------------------------------------------------------------------------
# Main sync transformer generation (with continuation loop)
# ---------------------------------------------------------------------------

def _generate_transformers(
    user_message: str,
    flower_name: str,
    context_docs: list[str],
    history: list[dict],
    max_tokens: int = PHI_MAX_TOKENS,
) -> str:
    import torch

    messages = _build_messages(user_message, flower_name, context_docs, history)

    prompt = _tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)
    prompt_tokens = inputs["input_ids"].shape[1]

    use_sampling = PHI_TEMPERATURE > 0.35
    gen_kwargs = dict(
        **inputs,
        max_new_tokens=max_tokens,
        repetition_penalty=1.05,
        do_sample=use_sampling,
        pad_token_id=_tokenizer.pad_token_id,
        eos_token_id=_tokenizer.eos_token_id,
        use_cache=True,
    )
    if use_sampling:
        gen_kwargs["temperature"] = PHI_TEMPERATURE
        gen_kwargs["top_p"] = PHI_TOP_P

    t0 = time.perf_counter()
    with torch.inference_mode():
        outputs = _model.generate(**gen_kwargs)
    gen_time = time.perf_counter() - t0

    generated_ids = outputs[0][prompt_tokens:]
    content = _tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    completion_tokens = len(generated_ids)
    total_tokens = prompt_tokens + completion_tokens
    finish_reason = "length" if completion_tokens >= max_tokens else "stop"

    logger.info(
        "=== LLM Generation Metrics ===\n"
        "  Active Backend   : %s\n"
        "  Loaded Model     : %s\n"
        "  Finish Reason    : %s\n"
        "  Prompt Tokens    : %d\n"
        "  Completion Tokens: %d\n"
        "  Total Token Usage: %d\n"
        "  Generation Time  : %.3f s\n"
        "==============================",
        _backend,
        PHI_HF_MODEL,
        finish_reason,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        gen_time,
    )

    # ── Continuation loop ─────────────────────────────────────────────────
    # If the model hit the token limit AND the response looks incomplete,
    # keep asking it to continue until the answer is finished (max 3 passes).
    MAX_CONTINUATION_PASSES = 3
    CONTINUATION_TOKENS = max(512, max_tokens // 2)

    for pass_num in range(1, MAX_CONTINUATION_PASSES + 1):
        if finish_reason != "length" or not _is_incomplete(content):
            break  # response is naturally complete — done

        logger.info(
            "Response appears incomplete (pass %d/%d). Continuing generation…",
            pass_num,
            MAX_CONTINUATION_PASSES,
        )
        content = _continue_generation(
            partial_text=content,
            user_message=user_message,
            flower_name=flower_name,
            context_docs=context_docs,
            history=history,
            max_tokens=CONTINUATION_TOKENS,
        )
        # Re-evaluate finish condition for the merged content
        finish_reason = "stop" if not _is_incomplete(content) else "length"

    return _enforce_user_formatting(content, user_message)


async def generate_async(
    user_message: str,
    flower_name: str = "",
    context_docs: list[str] = None,
    history: list[dict] = None,
    max_tokens: int | None = None,
) -> str:
    """
    Async wrapper around `generate` that uses the module ThreadPoolExecutor.
    This keeps FastAPI's event loop responsive while the blocking LLM code runs
    in a bounded pool of worker threads.
    """
    fast = _fast_answer_from_knowledge(user_message, flower_name, context_docs or [])
    if fast:
        return fast

    get_llm()

    loop = asyncio.get_event_loop()

    return await loop.run_in_executor(
        _executor,
        generate,
        user_message,
        flower_name,
        context_docs or [],
        history or [],
        max_tokens,
    )


import queue
from transformers.generation.streamers import BaseStreamer

class FastTokenStreamer(BaseStreamer):
    """
    High-performance token streamer that decodes tokens immediately and
    explicitly releases the Python GIL (Global Interpreter Lock) via time.sleep(0.0001)
    on every token, ensuring real-time token streaming to FastAPI without thread locking.
    """
    def __init__(self, tokenizer, skip_prompt: bool = True, timeout: float = 60.0):
        self.tokenizer = tokenizer
        self.skip_prompt = skip_prompt
        self.timeout = timeout
        self.token_queue = queue.Queue()
        self.stop_signal = object()
        self.next_tokens_are_prompt = True

    def put(self, value):
        if hasattr(value, "shape") and len(value.shape) > 1:
            value = value[0]

        if self.skip_prompt and self.next_tokens_are_prompt:
            self.next_tokens_are_prompt = False
            return

        tok_id = value.tolist() if hasattr(value, "tolist") else list(value)
        text = self.tokenizer.decode(tok_id, skip_special_tokens=True)
        if text:
            self.token_queue.put(text)
            time.sleep(0.0001)  # Release Python GIL immediately to consumer thread!

    def end(self):
        self.token_queue.put(self.stop_signal)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            value = self.token_queue.get(timeout=self.timeout)
        except queue.Empty:
            raise StopIteration
        if value is self.stop_signal:
            raise StopIteration
        return value


_RESPONSE_CACHE: dict[str, str] = {}
_MAX_CACHE_ENTRIES: int = 200

def generate_stream(
    user_message: str,
    flower_name: str = "",
    context_docs: list[str] = None,
    history: list[dict] = None,
    max_tokens: int | None = None,
):
    """
    Synchronous generator that yields output tokens one by one in real-time
    using Hugging Face TextIteratorStreamer.
    """
    get_llm()

    cache_key = f"{user_message.strip().lower()}|{flower_name.strip().lower()}"

    # 1. Fast answer / pleasantry check
    context_docs = context_docs or []
    history = history or []
    fast = _fast_answer_from_knowledge(user_message, flower_name, context_docs)
    if fast:
        words = fast.split(" ")
        for idx, word in enumerate(words):
            yield word if idx == len(words) - 1 else word + " "
            time.sleep(0.005)
        return

    # 2. Check repeat-question cache for zero-latency response replay
    if cache_key in _RESPONSE_CACHE:
        cached_answer = _RESPONSE_CACHE[cache_key]
        words = cached_answer.split(" ")
        for idx, word in enumerate(words):
            yield word if idx == len(words) - 1 else word + " "
            time.sleep(0.008)
        return

    parsed = _parse_request_constraints(user_message)
    if max_tokens:
        tokens_limit = max_tokens
    elif parsed.get('type') == 'lines' or (parsed.get('count') and parsed['count'] <= 2):
        tokens_limit = min(PHI_MAX_TOKENS, 120)
    elif parsed.get('type') == 'table':
        tokens_limit = min(PHI_MAX_TOKENS, 220)
    else:
        tokens_limit = min(PHI_MAX_TOKENS, 280)

    from transformers import TextIteratorStreamer
    from threading import Thread

    messages = _build_messages(user_message, flower_name, context_docs, history)

    prompt = _tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)

    from queue import Empty

    streamer = TextIteratorStreamer(
        _tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
        timeout=120.0,
    )

    use_sampling = PHI_TEMPERATURE > 0.35
    gen_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=tokens_limit,
        repetition_penalty=1.1,
        do_sample=use_sampling,
        pad_token_id=_tokenizer.pad_token_id,
        eos_token_id=_tokenizer.eos_token_id,
        use_cache=True,
    )
    if use_sampling:
        gen_kwargs["temperature"] = PHI_TEMPERATURE
        gen_kwargs["top_p"] = PHI_TOP_P

    def _worker():
        import torch
        num_threads = max(1, min(4, (os.cpu_count() or 4) - 1 if (os.cpu_count() or 4) > 2 else 2))
        torch.set_num_threads(num_threads)
        with torch.inference_mode():
            _model.generate(**gen_kwargs)

    thread = Thread(target=_worker, daemon=True)
    thread.start()

    collected_tokens = []
    try:
        for token in streamer:
            if token:
                collected_tokens.append(token)
                yield token
    except Empty:
        logger.warning("TextIteratorStreamer timeout after 120s; returning collected tokens.")

    thread.join(timeout=120)

    # Cache response for identical queries
    if collected_tokens:
        full_raw = "".join(collected_tokens)
        cleaned_ans = _enforce_user_formatting(full_raw, user_message)
        if cleaned_ans:
            if len(_RESPONSE_CACHE) >= _MAX_CACHE_ENTRIES:
                _RESPONSE_CACHE.pop(next(iter(_RESPONSE_CACHE)))
            _RESPONSE_CACHE[cache_key] = cleaned_ans


async def generate_stream_async(
    user_message: str,
    flower_name: str = "",
    context_docs: list[str] = None,
    history: list[dict] = None,
    max_tokens: int | None = None,
):
    """
    Asynchronous generator yielding tokens in real-time over an asyncio.Queue,
    running the token-generator thread safely inside worker threads.
    """
    get_llm()

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    _SENTINEL = object()

    def _producer():
        try:
            for token in generate_stream(
                user_message=user_message,
                flower_name=flower_name,
                context_docs=context_docs or [],
                history=history or [],
                max_tokens=max_tokens,
            ):
                loop.call_soon_threadsafe(queue.put_nowait, token)
        except Exception as exc:
            logger.error("Error in streaming generator producer thread: %s", exc)
            loop.call_soon_threadsafe(queue.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _SENTINEL)

    _executor.submit(_producer)

    while True:
        item = await queue.get()
        if item is _SENTINEL:
            break
        if isinstance(item, Exception):
            raise item
        yield item


def unload() -> None:
    """Explicitly release LLM and pipeline resources during app shutdown or reload."""
    global _model, _tokenizer, _executor, _backend
    logger.info("Unloading chatbot module resources (active backend was: %s)...", _backend or "none")
    _model = None
    _tokenizer = None

    if _executor is not None:
        try:
            _executor.shutdown(wait=False)
        except Exception:
            pass
        _executor = None

    _backend = ""
    logger.info("Chatbot resources successfully unloaded.")


atexit.register(unload)
