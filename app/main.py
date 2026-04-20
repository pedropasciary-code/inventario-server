from datetime import datetime

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from . import models, schemas

app = FastAPI(title="Inventário Server")

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/checkin", response_model=schemas.AssetResponse)
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
        ultima_comunicacao=datetime.utcnow()
    )

    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)

    return new_asset