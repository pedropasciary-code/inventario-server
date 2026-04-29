from datetime import UTC, datetime, timedelta
import csv
import hmac
import io
import math
import secrets

from fastapi import FastAPI, Depends, Header, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from openpyxl import Workbook
from openpyxl.styles import Font
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .database import SessionLocal
from .config import AGENT_TOKEN, SECRET_KEY, SESSION_COOKIE_SECURE, DISPLAY_TIMEZONE
from .auth import verify_password
from . import models, schemas

# Instancia a API principal e configura onde o FastAPI buscará os templates HTML.
app = FastAPI(title="Inventário Server")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="inventario_session",
    max_age=8 * 60 * 60,
    same_site="lax",
    https_only=SESSION_COOKIE_SECURE,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def format_datetime(value: datetime | None) -> str:
    value = ensure_utc(value)

    if not value:
        return ""

    return value.astimezone(DISPLAY_TIMEZONE).strftime("%d/%m/%Y %H:%M")


templates.env.filters["datetime_br"] = format_datetime


def get_db():
    # Abre uma sessão por requisição e sempre fecha a conexão ao final do uso.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_agent_token(x_agent_token: str = Header(default=None)):
    if not x_agent_token or not hmac.compare_digest(x_agent_token, AGENT_TOKEN):
        raise HTTPException(status_code=401, detail="Token do agent inválido")


def get_session_user(request: Request, db: Session) -> str | None:
    # Lê a sessão assinada e confirma no banco se o usuário ainda existe e está ativo.
    username = request.session.get("session_user")

    if not username:
        return None

    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or not user.is_active:
        request.session.clear()
        return None

    return user.username


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
    "disco_total_gb",
    "disco_livre_gb",
    "agent_version",
]

LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW = timedelta(minutes=15)
login_attempts: dict[str, list[datetime]] = {}

DASHBOARD_DEFAULT_PAGE_SIZE = 25
DASHBOARD_MAX_PAGE_SIZE = 100
ASSET_ONLINE_WINDOW = timedelta(hours=24)
ASSET_STALE_WINDOW = timedelta(days=7)


def get_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token

    return token


def validate_csrf_token(request: Request, csrf_token: str | None):
    session_token = request.session.get("csrf_token")

    if (
        not session_token
        or not csrf_token
        or not hmac.compare_digest(session_token, csrf_token)
    ):
        raise HTTPException(status_code=403, detail="Token CSRF inválido")


def get_client_ip(request: Request) -> str:
    if request.client:
        return request.client.host

    return "unknown"


def login_rate_limit_key(request: Request, username: str) -> str:
    return f"{get_client_ip(request)}:{username.lower().strip()}"


def prune_login_attempts(key: str, now: datetime):
    window_start = now - LOGIN_RATE_LIMIT_WINDOW
    attempts = [
        attempt
        for attempt in login_attempts.get(key, [])
        if attempt >= window_start
    ]

    if attempts:
        login_attempts[key] = attempts
    else:
        login_attempts.pop(key, None)

    return attempts


def enforce_login_rate_limit(request: Request, username: str):
    key = login_rate_limit_key(request, username)
    attempts = prune_login_attempts(key, utc_now())

    if len(attempts) >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Tente novamente mais tarde."
        )


def register_failed_login(request: Request, username: str):
    key = login_rate_limit_key(request, username)
    now = utc_now()
    attempts = prune_login_attempts(key, now)
    attempts.append(now)
    login_attempts[key] = attempts


def clear_failed_logins(request: Request, username: str):
    login_attempts.pop(login_rate_limit_key(request, username), None)


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
                models.Asset.ip.ilike(termo)
            )
        )

    return query


def clamp_page_size(per_page: int) -> int:
    if per_page <= 0:
        return DASHBOARD_DEFAULT_PAGE_SIZE

    return min(per_page, DASHBOARD_MAX_PAGE_SIZE)


def get_asset_status(asset: models.Asset, now: datetime) -> dict:
    last_seen = ensure_utc(asset.ultima_comunicacao)

    if not last_seen:
        return {"label": "Sem check-in", "class": "inactive"}

    elapsed = now - last_seen

    if elapsed <= ASSET_ONLINE_WINDOW:
        return {"label": "Comunicando", "class": "online"}

    if elapsed <= ASSET_STALE_WINDOW:
        return {"label": "Atrasado", "class": "stale"}

    return {"label": "Inativo", "class": "inactive"}


def normalize_asset_payload(asset: schemas.AssetCreate) -> dict:
    # Remove espaços acidentais e transforma strings vazias em None antes de comparar/salvar.
    data = asset.model_dump()

    for field in ASSET_TEXT_FIELDS:
        value = data.get(field)

        if isinstance(value, str):
            value = value.strip()
            data[field] = value or None

    return data


def find_asset_by_identity(asset_data: dict, db: Session) -> models.Asset | None:
    # Usa identificadores em ordem de confiança: serial, MAC e por último hostname.
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
            detail="Serial e MAC Address apontam para ativos diferentes"
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
                detail="Hostname ambíguo; envie serial ou MAC Address para identificar o ativo"
            )

    return None


def apply_asset_payload(asset_record: models.Asset, asset_data: dict):
    # Atualiza todos os campos de inventário mantendo a atribuição em um só lugar.
    for field, value in asset_data.items():
        setattr(asset_record, field, value)

    asset_record.ultima_comunicacao = utc_now()


def commit_asset_checkin(asset_record: models.Asset, asset_data: dict, db: Session):
    try:
        db.commit()
        db.refresh(asset_record)
        return asset_record
    except IntegrityError as error:
        db.rollback()

        conflicting_asset = find_asset_by_identity(asset_data, db)

        if not conflicting_asset:
            raise HTTPException(
                status_code=409,
                detail="Ativo duplicado por serial ou MAC Address"
            ) from error

        apply_asset_payload(conflicting_asset, asset_data)
        db.commit()
        db.refresh(conflicting_asset)
        return conflicting_asset


@app.get("/")
def home():
    # Endpoint simples de health-check para validar se a API está no ar.
    return {"status": "ok"}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    # Renderiza a tela de login inicial sem mensagem de erro.
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": None, "csrf_token": get_csrf_token(request)}
    )


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db)
):
    validate_csrf_token(request, csrf_token)
    enforce_login_rate_limit(request, username)

    # Busca o usuário pelo nome informado no formulário.
    user = db.query(models.User).filter(models.User.username == username).first()

    # Só permite login para usuário existente, ativo e com senha válida.
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        register_failed_login(request, username)
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "error": "Usuário ou senha inválidos",
                "csrf_token": get_csrf_token(request)
            },
            status_code=401
        )

    # Salva o usuário autenticado na sessão assinada para liberar acesso ao dashboard.
    clear_failed_logins(request, username)
    request.session.clear()
    request.session["session_user"] = user.username
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    response = RedirectResponse(url="/dashboard", status_code=303)
    return response


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    q: str | None = None,
    page: int = 1,
    per_page: int = DASHBOARD_DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db)
):
    # Usa a sessão assinada para impedir acesso ao painel sem autenticação.
    session_user = get_session_user(request, db)

    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    query = build_asset_query(db, q)
    now = utc_now()
    online_after = now - ASSET_ONLINE_WINDOW
    stale_after = now - ASSET_STALE_WINDOW

    total_assets = query.count()
    communicating_assets = (
        query
        .filter(models.Asset.ultima_comunicacao >= online_after)
        .count()
    )
    stale_assets = (
        query
        .filter(models.Asset.ultima_comunicacao < online_after)
        .filter(models.Asset.ultima_comunicacao >= stale_after)
        .count()
    )
    inactive_assets = (
        query
        .filter(
            or_(
                models.Asset.ultima_comunicacao.is_(None),
                models.Asset.ultima_comunicacao < stale_after
            )
        )
        .count()
    )

    per_page = clamp_page_size(per_page)
    total_pages = max(math.ceil(total_assets / per_page), 1)
    page = min(max(page, 1), total_pages)
    offset = (page - 1) * per_page

    # Ordena e pagina no banco para manter o dashboard leve quando o inventário crescer.
    assets = (
        query
        .order_by(models.Asset.hostname.asc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    for asset in assets:
        asset.dashboard_status = get_asset_status(asset, now)

    first_item = offset + 1 if total_assets else 0
    last_item = min(offset + len(assets), total_assets)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "session_user": session_user,
            "assets": assets,
            "q": q,
            "total_assets": total_assets,
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
            "csrf_token": get_csrf_token(request)
        }
    )

@app.post("/checkin", response_model=schemas.AssetResponse, dependencies=[Depends(validate_agent_token)])
def checkin(asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    # Normaliza o payload e exige ao menos um identificador estável para o inventário.
    asset_data = normalize_asset_payload(asset)

    if not any(asset_data.get(field) for field in ("serial", "mac_address", "hostname")):
        raise HTTPException(
            status_code=422,
            detail="Informe ao menos serial, MAC Address ou hostname para identificar o ativo"
        )

    existing_asset = find_asset_by_identity(asset_data, db)

    if existing_asset:
        # Atualiza os dados do ativo já existente com a última coleta recebida do agent.
        apply_asset_payload(existing_asset, asset_data)
        return commit_asset_checkin(existing_asset, asset_data, db)

    # Se nenhum identificador existente foi encontrado, cria um novo registro do ativo.
    new_asset = models.Asset(**asset_data, ultima_comunicacao=utc_now())

    db.add(new_asset)
    return commit_asset_checkin(new_asset, asset_data, db)

@app.get("/export/csv")
def export_csv(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    # Exige sessão válida antes de liberar exportação dos dados.
    session_user = get_session_user(request, db)

    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    # Reaproveita a mesma lógica de filtro do dashboard para exportar apenas o resultado visível.
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
                models.Asset.ip.ilike(termo)
            )
        )

    assets = query.order_by(models.Asset.hostname.asc()).all()

    # Gera o CSV em memória para não depender de arquivo temporário em disco.
    output = io.StringIO()
    writer = csv.writer(output)

    # Escreve a linha de cabeçalho com os campos mais importantes do inventário.
    writer.writerow([
        "Hostname",
        "Usuario",
        "Serial",
        "Fabricante",
        "Modelo",
        "CPU",
        "RAM",
        "Sistema",
        "Versao Windows",
        "IP",
        "MAC Address",
        "Disco Total GB",
        "Disco Livre GB",
        "Ultimo Boot",
        "Ultima Comunicacao"
    ])

    # Percorre os ativos filtrados e escreve uma linha para cada máquina.
    for asset in assets:
        writer.writerow([
            asset.hostname,
            asset.usuario,
            asset.serial,
            asset.fabricante,
            asset.modelo,
            asset.cpu,
            asset.ram,
            asset.sistema,
            asset.versao_windows,
            asset.ip,
            asset.mac_address,
            asset.disco_total_gb,
            asset.disco_livre_gb,
            asset.ultimo_boot,
            asset.ultima_comunicacao
        ])

    output.seek(0)

    # Retorna o CSV como download direto no navegador.
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventario.csv"}
    )

@app.get("/assets/{asset_id}", response_class=HTMLResponse)
def asset_detail(asset_id: int, request: Request, db: Session = Depends(get_db)):
    # Mantém a página de detalhes protegida pela mesma sessão do dashboard.
    session_user = get_session_user(request, db)

    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    # Busca o ativo selecionado pelo identificador numérico da URL.
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    # Renderiza a página com todos os metadados do ativo encontrado.
    return templates.TemplateResponse(
        request,
        "asset_detail.html",
        {
            "asset": asset
        }
    )

@app.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    validate_csrf_token(request, csrf_token)

    # Encerra a sessão assinada e redireciona para a tela de login.
    request.session.clear()
    response = RedirectResponse(url="/login", status_code=303)
    return response

@app.get("/export/xlsx")
def export_xlsx(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    # Exige autenticação para exportação em Excel assim como no CSV.
    session_user = get_session_user(request, db)

    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    # Reconstroi a consulta com o mesmo filtro opcional aplicado no dashboard.
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
                models.Asset.ip.ilike(termo)
            )
        )

    assets = query.order_by(models.Asset.hostname.asc()).all()

    # Cria a planilha em memória e prepara a aba principal do inventário.
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Inventario"

    headers = [
        "Hostname",
        "Usuario",
        "Serial",
        "Fabricante",
        "Modelo",
        "CPU",
        "RAM",
        "Sistema",
        "Versao Windows",
        "Arquitetura",
        "IP",
        "MAC Address",
        "Placa-mae",
        "BIOS",
        "Disco Total GB",
        "Disco Livre GB",
        "Ultimo Boot",
        "Ultima Comunicacao"
    ]

    # Adiciona os cabeçalhos e destaca visualmente a primeira linha.
    sheet.append(headers)

    for cell in sheet[1]:
        cell.font = Font(bold=True)

    # Preenche a planilha com uma linha por ativo encontrado.
    for asset in assets:
        sheet.append([
            asset.hostname,
            asset.usuario,
            asset.serial,
            asset.fabricante,
            asset.modelo,
            asset.cpu,
            asset.ram,
            asset.sistema,
            asset.versao_windows,
            asset.arquitetura,
            asset.ip,
            asset.mac_address,
            asset.motherboard,
            asset.bios_version,
            asset.disco_total_gb,
            asset.disco_livre_gb,
            asset.ultimo_boot,
            asset.ultima_comunicacao
        ])

    # Ajusta a largura de cada coluna com base no maior valor encontrado.
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

    # Devolve o arquivo XLSX pronto para download sem salvar nada localmente.
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=inventario.xlsx"}
    )
