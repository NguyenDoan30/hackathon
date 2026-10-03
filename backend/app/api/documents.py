from pathlib import Path
import hashlib
import sqlite3
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, BackgroundTasks, Response
from fastapi.responses import FileResponse
from ..security import current_user,db_session,owned_lesson,uid,now
from ..errors import ApiError
from ..services.content import public_document
from ..services.processing import process_document
from ..models import DocumentPublic

router=APIRouter(tags=['03 · Tài liệu'])
TYPES={'.pdf':'application/pdf','.txt':'text/plain','.md':'text/markdown','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.mp3':'audio/mpeg','.wav':'audio/wav','.m4a':'audio/mp4','.ogg':'audio/ogg'}

def owned_document(conn,document_id,user_id):
    row=conn.execute('SELECT d.* FROM documents d JOIN lessons l ON l.id=d.lesson_id WHERE d.id=? AND l.user_id=?',(document_id,user_id)).fetchone()
    if not row:
        raise ApiError(404,'DOCUMENT_NOT_FOUND','Không tìm thấy tài liệu.')
    return dict(row)

def verify_signature(data,ext):
    checks={'.pdf':data.startswith(b'%PDF-'),'.png':data.startswith(b'\x89PNG\r\n\x1a\n'),'.jpg':data.startswith(b'\xff\xd8\xff'),'.jpeg':data.startswith(b'\xff\xd8\xff'),'.webp':data.startswith(b'RIFF') and data[8:12]==b'WEBP', '.wav':data.startswith(b'RIFF') and data[8:12]==b'WAVE', '.ogg':data.startswith(b'OggS'),'.m4a':len(data)>12 and data[4:8]==b'ftyp', '.mp3':data.startswith(b'ID3') or (len(data)>1 and data[0]==255 and data[1]&224==224)}
    if ext in ('.md','.txt'):
        try:
            if b'\x00' in data:
                return False
            return bool(data.decode('utf-8-sig').strip())
        except UnicodeDecodeError:
            return False
    return checks.get(ext,False)

@router.post('/upload',status_code=202,response_model=DocumentPublic,summary='Nhận file và xếp xử lý nền')
def upload(request:Request,background:BackgroundTasks,lesson_id:str=Form(...),file:UploadFile=File(...),user=Depends(current_user),conn=Depends(db_session)):
    owned_lesson(conn,lesson_id,user['id'])
    filename=(file.filename or '').replace('\\','/').split('/')[-1]
    if not filename or len(filename)>240 or any(ord(c)<32 for c in filename):
        raise ApiError(422,'INVALID_FILENAME','Tên file không hợp lệ.')
    ext=Path(filename).suffix.lower()
    if ext not in TYPES:
        raise ApiError(415,'UNSUPPORTED_FILE','Định dạng file chưa được hỗ trợ.')
    max_size=request.app.state.settings.max_upload_mb*1024*1024
    document_id=uid()
    storage_name=document_id+ext
    target=request.app.state.db.uploads/storage_name
    size=0
    sha=hashlib.sha256()
    signature=bytearray()
    try:
        with target.open('xb') as output:
            while chunk:=file.file.read(65536):
                size+=len(chunk)
                if size>max_size:
                    raise ApiError(413,'FILE_TOO_LARGE',f'File vượt quá {request.app.state.settings.max_upload_mb} MB.')
                output.write(chunk)
                sha.update(chunk)
                if len(signature)<64:
                    signature.extend(chunk[:64-len(signature)])
        if size==0:
            raise ApiError(422,'EMPTY_FILE','File không có nội dung.')
        # Text validation is bounded by the upload limit; no PDF/OCR extraction here.
        inspection=target.read_bytes() if ext in ('.txt','.md') else bytes(signature)
        if not verify_signature(inspection,ext):
            raise ApiError(415,'FILE_CONTENT_MISMATCH','Nội dung không khớp định dạng hoặc text không phải UTF-8.')
        existing=conn.execute('SELECT * FROM documents WHERE lesson_id=? AND sha256=?',(lesson_id,sha.hexdigest())).fetchone()
        if existing:
            raise ApiError(409,'DOCUMENT_EXISTS','Tài liệu này đã có trong bài học.',{'document_id':existing['id']})
        timestamp=now()
        conn.execute('INSERT INTO documents(id,lesson_id,filename,storage_name,media_type,size_bytes,sha256,status,source_mode,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(document_id,lesson_id,filename,storage_name,TYPES[ext],size,sha.hexdigest(),'pending',request.app.state.providers.mode,timestamp,timestamp))
        conn.commit()
    except sqlite3.IntegrityError:
        target.unlink(missing_ok=True)
        raise ApiError(409,'DOCUMENT_EXISTS','Tài liệu đã tồn tại hoặc bài học vừa bị xóa.') from None
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()
    background.add_task(process_document,request.app.state.db,request.app.state.providers,document_id)
    return public_document(conn.execute('SELECT * FROM documents WHERE id=?',(document_id,)).fetchone())

@router.get('/documents/{document_id}',response_model=DocumentPublic,summary='Nội dung và trạng thái xử lý tài liệu')
def document(document_id:str,user=Depends(current_user),conn=Depends(db_session)):
    return public_document(owned_document(conn,document_id,user['id']))

@router.get('/documents/{document_id}/download')
def download(document_id:str,request:Request,user=Depends(current_user),conn=Depends(db_session)):
    row=owned_document(conn,document_id,user['id'])
    path=request.app.state.db.uploads/row['storage_name']
    if not path.is_file():
        raise ApiError(404,'FILE_NOT_FOUND','File lưu trữ không còn tồn tại.')
    return FileResponse(path,filename=row['filename'],media_type=row['media_type'],content_disposition_type='attachment')

@router.post('/documents/{document_id}/retry',status_code=202,response_model=DocumentPublic,summary='Thử lại tài liệu xử lý thất bại')
def retry(document_id:str,request:Request,background:BackgroundTasks,user=Depends(current_user),conn=Depends(db_session)):
    owned_document(conn,document_id,user['id'])
    changed=conn.execute("UPDATE documents SET status='pending',error_code=NULL,updated_at=? WHERE id=? AND status='failed'",(now(),document_id)).rowcount
    if not changed:
        raise ApiError(409,'DOCUMENT_NOT_FAILED','Chỉ thử lại tài liệu xử lý thất bại.')
    conn.commit()
    background.add_task(process_document,request.app.state.db,request.app.state.providers,document_id)
    return public_document(conn.execute('SELECT * FROM documents WHERE id=?',(document_id,)).fetchone())

@router.delete('/documents/{document_id}',status_code=204)
def delete_document(document_id:str,request:Request,user=Depends(current_user),conn=Depends(db_session)):
    row=owned_document(conn,document_id,user['id'])
    conn.execute('DELETE FROM documents WHERE id=?',(document_id,))
    conn.commit()
    (request.app.state.db.uploads/row['storage_name']).unlink(missing_ok=True)
    return Response(status_code=204)
