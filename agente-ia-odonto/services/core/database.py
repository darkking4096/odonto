"""
Configuração do banco de dados
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# URL do banco de dados
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@postgres:5432/odonto_db"
)

# Criar engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False  # Mudar para True se quiser ver queries SQL
)

# Criar session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para modelos
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency para obter sessão do banco
    
    Yields:
        Session: Sessão do SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializa o banco de dados
    Cria todas as tabelas se não existirem
    """
    try:
        from models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Banco de dados inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {str(e)}")
        raise


def test_connection() -> bool:
    """
    Testa conexão com o banco
    
    Returns:
        bool: True se conectou com sucesso
    """
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        logger.info("Conexão com banco testada com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao conectar no banco: {str(e)}")
        return False