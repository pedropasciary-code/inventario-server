from sqlalchemy import Column, Float, ForeignKey, Integer, String, DateTime, Boolean, Text
from .database import Base
from .utils import utc_now


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
    serial = Column(String, nullable=True, unique=True, index=True)

    fabricante = Column(String, nullable=True)
    modelo = Column(String, nullable=True)
    motherboard = Column(String, nullable=True)
    bios_version = Column(String, nullable=True)
    arquitetura = Column(String, nullable=True)
    versao_windows = Column(String, nullable=True)
    mac_address = Column(String, nullable=True, unique=True, index=True)
    network_interfaces = Column(String, nullable=True)
    disco_total_gb = Column(Float, nullable=True)
    disco_livre_gb = Column(Float, nullable=True)
    agent_version = Column(String, nullable=True)

    ultimo_boot = Column(DateTime(timezone=True), nullable=True)
    ultima_comunicacao = Column(DateTime(timezone=True), default=utc_now)


class User(Base):
    # Armazena os usuários autorizados a acessar o painel web do inventário.
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssetCheckin(Base):
    # Guarda o histórico bruto de check-ins recebidos para auditoria e suporte.
    __tablename__ = "asset_checkins"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    hostname = Column(String, nullable=True)
    usuario = Column(String, nullable=True)
    serial = Column(String, nullable=True, index=True)
    mac_address = Column(String, nullable=True, index=True)
    ip = Column(String, nullable=True)
    agent_version = Column(String, nullable=True)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)


class AuditEvent(Base):
    # Registra eventos operacionais do painel/API para auditoria básica.
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    username = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=True)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)


class Topology(Base):
    # Canvas de topologia de rede identificado por nome.
    __tablename__ = "topologies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class TopologyNode(Base):
    # Dispositivo posicionado em um canvas de topologia.
    __tablename__ = "topology_nodes"

    id = Column(Integer, primary_key=True, index=True)
    topology_id = Column(Integer, ForeignKey("topologies.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    parent_id = Column(Integer, ForeignKey("topology_nodes.id"), nullable=True)
    node_type = Column(String, nullable=False)
    label = Column(String, nullable=True)
    x = Column(Float, nullable=False, default=0.0)
    y = Column(Float, nullable=False, default=0.0)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    color = Column(String, nullable=True)
    props_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class TopologyEdge(Base):
    # Conexão de rede entre dois nós de uma topologia.
    __tablename__ = "topology_edges"

    id = Column(Integer, primary_key=True, index=True)
    topology_id = Column(Integer, ForeignKey("topologies.id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("topology_nodes.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("topology_nodes.id"), nullable=False)
    connection_type = Column(String, nullable=True)
    label = Column(String, nullable=True)
    color = Column(String, nullable=True)
