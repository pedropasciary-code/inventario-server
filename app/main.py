from datetime import datetime

from fastapi import FastAPI, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .config import AGENT_TOKEN
from . import models, schemas

app = FastAPI(title="Inventário Server")

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_agent_token(x_agent_token: str = Header(default=None)):
    if x_agent_token != AGENT_TOKEN:
        raise HTTPException(status_code=401, detail="Token do agent inválido")


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/checkin", response_model=schemas.AssetResponse, dependencies=[Depends(validate_agent_token)])
def checkin(asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    existing_asset = None

    if asset.serial:
        existing_asset = db.query(models.Asset).filter(models.Asset.serial == asset.serial).first()

    if existing_asset:
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