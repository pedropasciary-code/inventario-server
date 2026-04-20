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

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int
    ultima_comunicacao: datetime

    class Config:
        from_attributes = True