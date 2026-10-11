import os, secrets, hashlib, hmac
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, Request
from .database import DATA, get_db
from .models import User, LoginSession

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ':' + digest

def verify_password(password, stored):
    salt, digest = stored.split(':')
    check = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(digest, check)

secret = os.getenv('JWT_SECRET')
if not secret:
    if os.getenv('APP_ENV') == 'production':
        raise RuntimeError('JWT_SECRET is required in production')
    path = DATA / 'backend-session-secret'
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48))
    secret = path.read_text().strip()

def issue_session(db, user):
    sid = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    db.add(LoginSession(id=sid, user_id=user.id, expires=expires.isoformat()))
    db.commit()
    return jwt.encode({'sub':user.id, 'sid':sid, 'exp':expires}, secret, algorithm='HS256')

def optional_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get('campus_session')
    authorization = request.headers.get('Authorization', '')
    if authorization.startswith('Bearer '): token = authorization[7:]
    if not token: return None
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        session = db.get(LoginSession, payload['sid'])
        user = db.get(User, payload['sub'])
        if not session or not user or session.user_id != user.id or not user.active or session.expires < utcnow():
            raise ValueError()
        return user
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(401, 'Session expired. Sign in again.')

def current_user(user=Depends(optional_user)):
    if not user: raise HTTPException(401, 'Staff sign-in required')
    return user

def require(user, *roles):
    if user.role not in roles: raise HTTPException(403, 'This action is not permitted for your role')

def uid(prefix=''):
    return prefix + secrets.token_hex(10).upper()

def token_hash(token): return hashlib.sha256(token.encode()).hexdigest()
