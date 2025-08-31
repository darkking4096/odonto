"""
services/main.py - VERSÃO ETAPA 5
"""

import os
import logging
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

from services.core.database import init_db, get_db
from services.core.webhook import process_webhook
from services.api.admin import admin_router
from services.core.calendar import get_calendar_client

# Configurar logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    # Startup
    logger.info("🚀 Iniciando aplicação Odonto IA...")
    
    # Inicializar banco de dados
    try:
        init_db()
        logger.info("✅ Banco de dados inicializado")
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco: {e}")
        
    # Testar conexão com Google Calendar
    try:
        client = get_calendar_client()
        if client.test_connection():
            logger.info("✅ Google Calendar conectado")
        else:
            logger.warning("⚠️ Google Calendar não configurado")
    except Exception as e:
        logger.warning(f"⚠️ Google Calendar não disponível: {e}")
    
    yield
    
    # Shutdown
    logger.info("👋 Encerrando aplicação...")


# Criar aplicação FastAPI
app = FastAPI(
    title="Odonto IA API",
    description="Sistema de agendamento odontológico com IA",
    version="1.0.0 - Etapa 5",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar origens permitidas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== ENDPOINTS PRINCIPAIS ==========

@app.get("/")
async def root():
    """Endpoint raiz."""
    return {
        "service": "Odonto IA",
        "version": "1.0.0 - Etapa 5",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check para monitoramento."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Verificar banco de dados
    try:
        with get_db() as db:
            result = db.execute("SELECT 1").fetchone()
            health_status["services"]["database"] = "ok"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
        
    # Verificar Google Calendar
    try:
        client = get_calendar_client()
        if client.test_connection():
            health_status["services"]["google_calendar"] = "ok"
        else:
            health_status["services"]["google_calendar"] = "not configured"
    except Exception as e:
        health_status["services"]["google_calendar"] = f"error: {str(e)}"
        
    # Retornar status apropriado
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
        
    return health_status


@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    """
    Webhook para receber mensagens do Evolution API.
    
    Processa mensagens do WhatsApp e retorna respostas do bot.
    """
    try:
        body = await request.json()
        logger.info(f"Webhook recebido: {body.get('event', 'unknown')}")
        
        # Processar webhook
        response = await process_webhook(body)
        
        if response:
            logger.info(f"Resposta enviada: {response[:100]}...")
            return {"status": "success", "response": response}
        else:
            return {"status": "ignored", "reason": "No response needed"}
            
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return {"status": "error", "message": str(e)}


# ========== ENDPOINTS DE TESTE ==========

@app.post("/test/message")
async def test_message(request: Request):
    """
    Endpoint de teste para simular mensagens.
    
    Body esperado:
    {
        "phone": "5511999999999",
        "message": "Oi, quero agendar uma consulta"
    }
    """
    try:
        data = await request.json()
        phone = data.get("phone", "5511999999999")
        message = data.get("message", "")
        
        # Simular estrutura do Evolution
        fake_webhook = {
            "event": "messages.upsert",
            "instance": "test_instance",
            "data": {
                "key": {
                    "remoteJid": f"{phone}@s.whatsapp.net",
                    "fromMe": False,
                    "id": f"TEST_{datetime.now().timestamp()}"
                },
                "message": {
                    "conversation": message
                }
            }
        }
        
        # Processar como webhook normal
        response = await process_webhook(fake_webhook)
        
        return {
            "status": "success",
            "phone": phone,
            "message_received": message,
            "bot_response": response
        }
        
    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test/calendar")
async def test_calendar():
    """Testa conexão e lista próximos slots disponíveis."""
    try:
        from services.core.calendar import get_calendar_service
        
        service = get_calendar_service()
        
        # Testar conexão
        if not service.client.test_connection():
            return {"status": "error", "message": "Calendar not connected"}
            
        # Buscar slots disponíveis
        slots = service.list_free_slots(
            duration_min=30,
            limit=5
        )
        
        return {
            "status": "success",
            "calendar_id": service.calendar_id,
            "timezone": str(service.timezone),
            "available_slots": [
                {
                    "date": slot["date"].isoformat(),
                    "time": slot["start_time"].isoformat(),
                    "formatted": slot["formatted"],
                    "weekday": slot["weekday"]
                }
                for slot in slots
            ]
        }
        
    except Exception as e:
        logger.error(f"Erro no teste do calendar: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== ENDPOINTS ADMINISTRATIVOS ==========

# Incluir router de admin
app.include_router(admin_router)


# ========== ENDPOINTS DE ESTATÍSTICAS ==========

@app.get("/stats/conversations")
async def conversation_stats():
    """Estatísticas de conversas."""
    with get_db() as db:
        # Total de conversas
        total = db.execute(
            "SELECT COUNT(*) FROM conversation_state"
        ).scalar()
        
        # Por estágio
        by_stage = db.execute(
            """
            SELECT current_stage, COUNT(*) as count
            FROM conversation_state
            GROUP BY current_stage
            ORDER BY count DESC
            """
        ).fetchall()
        
        # Conversas hoje
        today = db.execute(
            """
            SELECT COUNT(*) 
            FROM conversation_state
            WHERE DATE(created_at) = CURRENT_DATE
            """
        ).scalar()
        
        # Taxa de conclusão
        completed = db.execute(
            """
            SELECT COUNT(*)
            FROM conversation_state
            WHERE current_stage = 'fechamento'
            """
        ).scalar()
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        return {
            "total_conversations": total,
            "today": today,
            "completion_rate": f"{completion_rate:.1f}%",
            "by_stage": {
                stage: count for stage, count in by_stage
            }
        }


@app.get("/stats/appointments")
async def appointment_stats():
    """Estatísticas de agendamentos."""
    with get_db() as db:
        # Total de agendamentos
        total = db.execute(
            "SELECT COUNT(*) FROM appointments"
        ).scalar()
        
        # Agendamentos hoje
        today = db.execute(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE date = CURRENT_DATE
              AND status = 'confirmed'
            """
        ).scalar()
        
        # Agendamentos esta semana
        week = db.execute(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE date >= DATE_TRUNC('week', CURRENT_DATE)
              AND date < DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '1 week'
              AND status = 'confirmed'
            """
        ).scalar()
        
        # Taxa de cancelamento
        cancelled = db.execute(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE status = 'cancelled'
            """
        ).scalar()
        
        cancellation_rate = (cancelled / total * 100) if total > 0 else 0
        
        # Procedimento mais agendado
        top_procedure = db.execute(
            """
            SELECT p.name, COUNT(a.id) as count
            FROM appointments a
            JOIN procedure_catalog p ON p.code = a.procedure_code
            WHERE a.status = 'confirmed'
            GROUP BY p.name
            ORDER BY count DESC
            LIMIT 1
            """
        ).fetchone()
        
        return {
            "total_appointments": total,
            "today": today,
            "this_week": week,
            "cancellation_rate": f"{cancellation_rate:.1f}%",
            "top_procedure": {
                "name": top_procedure[0] if top_procedure else None,
                "count": top_procedure[1] if top_procedure else 0
            }
        }


# ========== MAIN ==========

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"🚀 Iniciando servidor em {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )