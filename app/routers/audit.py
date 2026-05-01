import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from openpyxl import Workbook
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
from ..services.exporting import EXPORT_MAX_ROWS, UTF8_BOM, auto_fit_columns, style_header_row
from ..services.pagination import build_pagination
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
    pagination = build_pagination(total_events, page, per_page)

    events = (
        query
        .order_by(desc(models.AuditEvent.created_at), desc(models.AuditEvent.id))
        .offset(pagination.offset)
        .limit(pagination.per_page)
        .all()
    )

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
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.total_pages,
            "first_item": pagination.first_item,
            "last_item": min(pagination.offset + len(events), total_events),
            "has_previous_page": pagination.has_previous_page,
            "has_next_page": pagination.has_next_page,
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
    query = build_audit_query(db, event_type, username, start_date, end_date)
    total_rows = query.count()
    events = (
        query
        .order_by(desc(models.AuditEvent.created_at), desc(models.AuditEvent.id))
        .limit(EXPORT_MAX_ROWS)
        .all()
    )

    output = io.StringIO()
    output.write(UTF8_BOM)
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
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": "attachment; filename=auditoria.csv",
            "X-Export-Row-Limit": str(EXPORT_MAX_ROWS),
            "X-Export-Truncated": str(total_rows > EXPORT_MAX_ROWS).lower(),
        },
    )


@router.get("/audit/export/xlsx")
def export_audit_xlsx(
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
    query = build_audit_query(db, event_type, username, start_date, end_date)
    total_rows = query.count()
    events = (
        query
        .order_by(desc(models.AuditEvent.created_at), desc(models.AuditEvent.id))
        .limit(EXPORT_MAX_ROWS)
        .all()
    )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Auditoria"
    headers = ["Data", "Tipo", "Usuario", "IP", "Detalhes"]
    sheet.append(headers)
    style_header_row(sheet)

    for event in events:
        sheet.append([
            format_datetime(event.created_at),
            event.event_type,
            event.username or "",
            event.ip_address or "",
            event.details_json or "{}",
        ])

    auto_fit_columns(sheet, max_width=60)

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=auditoria.xlsx",
            "X-Export-Row-Limit": str(EXPORT_MAX_ROWS),
            "X-Export-Truncated": str(total_rows > EXPORT_MAX_ROWS).lower(),
        },
    )
