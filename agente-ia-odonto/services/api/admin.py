"""
services/api/admin.py - ADICIONAR AO ARQUIVO EXISTENTE
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import date, time
from pydantic import BaseModel

from services.core.database import get_db

# Router para endpoints administrativos
admin_router = APIRouter(prefix="/admin", tags=["admin"])


# Modelos Pydantic para requests/responses
class ProcedureModel(BaseModel):
    code: str
    name: str
    duration_min: int
    active: bool = True
    

class BusinessHoursModel(BaseModel):
    weekday: int  # 0=segunda, 6=domingo
    open_time: Optional[str] = None  # formato HH:MM
    close_time: Optional[str] = None  # formato HH:MM
    closed: bool = False
    

class AppointmentModel(BaseModel):
    id: int
    client_id: Optional[int]
    conversation_id: Optional[str]
    procedure_code: str
    date: str
    start_time: str
    end_time: str
    status: str
    google_event_id: Optional[str]
    notes: Optional[str]
    

# ENDPOINTS DE PROCEDURE_CATALOG
@admin_router.get("/procedures", response_model=List[ProcedureModel])
def list_procedures():
    """Lista todos os procedimentos cadastrados."""
    with get_db() as db:
        results = db.execute(
            """
            SELECT code, name, duration_min, active
            FROM procedure_catalog
            ORDER BY name
            """
        ).fetchall()
        
        return [
            ProcedureModel(
                code=r[0],
                name=r[1],
                duration_min=r[2],
                active=r[3]
            )
            for r in results
        ]
        

@admin_router.post("/procedures", response_model=ProcedureModel)
def create_procedure(procedure: ProcedureModel):
    """Cria um novo procedimento."""
    with get_db() as db:
        try:
            db.execute(
                """
                INSERT INTO procedure_catalog (code, name, duration_min, active)
                VALUES (:code, :name, :duration_min, :active)
                """,
                {
                    "code": procedure.code,
                    "name": procedure.name,
                    "duration_min": procedure.duration_min,
                    "active": procedure.active
                }
            )
            db.commit()
            return procedure
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro ao criar procedimento: {str(e)}")
            

@admin_router.put("/procedures/{code}", response_model=ProcedureModel)
def update_procedure(code: str, procedure: ProcedureModel):
    """Atualiza um procedimento existente."""
    with get_db() as db:
        result = db.execute(
            """
            UPDATE procedure_catalog
            SET name = :name,
                duration_min = :duration_min,
                active = :active,
                updated_at = CURRENT_TIMESTAMP
            WHERE code = :code
            RETURNING code
            """,
            {
                "code": code,
                "name": procedure.name,
                "duration_min": procedure.duration_min,
                "active": procedure.active
            }
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Procedimento não encontrado")
            
        db.commit()
        procedure.code = code
        return procedure
        

@admin_router.delete("/procedures/{code}")
def delete_procedure(code: str):
    """Desativa um procedimento (soft delete)."""
    with get_db() as db:
        result = db.execute(
            """
            UPDATE procedure_catalog
            SET active = false,
                updated_at = CURRENT_TIMESTAMP
            WHERE code = :code
            RETURNING code
            """,
            {"code": code}
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Procedimento não encontrado")
            
        db.commit()
        return {"message": f"Procedimento {code} desativado"}
        

# ENDPOINTS DE BUSINESS_HOURS
@admin_router.get("/business-hours", response_model=List[BusinessHoursModel])
def list_business_hours():
    """Lista horários de funcionamento."""
    with get_db() as db:
        results = db.execute(
            """
            SELECT weekday, open_time, close_time, closed
            FROM business_hours
            ORDER BY weekday
            """
        ).fetchall()
        
        return [
            BusinessHoursModel(
                weekday=r[0],
                open_time=r[1].strftime("%H:%M") if r[1] else None,
                close_time=r[2].strftime("%H:%M") if r[2] else None,
                closed=r[3]
            )
            for r in results
        ]
        

@admin_router.put("/business-hours/{weekday}", response_model=BusinessHoursModel)
def update_business_hours(weekday: int, hours: BusinessHoursModel):
    """Atualiza horário de funcionamento para um dia da semana."""
    if weekday < 0 or weekday > 6:
        raise HTTPException(status_code=400, detail="Dia da semana inválido (0-6)")
        
    with get_db() as db:
        # Parse dos horários
        open_time = None
        close_time = None
        
        if hours.open_time and not hours.closed:
            try:
                h, m = hours.open_time.split(":")
                open_time = time(int(h), int(m))
            except:
                raise HTTPException(status_code=400, detail="Formato de horário inválido")
                
        if hours.close_time and not hours.closed:
            try:
                h, m = hours.close_time.split(":")
                close_time = time(int(h), int(m))
            except:
                raise HTTPException(status_code=400, detail="Formato de horário inválido")
                
        # Atualiza ou insere
        result = db.execute(
            """
            UPDATE business_hours
            SET open_time = :open_time,
                close_time = :close_time,
                closed = :closed,
                updated_at = CURRENT_TIMESTAMP
            WHERE weekday = :weekday
            RETURNING id
            """,
            {
                "weekday": weekday,
                "open_time": open_time,
                "close_time": close_time,
                "closed": hours.closed
            }
        ).fetchone()
        
        if not result:
            # Insere se não existe
            db.execute(
                """
                INSERT INTO business_hours (weekday, open_time, close_time, closed)
                VALUES (:weekday, :open_time, :close_time, :closed)
                """,
                {
                    "weekday": weekday,
                    "open_time": open_time,
                    "close_time": close_time,
                    "closed": hours.closed
                }
            )
            
        db.commit()
        hours.weekday = weekday
        return hours
        

# ENDPOINTS DE APPOINTMENTS
@admin_router.get("/appointments", response_model=List[AppointmentModel])
def list_appointments(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None
):
    """Lista agendamentos com filtros opcionais."""
    with get_db() as db:
        query = """
            SELECT 
                a.id, a.client_id, a.conversation_id, a.procedure_code,
                a.date, a.start_time, a.end_time, a.status,
                a.google_event_id, a.notes
            FROM appointments a
            WHERE 1=1
        """
        params = {}
        
        if date_from:
            query += " AND a.date >= :date_from"
            params["date_from"] = date_from
            
        if date_to:
            query += " AND a.date <= :date_to"
            params["date_to"] = date_to
            
        if status:
            query += " AND a.status = :status"
            params["status"] = status
            
        query += " ORDER BY a.date, a.start_time"
        
        results = db.execute(query, params).fetchall()
        
        return [
            AppointmentModel(
                id=r[0],
                client_id=r[1],
                conversation_id=r[2],
                procedure_code=r[3],
                date=r[4].isoformat(),
                start_time=r[5].strftime("%H:%M"),
                end_time=r[6].strftime("%H:%M"),
                status=r[7],
                google_event_id=r[8],
                notes=r[9]
            )
            for r in results
        ]
        

@admin_router.get("/appointments/today")
def list_today_appointments():
    """Lista agendamentos de hoje."""
    today = date.today().isoformat()
    return list_appointments(date_from=today, date_to=today)
    

@admin_router.get("/appointments/stats")
def appointments_stats():
    """Estatísticas de agendamentos."""
    with get_db() as db:
        # Total por status
        status_stats = db.execute(
            """
            SELECT status, COUNT(*) as count
            FROM appointments
            WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY status
            """
        ).fetchall()
        
        # Total por procedimento
        procedure_stats = db.execute(
            """
            SELECT 
                p.name,
                COUNT(a.id) as count
            FROM appointments a
            JOIN procedure_catalog p ON p.code = a.procedure_code
            WHERE a.date >= CURRENT_DATE - INTERVAL '30 days'
              AND a.status = 'confirmed'
            GROUP BY p.name
            ORDER BY count DESC
            """
        ).fetchall()
        
        # Taxa de ocupação
        occupancy = db.execute(
            """
            SELECT 
                DATE_TRUNC('week', date) as week,
                COUNT(*) as appointments,
                COUNT(DISTINCT date) as days_with_appointments
            FROM appointments
            WHERE date >= CURRENT_DATE - INTERVAL '4 weeks'
              AND status = 'confirmed'
            GROUP BY week
            ORDER BY week
            """
        ).fetchall()
        
        return {
            "by_status": {r[0]: r[1] for r in status_stats},
            "by_procedure": {r[0]: r[1] for r in procedure_stats},
            "weekly_occupancy": [
                {
                    "week": r[0].isoformat() if r[0] else None,
                    "appointments": r[1],
                    "days": r[2]
                }
                for r in occupancy
            ]
        }
        

# Adicione o router à aplicação principal em main.py:
# app.include_router(admin_router)