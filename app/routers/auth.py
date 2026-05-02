import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .. import models
from ..auth import hash_password, normalize_username, password_needs_rehash, verify_password
from ..dependencies import get_csrf_token, get_db, get_session_user, validate_csrf_token
from ..rate_limiting import clear_failed_logins, enforce_login_rate_limit, register_failed_login
from ..services.audit import record_audit_event
from ..templating import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": None, "csrf_token": get_csrf_token(request)},
    )


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)
    username = normalize_username(username)
    enforce_login_rate_limit(request, username)

    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or not user.is_active or not verify_password(password, user.password_hash):
        register_failed_login(request, username)
        record_audit_event(
            db,
            "login_failed",
            request,
            username=username,
            details={"reason": "invalid_credentials"},
        )
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Usuário ou senha inválidos", "csrf_token": get_csrf_token(request)},
            status_code=401,
        )

    clear_failed_logins(request, username)
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    record_audit_event(db, "login_success", request, username=user.username)
    request.session.clear()
    request.session["session_user"] = user.username
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/logout")
def logout(
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)
    session_user = get_session_user(request, db)
    record_audit_event(db, "logout", request, username=session_user)
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
