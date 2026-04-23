import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Carrega variáveis do .env antes de inicializar a conexão com o banco.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não foi definida no arquivo .env")

# Cria o engine do SQLAlchemy e a fábrica de sessões usada nas requisições.
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base compartilhada por todos os modelos ORM do projeto.
Base = declarative_base()
