"""
API principal do agente de agendamento odontológico
"""
import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import httpx

# Importações locais
from database import engine, get_db, Base
from models import Client, Conversation, Message, StageHistory
from stages.engine import StageEngine

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# Criar aplicação FastAPI
app = FastAPI(
    title="Agente IA Odonto",
    version="1.0.0",
    description="API de agendamento odontológico com IA"
)

# Configurações da Evolution API
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://evolution:8080")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "odonto")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")

# Cache para deduplicação
processed_messages = set()


@app.on_event("startup")
async def startup_event():
    """Inicialização da aplicação"""
    logger.info("Iniciando aplicação...")
    # Criar tabelas se não existirem
    Base.metadata.create_all(bind=engine)
    logger.info("Banco de dados verificado/criado")


@app.get("/")
async def root():
    """Endpoint de health check"""
    return {
        "status": "online",
        "service": "agente-ia-odonto",
        "version": "1.0.0",
        "stage": "etapa4"
    }


@app.post("/webhook")
async def webhook_handler(request: Request, db: Session = Depends(get_db)):
    """
    Handler principal do webhook da Evolution API
    """
    try:
        # Receber payload
        payload = await request.json()
        logger.info(f"Webhook recebido: {json.dumps(payload, indent=2)[:500]}")
        
        # Verificar tipo de evento
        event_type = payload.get("event")
        if event_type != "messages.upsert":
            logger.info(f"Evento ignorado: {event_type}")
            return {"status": "ignored", "reason": "not_message_upsert"}
        
        # Extrair dados da mensagem
        data = payload.get("data", {})
        key = data.get("key", {})
        message = data.get("message", {})
        
        # Validar se é mensagem de entrada
        if not key.get("fromMe", False):
            remote_jid = key.get("remoteJid", "")
            message_id = key.get("id", "")
            
            # Verificar deduplicação
            if message_id in processed_messages:
                logger.info(f"Mensagem duplicada ignorada: {message_id}")
                return {"status": "ignored", "reason": "duplicate"}
            
            # Adicionar ao cache
            processed_messages.add(message_id)
            
            # Limpar cache se muito grande
            if len(processed_messages) > 1000:
                processed_messages.clear()
            
            # Extrair texto da mensagem
            message_text = extract_message_text(message)
            if not message_text:
                logger.warning("Mensagem sem texto ignorada")
                return {"status": "ignored", "reason": "no_text"}
            
            # Processar mensagem
            response_text = await process_message(
                db=db,
                remote_jid=remote_jid,
                message_text=message_text,
                message_id=message_id
            )
            
            # Enviar resposta via Evolution API
            if response_text:
                await send_message(remote_jid, response_text)
            
            return {"status": "processed", "response": response_text}
        
        return {"status": "ignored", "reason": "from_me"}
        
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def extract_message_text(message: Dict[str, Any]) -> Optional[str]:
    """
    Extrai texto da mensagem
    
    Args:
        message: Objeto da mensagem
        
    Returns:
        str: Texto extraído ou None
    """
    # Tentar extrair de diferentes formatos
    if "conversation" in message:
        return message["conversation"]
    elif "extendedTextMessage" in message:
        return message["extendedTextMessage"].get("text", "")
    elif "imageMessage" in message:
        return message["imageMessage"].get("caption", "")
    elif "videoMessage" in message:
        return message["videoMessage"].get("caption", "")
    
    return None


async def process_message(
    db: Session,
    remote_jid: str,
    message_text: str,
    message_id: str
) -> str:
    """
    Processa mensagem recebida
    
    Args:
        db: Sessão do banco
        remote_jid: ID do remetente
        message_text: Texto da mensagem
        message_id: ID único da mensagem
        
    Returns:
        str: Resposta gerada
    """
    try:
        # Extrair número do telefone
        phone = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid
        
        # Buscar ou criar cliente
        client = db.query(Client).filter_by(phone=phone).first()
        if not client:
            client = Client(
                phone=phone,
                name=None,  # Será preenchido pelo engine
                created_at=datetime.utcnow()
            )
            db.add(client)
            db.commit()
            logger.info(f"Novo cliente criado: {phone}")
        
        # Buscar ou criar conversa
        conversation = db.query(Conversation).filter_by(
            client_id=client.id,
            active=True
        ).first()
        
        if not conversation:
            conversation = Conversation(
                client_id=client.id,
                active=True,
                created_at=datetime.utcnow()
            )
            db.add(conversation)
            db.commit()
            logger.info(f"Nova conversa criada para cliente {client.id}")
        
        # Salvar mensagem recebida
        incoming_message = Message(
            conversation_id=conversation.id,
            content=message_text,
            direction='in',
            whatsapp_message_id=message_id,
            created_at=datetime.utcnow()
        )
        db.add(incoming_message)
        db.commit()
        
        # Processar com o engine de estágios
        stage_engine = StageEngine(db)
        response_text = stage_engine.handle(client.id, message_text)
        
        logger.info(f"Resposta gerada: {response_text[:100]}")
        return response_text
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {str(e)}", exc_info=True)
        return "Desculpe, ocorreu um erro. Por favor, tente novamente."


async def send_message(remote_jid: str, text: str) -> bool:
    """
    Envia mensagem via Evolution API
    
    Args:
        remote_jid: Destinatário
        text: Texto da mensagem
        
    Returns:
        bool: Sucesso do envio
    """
    try:
        url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
        
        payload = {
            "number": remote_jid,
            "text": text,
            "delay": 1000  # Delay de 1 segundo para parecer mais natural
        }
        
        headers = {
            "Content-Type": "application/json",
            "apikey": EVOLUTION_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                logger.info(f"Mensagem enviada para {remote_jid}")
                return True
            else:
                logger.error(f"Erro ao enviar mensagem: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {str(e)}", exc_info=True)
        return False


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Verifica saúde da aplicação"""
    try:
        # Testar conexão com banco
        db.execute("SELECT 1")
        
        # Verificar provider de IA
        from ai.factory import AIFactory
        ai_provider = AIFactory.create_provider()
        ai_status = "configured" if ai_provider else "not_configured"
        
        return {
            "status": "healthy",
            "database": "connected",
            "ai_provider": ai_status,
            "evolution_api": EVOLUTION_API_URL,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check falhou: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Retorna estatísticas do sistema"""
    try:
        total_clients = db.query(Client).count()
        total_conversations = db.query(Conversation).count()
        total_messages = db.query(Message).count()
        total_transitions = db.query(StageHistory).count()
        
        # Estágios mais comuns
        from sqlalchemy import func
        stage_stats = db.query(
            StageHistory.stage_to,
            func.count(StageHistory.id).label('count')
        ).group_by(StageHistory.stage_to).all()
        
        return {
            "total_clients": total_clients,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_stage_transitions": total_transitions,
            "stages": {s.stage_to: s.count for s in stage_stats}
        }
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )