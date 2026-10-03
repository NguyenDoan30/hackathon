"""Vietnamese accent-insensitive lexical retrieval; no embedding/vector DB required."""
import hashlib
import math
import re
import unicodedata
from collections import Counter
from .schemas import Chunk, Source, Settings

STOP = set('la va cua cac nhung mot nhieu trong voi cho ve tai tu co gi nao the nhu hay ban toi minh duoc nay do khong hay hay'.split())


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
                   if unicodedata.category(c) != 'Mn')


def tokens(text):
    return [w for w in re.findall(r'[a-z0-9]+', normalize(text)) if w not in STOP]


def split_text(text, settings):
    text = text.strip()
    pos = 0
    while pos < len(text):
        end = min(pos + settings.chunk_chars, len(text))
        if end < len(text):
            boundary = max(text.rfind('\n', pos + settings.chunk_chars // 2, end),
                           text.rfind(' ', pos + settings.chunk_chars // 2, end))
            if boundary > pos:
                end = boundary
        yield text[pos:end]
        if end == len(text):
            break
        pos = max(pos + 1, end - settings.overlap_chars)


def build_chunks(sources: list[Source], lesson_id: str, settings: Settings):
    if len(sources) > 100:
        raise ValueError('Tối đa 100 nguồn mỗi yêu cầu.')
    chosen = [s for s in sources if s.lesson_id == lesson_id]
    if len({s.id for s in chosen}) != len(chosen):
        raise ValueError('source.id bị trùng trong bài học.')
    if sum(len(s.text) + sum(len(x.text) for x in s.segments) for s in chosen) > 2_000_000:
        raise ValueError('Tổng dữ liệu bài học vượt 2 triệu ký tự.')
    chunks = []
    for source in chosen:
        # Segments are authoritative when supplied. Avoid duplicated transcript text.
        entries = [(s.text, s.start_seconds, s.end_seconds) for s in source.segments] if source.segments else [(source.text, None, None)]
        for entry, start, end in entries:
            for text in split_text(entry, settings):
                index = len(chunks)
                key = hashlib.sha256(f'{lesson_id}\0{source.id}\0{index}\0{text}'.encode()).hexdigest()[:16]
                chunks.append(Chunk(key, source.id, lesson_id, source.title, text, start, end))
    return chunks


def retrieve(chunks, question, top_k):
    query = Counter(tokens(question))
    if not query or not chunks:
        return []
    counts = [Counter(tokens(c.text)) for c in chunks]
    lengths = [sum(c.values()) for c in counts]
    average = max(1, sum(lengths) / len(lengths))
    df = Counter(w for c in counts for w in c)
    scored = []
    for chunk, count, length in zip(chunks, counts, lengths):
        score = 0.0
        for term in query:
            frequency = count[term]
            if frequency:
                idf = math.log(1 + (len(chunks) - df[term] + .5) / (df[term] + .5))
                score += idf * frequency * 2.2 / (frequency + 1.2 * (.25 + .75 * length / average))
        # A single generic overlap in a multiword query is not enough evidence.
        matches = sum(1 for term in query if count[term])
        if score > 0 and matches >= min(2, len(query)):
            scored.append((chunk, score))
    return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]
