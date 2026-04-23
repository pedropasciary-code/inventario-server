from datetime import datetime
import csv
import io

from fastapi import FastAPI, Depends, Header, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from openpyxl import Workbook
from openpyxl.styles import Font

from .database import Base, engine, SessionLocal
from .config import AGENT_TOKEN
from .auth import verify_password
from . import models, schemas

# Instancia a API principal e configura onde o FastAPI buscará os templates HTML.
app = FastAPI(title="Inventário Server")
templates = Jinja2Templates(directory="app/templates")

# Garante a criação das tabelas na inicialização caso ainda não existam no banco.
Base.metadata.create_all(bind=engine)


def get_db():
    # Abre uma sessão por requisição e sempre fecha a conexão ao final do uso.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_agent_token(x_agent_token: str = Header(default=None)):
    # Restringe o endpoint de check-in para apenas agents autorizados.
    if x_agent_token != AGENT_TOKEN:
        raise HTTPException(status_code=401, detail="Token do agent inválido")


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
        {"error": None}
    )


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Busca o usuário pelo nome informado no formulário.
    user = db.query(models.User).filter(models.User.username == username).first()

    # Só permite login para usuário existente, ativo e com senha válida.
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Usuário ou senha inválidos"},
            status_code=401
        )

    # Salva o usuário autenticado em cookie para liberar acesso ao dashboard.
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="session_user", value=user.username, httponly=True)
    return response


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    # Usa o cookie de sessão para impedir acesso ao painel sem autenticação.
    session_user = request.cookies.get("session_user")

    if not session_user:
        return RedirectResponse(url="/login", status_code=303)

    # Monta a consulta base com todos os ativos cadastrados.
    query = db.query(models.Asset)

    if q:
        # Aplica busca textual em múltiplos campos para facilitar a localização de máquinas.
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

    # Ordena por hostname para manter a listagem previsível no dashboard.
    assets = query.order_by(models.Asset.hostname.asc()).all()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "session_user": session_user,
            "assets": assets,
            "q": q
        }
    )

@app.post("/checkin", response_model=schemas.AssetResponse, dependencies=[Depends(validate_agent_token)])
def checkin(asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    # Tenta localizar o ativo pelo serial para decidir entre atualização e criação.
    existing_asset = None

    if asset.serial:
        existing_asset = db.query(models.Asset).filter(models.Asset.serial == asset.serial).first()

    if existing_asset:
        # Atualiza os dados do ativo já existente com a última coleta recebida do agent.
        existing_asset.hostname = asset.hostname
        existing_asset.usuario = asset.usuario
        existing_asset.cpu = asset.cpu
        existing_asset.ram = asset.ram
        existing_asset.sistema = asset.sistema
        existing_asset.ip = asset.ip
        existing_asset.serial = asset.serial
        existing_asset.fabricante = asset.fabricante
        existing_asset.modelo = asset.modelo
        existing_asset.motherboard = asset.motherboard
        existing_asset.bios_version = asset.bios_version
        existing_asset.arquitetura = asset.arquitetura
        existing_asset.versao_windows = asset.versao_windows
        existing_asset.mac_address = asset.mac_address
        existing_asset.disco_total_gb = asset.disco_total_gb
        existing_asset.disco_livre_gb = asset.disco_livre_gb
        existing_asset.ultimo_boot = asset.ultimo_boot
        existing_asset.ultima_comunicacao = datetime.utcnow()

        db.commit()
        db.refresh(existing_asset)
        return existing_asset

    # Se o serial ainda não existe no banco, cria um novo registro do ativo.
    new_asset = models.Asset(
        hostname=asset.hostname,
        usuario=asset.usuario,
        cpu=asset.cpu,
        ram=asset.ram,
        sistema=asset.sistema,
        ip=asset.ip,
        serial=asset.serial,
        fabricante=asset.fabricante,
        modelo=asset.modelo,
        motherboard=asset.motherboard,
        bios_version=asset.bios_version,
        arquitetura=asset.arquitetura,
        versao_windows=asset.versao_windows,
        mac_address=asset.mac_address,
        disco_total_gb=asset.disco_total_gb,
        disco_livre_gb=asset.disco_livre_gb,
        ultimo_boot=asset.ultimo_boot,
        ultima_comunicacao=datetime.utcnow()
    )

    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)

    return new_asset

@app.get("/export/csv")
def export_csv(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    # Exige sessão válida antes de liberar exportação dos dados.
    session_user = request.cookies.get("session_user")

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
    session_user = request.cookies.get("session_user")

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
def logout():
    # Encerra a sessão removendo o cookie e redireciona para a tela de login.
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_user")
    return response

@app.get("/export/xlsx")
def export_xlsx(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    # Exige autenticação para exportação em Excel assim como no CSV.
    session_user = request.cookies.get("session_user")

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
