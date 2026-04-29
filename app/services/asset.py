import json
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import asc, desc, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..formatting import ensure_utc, utc_now


ASSET_TEXT_FIELDS = [
    "hostname",
    "usuario",
    "cpu",
    "ram",
    "sistema",
    "ip",
    "serial",
    "fabricante",
    "modelo",
    "motherboard",
    "bios_version",
    "arquitetura",
    "versao_windows",
    "mac_address",
    "network_interfaces",
    "disco_total_gb",
    "disco_livre_gb",
    "agent_version",
]

UNKNOWN_SERIAL_VALUES = {
    "0",
    "NONE",
    "NULL",
    "SYSTEM SERIAL NUMBER",
    "TO BE FILLED BY O.E.M.",
    "TO BE FILLED BY OEM",
    "UNKNOWN",
}

ASSET_ONLINE_WINDOW = timedelta(hours=24)
ASSET_STALE_WINDOW = timedelta(days=7)

DASHBOARD_DEFAULT_PAGE_SIZE = 25
DASHBOARD_MAX_PAGE_SIZE = 100
DASHBOARD_PAGE_SIZE_OPTIONS = [10, 25, 50, 100]

ASSET_STATUS_OPTIONS = {
    "all": "Todos",
    "online": "Comunicando",
    "stale": "Atrasados",
    "inactive": "Inativos",
}

ASSET_SORT_OPTIONS = {
    "hostname": models.Asset.hostname,
    "usuario": models.Asset.usuario,
    "ultima_comunicacao": models.Asset.ultima_comunicacao,
}

ASSET_SORT_LABELS = {
    "hostname": "Hostname",
    "usuario": "Usuário",
    "ultima_comunicacao": "Última comunicação",
}


def normalize_status_filter(status: str | None) -> str:
    if status in ASSET_STATUS_OPTIONS:
        return status
    return "all"


def normalize_sort(sort: str | None) -> str:
    if sort in ASSET_SORT_OPTIONS:
        return sort
    return "hostname"


def normalize_direction(direction: str | None) -> str:
    if direction == "desc":
        return "desc"
    return "asc"


def normalize_mac_address(mac_address: str | None) -> str | None:
    if not mac_address:
        return None
    mac_address = mac_address.strip().upper().replace(":", "-")
    if mac_address in {"00-00-00-00-00-00", "FF-FF-FF-FF-FF-FF"}:
        return None
    return mac_address or None


def normalize_serial(serial: str | None) -> str | None:
    if not serial:
        return None
    serial = " ".join(serial.strip().upper().split())
    if serial in UNKNOWN_SERIAL_VALUES:
        return None
    return serial or None


def normalize_asset_payload(asset: schemas.AssetCreate) -> dict:
    data = asset.model_dump()
    for field in ASSET_TEXT_FIELDS:
        value = data.get(field)
        if isinstance(value, str):
            value = value.strip()
            data[field] = value or None
        if field == "network_interfaces" and isinstance(value, list):
            data[field] = json.dumps(value, ensure_ascii=False)
    data["serial"] = normalize_serial(data.get("serial"))
    data["mac_address"] = normalize_mac_address(data.get("mac_address"))
    return data


def find_asset_by_identity(asset_data: dict, db: Session) -> models.Asset | None:
    serial = asset_data.get("serial")
    mac_address = asset_data.get("mac_address")
    hostname = asset_data.get("hostname")

    serial_asset = None
    mac_asset = None

    if serial:
        serial_asset = db.query(models.Asset).filter(models.Asset.serial == serial).first()

    if mac_address:
        mac_asset = db.query(models.Asset).filter(models.Asset.mac_address == mac_address).first()

    if serial_asset and mac_asset and serial_asset.id != mac_asset.id:
        raise HTTPException(
            status_code=409,
            detail="Serial e MAC Address apontam para ativos diferentes",
        )

    if serial_asset:
        return serial_asset

    if mac_asset:
        return mac_asset

    if hostname:
        hostname_matches = (
            db.query(models.Asset)
            .filter(models.Asset.hostname == hostname)
            .limit(2)
            .all()
        )
        if len(hostname_matches) == 1:
            return hostname_matches[0]
        if len(hostname_matches) > 1:
            raise HTTPException(
                status_code=409,
                detail="Hostname ambíguo; envie serial ou MAC Address para identificar o ativo",
            )

    return None


def apply_asset_payload(asset_record: models.Asset, asset_data: dict):
    for field, value in asset_data.items():
        setattr(asset_record, field, value)
    asset_record.ultima_comunicacao = utc_now()


def add_asset_checkin(asset_record: models.Asset, asset_data: dict, event_type: str, db: Session):
    checkin = models.AssetCheckin(
        asset_id=asset_record.id,
        event_type=event_type,
        hostname=asset_data.get("hostname"),
        usuario=asset_data.get("usuario"),
        serial=asset_data.get("serial"),
        mac_address=asset_data.get("mac_address"),
        ip=asset_data.get("ip"),
        agent_version=asset_data.get("agent_version"),
        payload_json=json.dumps(asset_data, ensure_ascii=False, default=str),
    )
    db.add(checkin)


def commit_asset_checkin(asset_record: models.Asset, asset_data: dict, db: Session, event_type: str):
    try:
        db.flush()
        add_asset_checkin(asset_record, asset_data, event_type, db)
        db.commit()
        db.refresh(asset_record)
        return asset_record
    except IntegrityError as error:
        db.rollback()
        conflicting_asset = find_asset_by_identity(asset_data, db)
        if not conflicting_asset:
            raise HTTPException(
                status_code=409,
                detail="Ativo duplicado por serial ou MAC Address",
            ) from error
        apply_asset_payload(conflicting_asset, asset_data)
        db.flush()
        add_asset_checkin(conflicting_asset, asset_data, "merged", db)
        db.commit()
        db.refresh(conflicting_asset)
        return conflicting_asset


def get_asset_status(asset: models.Asset, now) -> dict:
    last_seen = ensure_utc(asset.ultima_comunicacao)
    if not last_seen:
        return {"label": "Sem check-in", "class": "inactive"}
    elapsed = now - last_seen
    if elapsed <= ASSET_ONLINE_WINDOW:
        return {"label": "Comunicando", "class": "online"}
    if elapsed <= ASSET_STALE_WINDOW:
        return {"label": "Atrasado", "class": "stale"}
    return {"label": "Inativo", "class": "inactive"}


def prepare_assets_for_display(assets: list[models.Asset], now):
    for asset in assets:
        asset.dashboard_status = get_asset_status(asset, now)
    return assets


def build_asset_query(db: Session, q: str | None = None):
    query = db.query(models.Asset)
    if q:
        termo = f"%{q}%"
        query = query.filter(
            or_(
                models.Asset.hostname.ilike(termo),
                models.Asset.usuario.ilike(termo),
                models.Asset.serial.ilike(termo),
                models.Asset.fabricante.ilike(termo),
                models.Asset.modelo.ilike(termo),
                models.Asset.ip.ilike(termo),
            )
        )
    return query


def apply_status_filter(query, status: str, now):
    online_after = now - ASSET_ONLINE_WINDOW
    stale_after = now - ASSET_STALE_WINDOW
    if status == "online":
        return query.filter(models.Asset.ultima_comunicacao >= online_after)
    if status == "stale":
        return (
            query
            .filter(models.Asset.ultima_comunicacao < online_after)
            .filter(models.Asset.ultima_comunicacao >= stale_after)
        )
    if status == "inactive":
        return query.filter(
            or_(
                models.Asset.ultima_comunicacao.is_(None),
                models.Asset.ultima_comunicacao < stale_after,
            )
        )
    return query


def apply_asset_sort(query, sort: str, direction: str):
    sort_column = ASSET_SORT_OPTIONS[sort]
    order_expression = desc(sort_column) if direction == "desc" else asc(sort_column)
    return query.order_by(order_expression, asc(models.Asset.id))


def next_sort_direction(current_sort: str, current_direction: str, target_sort: str) -> str:
    if current_sort == target_sort and current_direction == "asc":
        return "desc"
    return "asc"


def clamp_page_size(per_page: int) -> int:
    if per_page <= 0:
        return DASHBOARD_DEFAULT_PAGE_SIZE
    return min(per_page, DASHBOARD_MAX_PAGE_SIZE)
