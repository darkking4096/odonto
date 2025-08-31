"""
Modelos do banco de dados
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, Time, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Client(Base):
    """Modelo de cliente"""
    __tablename__ = 'clients'
    
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    conversations = relationship("Conversation", back_populates="client")
    profile = relationship("ClientProfile", back_populates="client", uselist=False)
    stage_history = relationship("StageHistory", back_populates="client")


class Conversation(Base):
    """Modelo de conversa"""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    client = relationship("Client", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """Modelo de mensagem"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    content = Column(Text, nullable=False)
    direction = Column(String(3), nullable=False)  # 'in' ou 'out'
    whatsapp_message_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    conversation = relationship("Conversation", back_populates="messages")


class StageHistory(Base):
    """Histórico de mudanças de estágio"""
    __tablename__ = 'stage_history'
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    stage_from = Column(String(50), nullable=False)
    stage_to = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    client = relationship("Client", back_populates="stage_history")


class ClientProfile(Base):
    """Perfil do cliente com dados extraídos"""
    __tablename__ = 'client_profile'
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'), unique=True, nullable=False)
    full_name = Column(Text, nullable=True)
    procedure = Column(Text, nullable=True)
    desired_date = Column(Date, nullable=True)
    desired_time = Column(Time, nullable=True)
    desired_window = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    client = relationship("Client", back_populates="profile")


class StagePrompt(Base):
    """Prompts configuráveis por estágio"""
    __tablename__ = 'stage_prompt'
    
    id = Column(Integer, primary_key=True)
    stage_name = Column(Text, unique=True, nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_template = Column(Text, nullable=False)
    active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)