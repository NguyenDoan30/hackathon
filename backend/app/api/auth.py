import sqlite3
from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from ..schemas import Register, Login
from ..security import current_user, db_session, hasher, new_session, uid, now, verify_password, bearer, digest
from ..errors import ApiError
from ..models import SessionPublic,UserPublic

router = APIRouter(prefix='/auth', tags=['01 · Người dùng'])

@router.post('/register', status_code=201,response_model=SessionPublic,summary='Đăng ký và tạo phiên đăng nhập')
def register(body: Register, request: Request, conn=Depends(db_session)):
    user_id = uid()
    try:
        conn.execute('INSERT INTO users VALUES (?,?,?,?,?)', (user_id,body.name,body.email.lower(),hasher.hash(body.password),now()))
    except sqlite3.IntegrityError:
        raise ApiError(409,'EMAIL_EXISTS','Email đã được sử dụng.') from None
    user = dict(conn.execute('SELECT id,name,email,created_at FROM users WHERE id=?',(user_id,)).fetchone())
    return {**new_session(conn,user_id,request.app.state.settings.session_hours),'user':user}

@router.post('/login',response_model=SessionPublic,summary='Đăng nhập bằng email và mật khẩu')
def login(body: Login, request: Request, conn=Depends(db_session)):
    row = conn.execute('SELECT * FROM users WHERE email=?',(body.email.lower(),)).fetchone()
    if not row or not verify_password(row['password_hash'],body.password):
        raise ApiError(401,'LOGIN_FAILED','Email hoặc mật khẩu không đúng.')
    user = {k:row[k] for k in ('id','name','email','created_at')}
    return {**new_session(conn,row['id'],request.app.state.settings.session_hours),'user':user}

@router.get('/me',response_model=UserPublic,summary='Thông tin tài khoản hiện tại')
def me(user=Depends(current_user)):
    return user

@router.post('/logout', status_code=204)
def logout(user=Depends(current_user), credentials: HTTPAuthorizationCredentials=Depends(bearer), conn=Depends(db_session)):
    conn.execute('DELETE FROM sessions WHERE token_hash=?',(digest(credentials.credentials),))
    return Response(status_code=204)
