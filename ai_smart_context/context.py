import json
from .retrieval import normalize


def is_followup(question):
    q = normalize(question).strip()
    return any(phrase in q for phrase in ('de hieu hon', 'don gian hon', 'chi tiet hon',
               'vi du', 'giai thich lai', 'tai sao vay', 'no la gi', 'dieu do', 'phan do'))


def history_context(history, lesson_id, budget):
    turns = [t for t in history if t.lesson_id == lesson_id]
    # Keep recent turns and extract old user topics; do not treat old AI answers as facts.
    recent = []
    available = budget * 3 // 4
    for turn in reversed(turns[-6:]):
        item = {'role': turn.role, 'content': turn.content[:available]}
        cost = len(json.dumps(item, ensure_ascii=False))
        if cost > available:
            break
        recent.insert(0, item)
        available -= cost
    topics = [t.content[:160] for t in turns[:-6] if t.role == 'user'][-5:]
    value = {'recent_turns': recent, 'older_user_topics': topics}
    while len(json.dumps(value, ensure_ascii=False)) > budget and topics:
        topics.pop(0)
    return value, turns


def select_context(ranked, budget):
    selected = []
    total = 2  # JSON list delimiters
    for chunk, score in ranked:
        item = {'id': chunk.id, 'title': chunk.title, 'text': chunk.text,
                'start_seconds': chunk.start_seconds, 'end_seconds': chunk.end_seconds}
        cost = len(json.dumps(item, ensure_ascii=False)) + (2 if selected else 0)
        if total + cost <= budget:
            selected.append((chunk, score))
            total += cost
    return selected


def context_items(selected):
    return [{'id': c.id, 'title': c.title, 'text': c.text,
             'start_seconds': c.start_seconds, 'end_seconds': c.end_seconds} for c, _ in selected]
