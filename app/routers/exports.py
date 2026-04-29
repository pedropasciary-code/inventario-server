import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_session_user
from ..formatting import format_datetime, utc_now
from ..services.asset import (
    apply_asset_sort,
    apply_status_filter,
    build_asset_query,
    normalize_direction,
    normalize_sort,
    normalize_status_filter,
    prepare_assets_for_display,
)
from ..services.audit import record_audit_event

router = APIRouter()


@router.get("/export/csv")
def export_csv(
    request: Request,
    q: str | None = None,
    status: str = "all",
    sort: str = "hostname",
    direction: str = "asc",
    db: Session = Depends(get_db),
):
    session_user = get_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    status = normalize_status_filter(status)
    sort = normalize_sort(sort)
    direction = normalize_direction(direction)
    record_audit_event(
        db,
        "export_csv",
        request,
        username=session_user,
        details={"q": q, "status": status, "sort": sort, "direction": direction},
    )
    now = utc_now()
    query = apply_status_filter(build_asset_query(db, q), status, now)
    assets = apply_asset_sort(query, sort, direction).all()
    prepare_assets_for_display(assets, now)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Hostname", "Usuario", "Serial", "Fabricante", "Modelo", "CPU", "RAM",
        "Sistema", "Versao Windows", "IP", "MAC Address", "Status",
        "Disco Total GB", "Disco Livre GB", "Ultimo Boot", "Ultima Comunicacao",
    ])

    for asset in assets:
        writer.writerow([
            asset.hostname, asset.usuario, asset.serial, asset.fabricante,
            asset.modelo, asset.cpu, asset.ram, asset.sistema, asset.versao_windows,
            asset.ip, asset.mac_address, asset.dashboard_status["label"],
            asset.disco_total_gb, asset.disco_livre_gb,
            format_datetime(asset.ultimo_boot),
            format_datetime(asset.ultima_comunicacao),
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventario.csv"},
    )


@router.get("/export/xlsx")
def export_xlsx(
    request: Request,
    q: str | None = None,
    status: str = "all",
    sort: str = "hostname",
    direction: str = "asc",
    db: Session = Depends(get_db),
):
    session_user = get_session_user(request, db)
    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    status = normalize_status_filter(status)
    sort = normalize_sort(sort)
    direction = normalize_direction(direction)
    record_audit_event(
        db,
        "export_xlsx",
        request,
        username=session_user,
        details={"q": q, "status": status, "sort": sort, "direction": direction},
    )
    now = utc_now()
    query = apply_status_filter(build_asset_query(db, q), status, now)
    assets = apply_asset_sort(query, sort, direction).all()
    prepare_assets_for_display(assets, now)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Inventario"

    headers = [
        "Hostname", "Usuario", "Serial", "Fabricante", "Modelo", "CPU", "RAM",
        "Sistema", "Versao Windows", "Arquitetura", "IP", "MAC Address", "Status",
        "Placa-mae", "BIOS", "Disco Total GB", "Disco Livre GB",
        "Ultimo Boot", "Ultima Comunicacao",
    ]

    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for asset in assets:
        sheet.append([
            asset.hostname, asset.usuario, asset.serial, asset.fabricante,
            asset.modelo, asset.cpu, asset.ram, asset.sistema, asset.versao_windows,
            asset.arquitetura, asset.ip, asset.mac_address,
            asset.dashboard_status["label"], asset.motherboard, asset.bios_version,
            asset.disco_total_gb, asset.disco_livre_gb,
            format_datetime(asset.ultimo_boot),
            format_datetime(asset.ultima_comunicacao),
        ])

    for column_cells in sheet.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter
        for cell in column_cells:
            value = str(cell.value) if cell.value is not None else ""
            if len(value) > max_length:
                max_length = len(value)
        sheet.column_dimensions[column_letter].width = min(max_length + 2, 40)

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=inventario.xlsx"},
    )
