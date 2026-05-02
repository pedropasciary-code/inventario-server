from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models
from ..auth import hash_password, normalize_username
from ..dependencies import get_admin_session_user, get_csrf_token, get_db, validate_csrf_token
from ..services.audit import record_audit_event
from ..templating import templates

router = APIRouter(prefix="/users")


def _normalize_username(username: str | None) -> str:
    return normalize_username(username)


def _validate_password_fields(password: str, password_confirmation: str):
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    if password != password_confirmation:
        raise ValueError("As senhas informadas nao conferem.")


def _render_users_page(
    request: Request,
    db: Session,
    session_user: str,
    message: str | None = None,
    error: str | None = None,
):
    users = db.query(models.User).order_by(asc(models.User.username)).all()
    return templates.TemplateResponse(
        request,
        "users.html",
        {
            "session_user": session_user,
            "users": users,
            "message": message,
            "error": error,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.get("", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db)):
    session_user = get_admin_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)
    return _render_users_page(request, db, session_user)


@router.post("", response_class=HTMLResponse)
def create_panel_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirmation: str = Form(...),
    is_admin: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)
    session_user = get_admin_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    username = _normalize_username(username)

    try:
        if not username:
            raise ValueError("Usuario nao pode ficar vazio.")
        _validate_password_fields(password, password_confirmation)
        if db.query(models.User).filter(models.User.username == username).first():
            raise ValueError("Usuario ja existe.")
        user = models.User(
            username=username,
            password_hash=hash_password(password),
            is_active=True,
            is_admin=is_admin == "on",
        )
        db.add(user)
        db.commit()
    except ValueError as error:
        db.rollback()
        return _render_users_page(request, db, session_user, error=str(error))
    except IntegrityError:
        db.rollback()
        return _render_users_page(request, db, session_user, error="Usuario ja existe.")

    record_audit_event(
        db,
        "user_created",
        request,
        username=session_user,
        details={"target_username": username, "is_admin": user.is_admin},
    )
    return _render_users_page(request, db, session_user, message="Usuario criado com sucesso.")


@router.post("/{user_id}/toggle", response_class=HTMLResponse)
def toggle_panel_user(
    user_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)
    session_user = get_admin_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    if user.username == session_user and user.is_active:
        return _render_users_page(
            request,
            db,
            session_user,
            error="Voce nao pode desativar o proprio usuario logado.",
        )

    user.is_active = not user.is_active
    db.commit()

    event_type = "user_enabled" if user.is_active else "user_disabled"
    record_audit_event(
        db, event_type, request,
        username=session_user,
        details={"target_username": user.username},
    )
    message = "Usuario ativado com sucesso." if user.is_active else "Usuario desativado com sucesso."
    return _render_users_page(request, db, session_user, message=message)


@router.post("/{user_id}/password", response_class=HTMLResponse)
def change_panel_user_password(
    user_id: int,
    request: Request,
    password: str = Form(...),
    password_confirmation: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)
    session_user = get_admin_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    try:
        _validate_password_fields(password, password_confirmation)
    except ValueError as error:
        return _render_users_page(request, db, session_user, error=str(error))

    user.password_hash = hash_password(password)
    db.commit()
    record_audit_event(
        db,
        "password_changed",
        request,
        username=session_user,
        details={"target_username": user.username},
    )
    return _render_users_page(request, db, session_user, message="Senha alterada com sucesso.")


@router.post("/{user_id}/admin", response_class=HTMLResponse)
def toggle_panel_user_admin(
    user_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)
    session_user = get_admin_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    if user.username == session_user and user.is_admin:
        return _render_users_page(
            request,
            db,
            session_user,
            error="Voce nao pode remover o proprio acesso admin.",
        )

    user.is_admin = not user.is_admin
    db.commit()

    event_type = "user_promoted" if user.is_admin else "user_demoted"
    record_audit_event(
        db, event_type, request,
        username=session_user,
        details={"target_username": user.username},
    )
    message = "Usuario promovido a admin." if user.is_admin else "Usuario rebaixado para comum."
    return _render_users_page(request, db, session_user, message=message)
