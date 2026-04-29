import math

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_
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

    communicating_assets = (
        base_query
        .filter(models.Asset.ultima_comunicacao >= online_after)
        .count()
    )
    stale_assets = (
        base_query
        .filter(models.Asset.ultima_comunicacao < online_after)
        .filter(models.Asset.ultima_comunicacao >= stale_after)
        .count()
    )
    inactive_assets = (
        base_query
        .filter(
            or_(
                models.Asset.ultima_comunicacao.is_(None),
                models.Asset.ultima_comunicacao < stale_after,
            )
        )
        .count()
    )

    query = apply_status_filter(base_query, status, now)
    total_assets = query.count()
    total_matching_assets = base_query.count()
    status_filter_label = ASSET_STATUS_OPTIONS[status]
    sort_label = ASSET_SORT_LABELS[sort]
    reverse_direction = "desc" if direction == "asc" else "asc"
    sort_links = {
        sort_key: next_sort_direction(sort, direction, sort_key)
        for sort_key in ASSET_SORT_OPTIONS
    }

    per_page = clamp_page_size(per_page)
    total_pages = max(math.ceil(total_assets / per_page), 1)
    page = min(max(page, 1), total_pages)
    offset = (page - 1) * per_page

    assets = (
        apply_asset_sort(query, sort, direction)
        .offset(offset)
        .limit(per_page)
        .all()
    )
    prepare_assets_for_display(assets, now)

    first_item = offset + 1 if total_assets else 0
    last_item = min(offset + len(assets), total_assets)

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
            "communicating_assets": communicating_assets,
            "stale_assets": stale_assets,
            "inactive_assets": inactive_assets,
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
            "network_interfaces": parse_network_interfaces(asset.network_interfaces),
            "recent_checkins": recent_checkins,
        },
    )
