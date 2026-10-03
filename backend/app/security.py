from datetime import datetime, timezone, timedelta
import hashlib
import secrets
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .errors import ApiError

hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)

def now():
    return datetime.now(timezone.utc).isoformat()

def uid():
    return str(uuid4())

def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def verify_password(encoded, password):
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False

def new_session(conn, user_id, hours):
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    conn.execute('DELETE FROM sessions WHERE expires_at <= ?', (now(),))
    conn.execute('INSERT INTO sessions VALUES (?,?,?,?)', (digest(token), user_id, expires, now()))
    return {'access_token': token, 'token_type': 'bearer', 'expires_at': expires}

def db_session(request: Request):
    with request.app.state.db.session() as conn:
        yield conn

def current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer), conn=Depends(db_session)):
    if not credentials or credentials.scheme.lower() != 'bearer':
        raise ApiError(401, 'AUTH_REQUIRED', 'Vui lòng đăng nhập.')
    row = conn.execute('SELECT u.id,u.name,u.email,u.created_at FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>?', (digest(credentials.credentials), now())).fetchone()
    if not row:
        raise ApiError(401, 'SESSION_INVALID', 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn.')
    return dict(row)

def owned_lesson(conn, lesson_id, user_id):
    row = conn.execute('SELECT * FROM lessons WHERE id=? AND user_id=?', (lesson_id, user_id)).fetchone()
    if not row:
        raise ApiError(404, 'LESSON_NOT_FOUND', 'Không tìm thấy bài học.')
    return dict(row)
