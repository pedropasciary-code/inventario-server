from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .database import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, nullable=True)
    usuario = Column(String, nullable=True)
    cpu = Column(String, nullable=True)
    ram = Column(String, nullable=True)
    sistema = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    serial = Column(String, nullable=True)
    ultima_comunicacao = Column(DateTime, default=datetime.utcnow)