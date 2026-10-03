import json
from fastapi import APIRouter,Depends,Request,Query
from ..security import current_user,db_session,owned_lesson,uid,now
from ..schemas import ChatInput,Review,QuizSubmit,SummaryResult,AnswerResult,CardResult,QuestionResult,GradeResult
from ..services.content import provider_output,list_output,documents_context,public_quiz,validate_quiz
from ..errors import ApiError
from ..models import SummaryPublic,ChatPublic,ChatPage,CardPage,ReviewPublic,QuizPublic,AttemptPublic

router=APIRouter(tags=['04 · AI & học tập'])

@router.post('/summary/{lesson_id}/generate',response_model=SummaryPublic,summary='Gọi module AI và lưu tóm tắt')
def generate_summary(lesson_id:str,request:Request,user=Depends(current_user),conn=Depends(db_session)):
    owned_lesson(conn,lesson_id,user['id'])
    context=documents_context(conn,lesson_id)
    result=provider_output(SummaryResult,request.app.state.providers.call('ai','summarize',context))
    conn.execute('INSERT INTO summaries VALUES (?,?,?,?,?) ON CONFLICT(lesson_id) DO UPDATE SET summary=excluded.summary,key_points=excluded.key_points,source_mode=excluded.source_mode,updated_at=excluded.updated_at',(lesson_id,result['summary'],json.dumps(result['key_points'],ensure_ascii=False),request.app.state.providers.mode,now()))
    return get_summary(lesson_id,user,conn)

@router.get('/summary/{lesson_id}',response_model=SummaryPublic,summary='Đọc tóm tắt đã lưu')
def get_summary(lesson_id:str,user=Depends(current_user),conn=Depends(db_session)):
    owned_lesson(conn,lesson_id,user['id'])
    row=conn.execute('SELECT * FROM summaries WHERE lesson_id=?',(lesson_id,)).fetchone()
    if not row:
        raise ApiError(404,'SUMMARY_NOT_FOUND','Bài học chưa có tóm tắt.')
    result=dict(row)
    result['key_points']=json.loads(result['key_points'])
    return result

@router.post('/chat',status_code=201,response_model=ChatPublic,summary='Gọi AI Tutor và lưu hội thoại')
def chat(body:ChatInput,request:Request,user=Depends(current_user),conn=Depends(db_session)):
    owned_lesson(conn,body.lesson_id,user['id'])
    context=documents_context(conn,body.lesson_id)
    history=[dict(r) for r in conn.execute('SELECT question,answer FROM chats WHERE lesson_id=? ORDER BY created_at DESC,id DESC LIMIT 12',(body.lesson_id,))][::-1]
    result=provider_output(AnswerResult,request.app.state.providers.call('ai','chat',body.question,context,history))
    if not set(result['sources']).issubset({d['id'] for d in context}):
        raise ApiError(502,'PROVIDER_INVALID_OUTPUT','Nguồn trả lời phải thuộc tài liệu của bài học.')
    chat_id=uid()
    conn.execute('INSERT INTO chats VALUES (?,?,?,?,?,?,?)',(chat_id,body.lesson_id,body.question,result['answer'],json.dumps(result['sources']),request.app.state.providers.mode,now()))
    row=dict(conn.execute('SELECT * FROM chats WHERE id=?',(chat_id,)).fetchone())
    row['sources']=result['sources']
    return row

@router.get('/chat/{lesson_id}',response_model=ChatPage,summary='Lịch sử hội thoại theo bài học')
def history(lesson_id:str,limit:int=Query(default=50,ge=1,le=100),offset:int=Query(default=0,ge=0),user=Depends(current_user),conn=Depends(db_session)):
    owned_lesson(conn,lesson_id,user['id'])
    rows=[]
    for r in conn.execute('SELECT * FROM chats WHERE lesson_id=? ORDER BY created_at,id LIMIT ? OFFSET ?',(lesson_id,limit,offset)):
        item=dict(r)
        item['sources']=json.loads(item['sources'])
        rows.append(item)
    total=conn.execute('SELECT COUNT(*) FROM chats WHERE lesson_id=?',(lesson_id,)).fetchone()[0]
    return {'items':rows,'total':total,'limit':limit,'offset':offset}

@router.post('/flashcards/{lesson_id}/generate',status_code=201,response_model=CardPage,summary='Gọi module learning và thay thế bộ thẻ hiện tại')
def generate_cards(lesson_id:str,request:Request,user=Depends(current_user),conn=Depends(db_session)):
    owned_lesson(conn,lesson_id,user['id'])
    context=documents_context(conn,lesson_id)
    result=list_output(CardResult,request.app.state.providers.call('learning','flashcards',context))
    # Replace the active deck atomically; its old review records cascade.
    conn.execute('DELETE FROM flashcards WHERE lesson_id=?',(lesson_id,))
    for item in result:
        conn.execute('INSERT INTO flashcards VALUES (?,?,?,?,?,?,?)',(uid(),lesson_id,item['question'],item['answer'],item['difficulty'],request.app.state.providers.mode,now()))
    return cards(lesson_id,user,conn)

@router.get('/flashcards/{lesson_id}',response_model=CardPage,summary='Đọc bộ flashcard đã lưu')
def cards(lesson_id:str,user=Depends(current_user),conn=Depends(db_session)):
    owned_lesson(conn,lesson_id,user['id'])
    return {'items':[dict(r) for r in conn.execute('SELECT * FROM flashcards WHERE lesson_id=? ORDER BY created_at,id',(lesson_id,))]}

@router.post('/flashcards/{flashcard_id}/review',status_code=201,response_model=ReviewPublic,summary='Lưu đánh giá độ nhớ một thẻ')
def review(flashcard_id:str,body:Review,user=Depends(current_user),conn=Depends(db_session)):
    row=conn.execute('SELECT f.* FROM flashcards f JOIN lessons l ON l.id=f.lesson_id WHERE f.id=? AND l.user_id=?',(flashcard_id,user['id'])).fetchone()
    if not row:
        raise ApiError(404,'FLASHCARD_NOT_FOUND','Không tìm thấy flashcard.')
    review_id=uid()
    conn.execute('INSERT INTO flashcard_reviews VALUES (?,?,?,?,?)',(review_id,flashcard_id,user['id'],body.rating,now()))
    return dict(conn.execute('SELECT * FROM flashcard_reviews WHERE id=?',(review_id,)).fetchone())

@router.post('/quiz/{lesson_id}/generate',status_code=201,response_model=QuizPublic,summary='Gọi module learning và lưu quiz mới')
def generate_quiz(lesson_id:str,request:Request,user=Depends(current_user),conn=Depends(db_session)):
    owned_lesson(conn,lesson_id,user['id'])
    context=documents_context(conn,lesson_id)
    questions=list_output(QuestionResult,request.app.state.providers.call('learning','quiz',context))
    validate_quiz(questions)
    quiz_id=uid()
    conn.execute('INSERT INTO quizzes VALUES (?,?,?,?,?)',(quiz_id,lesson_id,json.dumps(questions,ensure_ascii=False),request.app.state.providers.mode,now()))
    return public_quiz(conn.execute('SELECT * FROM quizzes WHERE id=?',(quiz_id,)).fetchone())

@router.get('/quiz/{lesson_id}',response_model=QuizPublic,summary='Đọc quiz mới nhất, không trả đáp án')
def quiz(lesson_id:str,user=Depends(current_user),conn=Depends(db_session)):
    owned_lesson(conn,lesson_id,user['id'])
    row=conn.execute('SELECT * FROM quizzes WHERE lesson_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(lesson_id,)).fetchone()
    if not row:
        raise ApiError(404,'QUIZ_NOT_FOUND','Bài học chưa có quiz.')
    return public_quiz(row)

@router.post('/quizzes/{quiz_id}/submit',status_code=201,response_model=AttemptPublic,summary='Gọi module chấm bài và lưu kết quả')
def submit(quiz_id:str,body:QuizSubmit,request:Request,user=Depends(current_user),conn=Depends(db_session)):
    row=conn.execute('SELECT q.* FROM quizzes q JOIN lessons l ON l.id=q.lesson_id WHERE q.id=? AND l.user_id=?',(quiz_id,user['id'])).fetchone()
    if not row:
        raise ApiError(404,'QUIZ_NOT_FOUND','Không tìm thấy quiz.')
    questions=json.loads(row['questions'])
    if set(body.answers)!={q['id'] for q in questions} or any(body.answers[q['id']] not in q['options'] for q in questions):
        raise ApiError(422,'INVALID_ANSWERS','Cần trả lời đủ câu hỏi với lựa chọn hợp lệ.')
    if row['source_mode']!=request.app.state.providers.mode:
        raise ApiError(409,'QUIZ_MODE_MISMATCH','Quiz thuộc chế độ khác; hãy tạo quiz mới.')
    grade=provider_output(GradeResult,request.app.state.providers.call('learning','grade',questions,body.answers))
    if grade['total']!=len(questions) or grade['correct']>grade['total'] or abs(grade['score']-100*grade['correct']/grade['total'])>0.02:
        raise ApiError(502,'PROVIDER_INVALID_OUTPUT','Kết quả chấm bài không nhất quán.')
    attempt_id=uid()
    conn.execute('INSERT INTO quiz_attempts VALUES (?,?,?,?,?,?,?,?,?,?)',(attempt_id,quiz_id,user['id'],json.dumps(body.answers,ensure_ascii=False),grade['correct'],grade['total'],grade['score'],json.dumps(grade['feedback'],ensure_ascii=False),row['source_mode'],now()))
    return {'id':attempt_id,'quiz_id':quiz_id,'lesson_id':row['lesson_id'],**grade,'source_mode':row['source_mode'],'created_at':conn.execute('SELECT created_at FROM quiz_attempts WHERE id=?',(attempt_id,)).fetchone()[0]}
