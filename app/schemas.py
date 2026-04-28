from pydantic import BaseModel
from datetime import datetime


class AssetBase(BaseModel):
    # Define os campos compartilhados entre entrada e saída da API de ativos.
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
    agent_version: str | None = None
    ultimo_boot: datetime | None = None


class AssetCreate(AssetBase):
    # Schema recebido no check-in enviado pelo agent.
    pass


class AssetResponse(AssetBase):
    # Schema devolvido pela API após criar ou atualizar um ativo.
    id: int
    ultima_comunicacao: datetime

    class Config:
        # Permite converter diretamente objetos ORM do SQLAlchemy em resposta Pydantic.
        from_attributes = True
