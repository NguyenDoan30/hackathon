from fastapi import APIRouter, Depends, Request, Query, Response
from ..security import current_user, db_session, owned_lesson, uid, now
from ..schemas import LessonCreate, LessonUpdate
from ..services.content import public_document, progress
from ..models import LessonPublic,LessonPage,LessonDetail,ProgressPublic

router = APIRouter(tags=['02 · Bài học'])

@router.post('/lessons', status_code=201,response_model=LessonPublic,summary='Tạo bài học')
def create_lesson(body: LessonCreate, user=Depends(current_user), conn=Depends(db_session)):
    lesson_id, timestamp = uid(), now()
    conn.execute('INSERT INTO lessons VALUES (?,?,?,?,?,?)',(lesson_id,user['id'],body.title,body.description,timestamp,timestamp))
    return owned_lesson(conn,lesson_id,user['id'])

@router.get('/lessons',response_model=LessonPage,summary='Danh sách bài học có tìm kiếm và phân trang')
def list_lessons(q: str=Query(default='',max_length=160), limit:int=Query(default=20,ge=1,le=100), offset:int=Query(default=0,ge=0), user=Depends(current_user), conn=Depends(db_session)):
    # instr gives literal matching, without treating user %/_ characters as wildcards.
    params=(user['id'],q)
    total=conn.execute('SELECT COUNT(*) FROM lessons WHERE user_id=? AND instr(lower(title),lower(?))>0',params).fetchone()[0]
    rows=conn.execute("SELECT l.*, (SELECT COUNT(*) FROM documents d WHERE d.lesson_id=l.id) document_count, (SELECT COUNT(*) FROM chats c WHERE c.lesson_id=l.id) chat_count FROM lessons l WHERE user_id=? AND instr(lower(title),lower(?))>0 ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",(*params,limit,offset)).fetchall()
    return {'items':[dict(r) for r in rows],'total':total,'limit':limit,'offset':offset}

@router.get('/lessons/{lesson_id}',response_model=LessonDetail,summary='Chi tiết bài học và tài liệu')
def lesson_detail(lesson_id:str,user=Depends(current_user),conn=Depends(db_session)):
    lesson=owned_lesson(conn,lesson_id,user['id'])
    lesson['documents']=[public_document(r) for r in conn.execute('SELECT * FROM documents WHERE lesson_id=? ORDER BY created_at,id',(lesson_id,))]
    lesson['transcripts']=[dict(r) for r in conn.execute('SELECT id,document_id,content,created_at FROM transcripts WHERE lesson_id=?',(lesson_id,))]
    lesson['progress']=progress(conn,user['id'],lesson_id)
    return lesson

@router.patch('/lessons/{lesson_id}',response_model=LessonPublic,summary='Cập nhật tên và mô tả bài học')
def update_lesson(lesson_id:str,body:LessonUpdate,user=Depends(current_user),conn=Depends(db_session)):
    lesson=owned_lesson(conn,lesson_id,user['id'])
    updates=body.model_dump(exclude_unset=True)
    for field in ('title','description'):
        if field in updates:
            lesson[field]=updates[field]
    conn.execute('UPDATE lessons SET title=?,description=?,updated_at=? WHERE id=?',(lesson['title'],lesson['description'],now(),lesson_id))
    return owned_lesson(conn,lesson_id,user['id'])

@router.delete('/lessons/{lesson_id}',status_code=204)
def delete_lesson(lesson_id:str,request:Request,user=Depends(current_user),conn=Depends(db_session)):
    owned_lesson(conn,lesson_id,user['id'])
    storage=[r['storage_name'] for r in conn.execute('SELECT storage_name FROM documents WHERE lesson_id=?',(lesson_id,))]
    conn.execute('DELETE FROM lessons WHERE id=?',(lesson_id,))
    conn.commit()
    for name in storage:
        (request.app.state.db.uploads/name).unlink(missing_ok=True)
    return Response(status_code=204)

@router.get('/progress',response_model=ProgressPublic,summary='Tiến độ tổng hợp của tài khoản')
def all_progress(user=Depends(current_user),conn=Depends(db_session)):
    return progress(conn,user['id'])

@router.get('/progress/{lesson_id}',response_model=ProgressPublic,summary='Tiến độ của một bài học')
def lesson_progress(lesson_id:str,user=Depends(current_user),conn=Depends(db_session)):
    owned_lesson(conn,lesson_id,user['id'])
    return progress(conn,user['id'],lesson_id)
