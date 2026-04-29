from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from .database import Base


class Asset(Base):
    # Representa um equipamento inventariado e os metadados coletados pelo agent.
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, nullable=True, index=True)
    usuario = Column(String, nullable=True)
    cpu = Column(String, nullable=True)
    ram = Column(String, nullable=True)
    sistema = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    serial = Column(String, nullable=True, index=True)

    fabricante = Column(String, nullable=True)
    modelo = Column(String, nullable=True)
    motherboard = Column(String, nullable=True)
    bios_version = Column(String, nullable=True)
    arquitetura = Column(String, nullable=True)
    versao_windows = Column(String, nullable=True)
    mac_address = Column(String, nullable=True, index=True)
    disco_total_gb = Column(String, nullable=True)
    disco_livre_gb = Column(String, nullable=True)
    agent_version = Column(String, nullable=True)

    ultimo_boot = Column(DateTime, nullable=True)
    ultima_comunicacao = Column(DateTime, default=datetime.utcnow)


class User(Base):
    # Armazena os usuários autorizados a acessar o painel web do inventário.
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
