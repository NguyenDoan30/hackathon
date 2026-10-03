import re
import unicodedata

from .schemas import LearningSettings, normalize_documents

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_SPACE = re.compile(r"\s+")


def clean_text(value: str) -> str:
    return _SPACE.sub(" ", value).strip()


def ascii_key(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower())
    return "".join(ch for ch in value if unicodedata.category(ch) != "Mn")


def sentence_candidates(documents: list[dict], settings: LearningSettings) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for doc in normalize_documents(documents):
        for sentence in _SENTENCE_SPLIT.split(doc["content"]):
            text = clean_text(sentence)
            if not settings.min_sentence_length <= len(text) <= settings.max_sentence_length:
                continue
            key = ascii_key(text)
            if key in seen:
                continue
            seen.add(key)
            result.append({
                "document_id": doc["id"],
                "title": doc["title"],
                "text": text,
            })
    return result


def term_from_sentence(sentence: str) -> str:
    left = re.split(r"\s+(?:là|la|is|are|means|gồm|gom|bao gồm|bao gom)\s+", sentence, maxsplit=1, flags=re.I)
    if len(left) == 2:
        candidate = left[0].strip(" :;,.-")
        if 2 <= len(candidate.split()) <= 10:
            return candidate
    words = re.findall(r"[\wÀ-ỹ]+", sentence, flags=re.UNICODE)
    return " ".join(words[: min(7, len(words))])
