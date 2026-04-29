import json
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy.orm import Session

from .. import models
from ..config import DISPLAY_TIMEZONE
from ..formatting import format_datetime, get_client_ip


AUDIT_EVENT_OPTIONS = {
    "all": "Todos",
    "login_success": "Login realizado",
    "login_failed": "Login recusado",
    "logout": "Logout",
    "export_csv": "Exportacao CSV",
    "export_xlsx": "Exportacao Excel",
    "checkin_rejected": "Check-in rejeitado",
    "user_created": "Usuario criado",
    "user_enabled": "Usuario ativado",
    "user_disabled": "Usuario desativado",
    "password_changed": "Senha alterada",
    "user_promoted": "Usuario promovido",
    "user_demoted": "Usuario rebaixado",
}


def record_audit_event(
    db: Session,
    event_type: str,
    request: Request,
    username: str | None = None,
    details: dict | None = None,
):
    event = models.AuditEvent(
        event_type=event_type,
        username=username,
        ip_address=get_client_ip(request),
        details_json=json.dumps(details or {}, ensure_ascii=False, default=str),
    )
    db.add(event)
    db.commit()


def normalize_audit_event_type(event_type: str | None) -> str:
    if event_type in AUDIT_EVENT_OPTIONS:
        return event_type
    return "all"


def parse_date_filter(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return parsed.replace(tzinfo=DISPLAY_TIMEZONE).astimezone(UTC)


def build_audit_query(
    db: Session,
    event_type: str,
    username: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
):
    query = db.query(models.AuditEvent)
    if event_type != "all":
        query = query.filter(models.AuditEvent.event_type == event_type)
    if username:
        query = query.filter(models.AuditEvent.username.ilike(f"%{username}%"))
    if start_date:
        query = query.filter(models.AuditEvent.created_at >= start_date)
    if end_date:
        query = query.filter(models.AuditEvent.created_at < end_date + timedelta(days=1))
    return query
