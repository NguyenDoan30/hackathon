import json
from pydantic import ValidationError, TypeAdapter
from ..errors import ApiError
from ..schemas import CardResult, QuestionResult

def provider_output(schema, result):
    try:
        return schema.model_validate(result).model_dump()
    except (ValidationError, TypeError, ValueError):
        raise ApiError(502, 'PROVIDER_INVALID_OUTPUT', 'Module trả dữ liệu không đúng đặc tả.') from None

def list_output(model, result):
    try:
        items = TypeAdapter(list[model]).validate_python(result)
        if not 1 <= len(items) <= 50:
            raise ValueError('Provider list must contain 1..50 items')
        return [item.model_dump() for item in items]
    except (ValidationError, TypeError, ValueError):
        raise ApiError(502, 'PROVIDER_INVALID_OUTPUT', 'Module trả danh sách không đúng đặc tả.') from None

def documents_context(conn, lesson_id):
    rows = conn.execute("SELECT id,filename,content FROM documents WHERE lesson_id=? AND status='ready' ORDER BY created_at,id", (lesson_id,)).fetchall()
    if not rows:
        raise ApiError(409, 'CONTEXT_NOT_READY', 'Cần ít nhất một tài liệu đã xử lý để thực hiện chức năng này.')
    return [dict(row) for row in rows]

def public_document(row):
    fields = ('id','lesson_id','filename','media_type','size_bytes','status','content','error_code','source_mode','created_at','updated_at')
    return {k: row[k] for k in fields}

def public_quiz(row):
    quiz = dict(row)
    # Answers and explanations only leave the server after a submitted attempt.
    quiz['questions'] = [{k:q[k] for k in ('id','question','options')} for q in json.loads(quiz['questions'])]
    return quiz

def validate_quiz(questions):
    ids = [q['id'] for q in questions]
    if len(ids) != len(set(ids)) or any(q['answer'] not in q['options'] or len(q['options']) != len(set(q['options'])) for q in questions):
        raise ApiError(502, 'PROVIDER_INVALID_OUTPUT', 'Quiz cần ID duy nhất và đáp án thuộc danh sách lựa chọn.')

def progress(conn, user_id, lesson_id=None):
    params = [user_id]
    scope = ' AND q.lesson_id=?' if lesson_id else ''
    if lesson_id:
        params.append(lesson_id)
    row = conn.execute('SELECT COUNT(*) attempts, COALESCE(AVG(a.score),0) average_score, COALESCE(MAX(a.score),0) best_score, COALESCE(SUM(a.correct),0) correct_answers, COALESCE(SUM(a.total),0) answered_questions FROM quiz_attempts a JOIN quizzes q ON q.id=a.quiz_id WHERE a.user_id=?'+scope, params).fetchone()
    result = dict(row)
    result['average_score'] = round(result['average_score'], 2)
    result['recent_attempts'] = [dict(x) for x in conn.execute('SELECT a.id,a.quiz_id,q.lesson_id,a.correct,a.total,a.score,a.source_mode,a.created_at FROM quiz_attempts a JOIN quizzes q ON q.id=a.quiz_id WHERE a.user_id=?'+scope+' ORDER BY a.created_at DESC,a.id DESC LIMIT 10', params)]
    count_scope = ' AND l.id=?' if lesson_id else ''
    result['flashcard_reviews'] = conn.execute('SELECT COUNT(*) FROM flashcard_reviews r JOIN flashcards f ON f.id=r.flashcard_id JOIN lessons l ON l.id=f.lesson_id WHERE r.user_id=?'+count_scope, params).fetchone()[0]
    return result
