from pydantic import BaseModel
from datetime import datetime


class AssetBase(BaseModel):
    hostname: str | None = None
    usuario: str | None = None
    cpu: str | None = None
    ram: str | None = None
    sistema: str | None = None
    ip: str | None = None
    serial: str | None = None

    fabricante: str | None = None
    modelo: str | None = None
    motherboard: str | None = None
    bios_version: str | None = None
    arquitetura: str | None = None
    versao_windows: str | None = None
    mac_address: str | None = None
    disco_total_gb: str | None = None
    disco_livre_gb: str | None = None

    ultimo_boot: datetime | None = None


class AssetCreate(AssetBase):
    pass


class AssetResponse(AssetBase):
    id: int
    ultima_comunicacao: datetime

    class Config:
        from_attributes = True