from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from .. import models
from ..dependencies import get_csrf_token, get_db, get_session_user, get_session_user_record
from ..formatting import parse_network_interfaces, utc_now
from ..services.asset import (
    ASSET_ONLINE_WINDOW,
    ASSET_SORT_LABELS,
    ASSET_SORT_OPTIONS,
    ASSET_STALE_WINDOW,
    ASSET_STATUS_OPTIONS,
    DASHBOARD_DEFAULT_PAGE_SIZE,
    DASHBOARD_PAGE_SIZE_OPTIONS,
    apply_asset_sort,
    apply_status_filter,
    build_asset_query,
    clamp_page_size,
    next_sort_direction,
    normalize_direction,
    normalize_sort,
    normalize_status_filter,
    prepare_assets_for_display,
)
from ..services.exporting import EXPORT_MAX_ROWS
from ..services.pagination import build_pagination
from ..templating import templates

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    q: str | None = None,
    status: str = "all",
    sort: str = "hostname",
    direction: str = "asc",
    page: int = 1,
    per_page: int = DASHBOARD_DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db),
):
    current_user = get_session_user_record(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    session_user = current_user.username
    status = normalize_status_filter(status)
    sort = normalize_sort(sort)
    direction = normalize_direction(direction)
    base_query = build_asset_query(db, q)
    now = utc_now()
    online_after = now - ASSET_ONLINE_WINDOW
    stale_after = now - ASSET_STALE_WINDOW

    counts = base_query.with_entities(
        func.count(case((models.Asset.ultima_comunicacao >= online_after, 1))).label("communicating"),
        func.count(case((
            (models.Asset.ultima_comunicacao < online_after) &
            (models.Asset.ultima_comunicacao >= stale_after), 1,
        ))).label("stale"),
        func.count(case((
            models.Asset.ultima_comunicacao.is_(None) |
            (models.Asset.ultima_comunicacao < stale_after), 1,
        ))).label("inactive"),
        func.count().label("total_matching"),
    ).one()

    communicating_assets = counts.communicating
    stale_assets = counts.stale
    inactive_assets = counts.inactive
    total_matching_assets = counts.total_matching

    if status == "online":
        total_assets = communicating_assets
    elif status == "stale":
        total_assets = stale_assets
    elif status == "inactive":
        total_assets = inactive_assets
    else:
        total_assets = total_matching_assets

    query = apply_status_filter(base_query, status, now)
    status_filter_label = ASSET_STATUS_OPTIONS[status]
    sort_label = ASSET_SORT_LABELS[sort]
    reverse_direction = "desc" if direction == "asc" else "asc"
    sort_links = {
        sort_key: next_sort_direction(sort, direction, sort_key)
        for sort_key in ASSET_SORT_OPTIONS
    }

    per_page = clamp_page_size(per_page)
    pagination = build_pagination(total_assets, page, per_page)

    assets = (
        apply_asset_sort(query, sort, direction)
        .offset(pagination.offset)
        .limit(pagination.per_page)
        .all()
    )
    prepare_assets_for_display(assets, now)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "session_user": session_user,
            "session_is_admin": current_user.is_admin,
            "assets": assets,
            "q": q,
            "status": status,
            "sort": sort,
            "direction": direction,
            "reverse_direction": reverse_direction,
            "sort_links": sort_links,
            "sort_label": sort_label,
            "status_filter_label": status_filter_label,
            "status_options": ASSET_STATUS_OPTIONS,
            "page_size_options": DASHBOARD_PAGE_SIZE_OPTIONS,
            "total_assets": total_assets,
            "total_matching_assets": total_matching_assets,
            "export_max_rows": EXPORT_MAX_ROWS,
            "export_is_truncated": total_assets > EXPORT_MAX_ROWS,
            "communicating_assets": communicating_assets,
            "stale_assets": stale_assets,
            "inactive_assets": inactive_assets,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.total_pages,
            "first_item": pagination.first_item,
            "last_item": min(pagination.offset + len(assets), total_assets),
            "has_previous_page": pagination.has_previous_page,
            "has_next_page": pagination.has_next_page,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.get("/assets/{asset_id}", response_class=HTMLResponse)
def asset_detail(asset_id: int, request: Request, db: Session = Depends(get_db)):
    session_user = get_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    recent_checkins = (
        db.query(models.AssetCheckin)
        .filter(models.AssetCheckin.asset_id == asset.id)
        .order_by(models.AssetCheckin.created_at.desc())
        .limit(10)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "asset_detail.html",
        {
            "asset": asset,
            "session_user": session_user,
            "csrf_token": get_csrf_token(request),
            "network_interfaces": parse_network_interfaces(asset.network_interfaces),
            "recent_checkins": recent_checkins,
        },
    )
