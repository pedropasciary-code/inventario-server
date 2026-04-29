import hmac
import secrets

from fastapi import Header, HTTPException, Request
from sqlalchemy.orm import Session

from .config import AGENT_TOKEN
from .database import SessionLocal
from . import models


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_agent_token(x_agent_token: str = Header(default=None)):
    if not x_agent_token or not hmac.compare_digest(x_agent_token, AGENT_TOKEN):
        raise HTTPException(status_code=401, detail="Token do agent inválido")


def get_session_user_record(request: Request, db: Session) -> models.User | None:
    username = request.session.get("session_user")
    if not username:
        return None
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not user.is_active:
        request.session.clear()
        return None
    return user


def get_session_user(request: Request, db: Session) -> str | None:
    user = get_session_user_record(request, db)
    if not user:
        return None
    return user.username


def get_admin_session_user(request: Request, db: Session) -> str | None:
    user = get_session_user_record(request, db)
    if not user:
        return None
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user.username


def get_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def validate_csrf_token(request: Request, csrf_token: str | None):
    session_token = request.session.get("csrf_token")
    if (
        not session_token
        or not csrf_token
        or not hmac.compare_digest(session_token, csrf_token)
    ):
        raise HTTPException(status_code=403, detail="Token CSRF inválido")
