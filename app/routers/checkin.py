from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..dependencies import get_db, validate_agent_token
from ..formatting import utc_now
from ..rate_limiting import enforce_checkin_rate_limit
from ..services.asset import (
    apply_asset_payload,
    commit_asset_checkin,
    find_asset_by_identity,
    normalize_asset_payload,
)
from ..services.audit import record_audit_event

router = APIRouter()


@router.post("/checkin", response_model=schemas.AssetResponse, dependencies=[Depends(validate_agent_token)])
def checkin(
    request: Request,
    asset: schemas.AssetCreate,
    db: Session = Depends(get_db),
):
    asset_data = normalize_asset_payload(asset)
    enforce_checkin_rate_limit(request, asset_data)

    if not any(asset_data.get(field) for field in ("serial", "mac_address", "hostname")):
        record_audit_event(
            db,
            "checkin_rejected",
            request,
            details={"reason": "missing_identity"},
        )
        raise HTTPException(
            status_code=422,
            detail="Informe ao menos serial, MAC Address ou hostname para identificar o ativo",
        )

    try:
        existing_asset = find_asset_by_identity(asset_data, db)
    except HTTPException as error:
        if error.status_code == 409:
            record_audit_event(
                db,
                "checkin_rejected",
                request,
                details={
                    "reason": "identity_conflict",
                    "detail": error.detail,
                    "hostname": asset_data.get("hostname"),
                    "serial": asset_data.get("serial"),
                    "mac_address": asset_data.get("mac_address"),
                },
            )
        raise

    if existing_asset:
        apply_asset_payload(existing_asset, asset_data)
        return commit_asset_checkin(existing_asset, asset_data, db, "updated")

    new_asset = models.Asset(**asset_data, ultima_comunicacao=utc_now())
    db.add(new_asset)
    return commit_asset_checkin(new_asset, asset_data, db, "created")
