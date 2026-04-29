import csv
import io
import math

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import models
from ..dependencies import get_admin_session_user, get_csrf_token, get_db
from ..formatting import format_datetime
from ..services.asset import DASHBOARD_DEFAULT_PAGE_SIZE, DASHBOARD_PAGE_SIZE_OPTIONS, clamp_page_size
from ..services.audit import (
    AUDIT_EVENT_OPTIONS,
    build_audit_query,
    normalize_audit_event_type,
    parse_date_filter,
)
from ..templating import templates

router = APIRouter()


@router.get("/audit", response_class=HTMLResponse)
def audit_events(
    request: Request,
    event_type: str = "all",
    username: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    per_page: int = DASHBOARD_DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db),
):
    session_user = get_admin_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    event_type = normalize_audit_event_type(event_type)
    start_date = parse_date_filter(date_from)
    end_date = parse_date_filter(date_to)
    query = build_audit_query(db, event_type, username, start_date, end_date)
    total_events = query.count()

    per_page = clamp_page_size(per_page)
    total_pages = max(math.ceil(total_events / per_page), 1)
    page = min(max(page, 1), total_pages)
    offset = (page - 1) * per_page

    events = (
        query
        .order_by(desc(models.AuditEvent.created_at), desc(models.AuditEvent.id))
        .offset(offset)
        .limit(per_page)
        .all()
    )

    first_item = offset + 1 if total_events else 0
    last_item = min(offset + len(events), total_events)

    return templates.TemplateResponse(
        request,
        "audit.html",
        {
            "session_user": session_user,
            "events": events,
            "event_type": event_type,
            "event_options": AUDIT_EVENT_OPTIONS,
            "username": username,
            "date_from": date_from,
            "date_to": date_to,
            "page_size_options": DASHBOARD_PAGE_SIZE_OPTIONS,
            "total_events": total_events,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "first_item": first_item,
            "last_item": last_item,
            "has_previous_page": page > 1,
            "has_next_page": page < total_pages,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.get("/audit/export/csv")
def export_audit_csv(
    request: Request,
    event_type: str = "all",
    username: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
):
    session_user = get_admin_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    event_type = normalize_audit_event_type(event_type)
    start_date = parse_date_filter(date_from)
    end_date = parse_date_filter(date_to)
    events = (
        build_audit_query(db, event_type, username, start_date, end_date)
        .order_by(desc(models.AuditEvent.created_at), desc(models.AuditEvent.id))
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data", "Tipo", "Usuario", "IP", "Detalhes"])

    for event in events:
        writer.writerow([
            format_datetime(event.created_at),
            event.event_type,
            event.username or "",
            event.ip_address or "",
            event.details_json or "{}",
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=auditoria.csv"},
    )
