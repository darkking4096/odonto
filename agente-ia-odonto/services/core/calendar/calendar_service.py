"""
services/core/calendar/calendar_service.py
"""

import os
import hashlib
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import select, and_
from googleapiclient.errors import HttpError

from services.core.database import get_db
from services.core.calendar.google_client import get_calendar_client
from services.core.calendar.timeutils import (
    parse_date, parse_time, combine_datetime_tz,
    get_timezone, format_time_br, get_weekday,
    parse_window
)


class CalendarService:
    """Serviço para gerenciar disponibilidade e agendamentos."""
    
    def __init__(self):
        """Inicializa o serviço de calendário."""
        self.client = get_calendar_client()
        self.service = self.client.get_service()
        self.calendar_id = self.client.calendar_id
        self.timezone = get_timezone()
        self.slot_minutes = int(os.getenv("DEFAULT_SLOT_MINUTES", "30"))
        self.lookahead_days = int(os.getenv("AVAIL_LOOKAHEAD_DAYS", "14"))
        
    def list_free_slots(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        duration_min: int = 30,
        window: Optional[str] = None,
        limit: int = 3
    ) -> List[Dict]:
        """
        Lista slots livres disponíveis para agendamento.
        
        Args:
            date_from: Data inicial (default: hoje)
            date_to: Data final (default: hoje + lookahead_days)
            duration_min: Duração do procedimento em minutos
            window: Janela preferida (manhã/tarde/noite)
            limit: Número máximo de slots a retornar
            
        Returns:
            Lista de dicionários com slots disponíveis
        """
        # Define período de busca
        if not date_from:
            date_from = datetime.now(self.timezone).date()
        if not date_to:
            date_to = date_from + timedelta(days=self.lookahead_days)
            
        # Parse da janela preferida
        window_start, window_end = parse_window(window)
        
        slots = []
        current_date = date_from
        
        # Itera por cada dia no período
        while current_date <= date_to and len(slots) < limit:
            # Verifica se a clínica abre neste dia
            business_hours = self._get_business_hours(current_date)
            
            if not business_hours or business_hours['closed']:
                current_date += timedelta(days=1)
                continue
                
            # Busca eventos existentes no dia
            busy_times = self._get_busy_times(current_date)
            
            # Gera slots livres para o dia
            day_slots = self._generate_day_slots(
                current_date,
                business_hours,
                busy_times,
                duration_min,
                window_start,
                window_end
            )
            
            # Adiciona slots até o limite
            for slot in day_slots:
                if len(slots) >= limit:
                    break
                slots.append(slot)
                
            current_date += timedelta(days=1)
            
        return slots
        
    def _get_business_hours(self, check_date: date) -> Optional[Dict]:
        """Busca horário de funcionamento para uma data."""
        weekday = check_date.weekday()  # 0=segunda, 6=domingo
        
        with get_db() as db:
            # Busca horário para o dia da semana
            result = db.execute(
                """
                SELECT open_time, close_time, closed
                FROM business_hours
                WHERE weekday = :weekday
                """,
                {"weekday": weekday}
            ).fetchone()
            
            if not result:
                return None
                
            return {
                'open_time': result[0],
                'close_time': result[1],
                'closed': result[2]
            }
            
    def _get_busy_times(self, check_date: date) -> List[Tuple[time, time]]:
        """Busca horários ocupados no Google Calendar para uma data."""
        busy = []
        
        try:
            # Define intervalo do dia inteiro
            time_min = combine_datetime_tz(check_date, time(0, 0), self.timezone)
            time_max = combine_datetime_tz(check_date, time(23, 59), self.timezone)
            
            # Busca eventos no Google Calendar
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            for event in events:
                # Ignora eventos cancelados
                if event.get('status') == 'cancelled':
                    continue
                    
                # Parse dos horários
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                if start and end:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    
                    # Converte para timezone local
                    start_local = start_dt.astimezone(self.timezone)
                    end_local = end_dt.astimezone(self.timezone)
                    
                    # Adiciona à lista de ocupados
                    busy.append((start_local.time(), end_local.time()))
                    
        except HttpError as e:
            print(f"Erro ao buscar eventos: {e}")
            
        return busy
        
    def _generate_day_slots(
        self,
        check_date: date,
        business_hours: Dict,
        busy_times: List[Tuple[time, time]],
        duration_min: int,
        window_start: Optional[time],
        window_end: Optional[time]
    ) -> List[Dict]:
        """Gera slots livres para um dia específico."""
        slots = []
        
        # Define horário de abertura e fechamento
        open_time = business_hours['open_time']
        close_time = business_hours['close_time']
        
        # Aplica janela preferida se especificada
        if window_start and window_start > open_time:
            open_time = window_start
        if window_end and window_end < close_time:
            close_time = window_end
            
        # Converte para minutos para facilitar cálculos
        open_minutes = open_time.hour * 60 + open_time.minute
        close_minutes = close_time.hour * 60 + close_time.minute
        
        # Itera em incrementos de slot_minutes
        current_minutes = open_minutes
        
        while current_minutes + duration_min <= close_minutes:
            # Converte minutos de volta para time
            start_hour = current_minutes // 60
            start_minute = current_minutes % 60
            start_time = time(start_hour, start_minute)
            
            end_minutes = current_minutes + duration_min
            end_hour = end_minutes // 60
            end_minute = end_minutes % 60
            end_time = time(end_hour, end_minute)
            
            # Verifica se o slot está livre
            is_free = True
            for busy_start, busy_end in busy_times:
                # Verifica sobreposição
                if not (end_time <= busy_start or start_time >= busy_end):
                    is_free = False
                    break
                    
            if is_free:
                # Adiciona slot disponível
                slots.append({
                    'date': check_date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'formatted': f"{check_date.strftime('%d/%m')} às {format_time_br(start_time)}",
                    'weekday': get_weekday(check_date)
                })
                
            # Avança para próximo slot
            current_minutes += self.slot_minutes
            
        return slots
        
    def create_event(
        self,
        client_name: str,
        procedure_name: str,
        event_date: date,
        start_time: time,
        end_time: time,
        client_phone: Optional[str] = None,
        notes: Optional[str] = None,
        client_id: Optional[int] = None
    ) -> str:
        """
        Cria um evento no Google Calendar.
        
        Args:
            client_name: Nome do cliente
            procedure_name: Nome do procedimento
            event_date: Data do evento
            start_time: Hora de início
            end_time: Hora de término
            client_phone: Telefone do cliente (opcional)
            notes: Observações (opcional)
            client_id: ID do cliente para idempotência (opcional)
            
        Returns:
            ID do evento criado no Google Calendar
        """
        # Monta o evento
        summary = f"{procedure_name} - {client_name}"
        description = f"Cliente: {client_name}\nProcedimento: {procedure_name}"
        
        if client_phone:
            description += f"\nTelefone: {client_phone}"
        if notes:
            description += f"\n\nObservações: {notes}"
            
        # Converte para datetime com timezone
        start_datetime = combine_datetime_tz(event_date, start_time, self.timezone)
        end_datetime = combine_datetime_tz(event_date, end_time, self.timezone)
        
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': str(self.timezone),
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': str(self.timezone),
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 24 * 60},  # 1 dia antes
                    {'method': 'popup', 'minutes': 60},       # 1 hora antes
                ],
            },
        }
        
        # Request ID para idempotência (evita duplicatas)
        if client_id:
            request_id = self._generate_request_id(
                client_id, event_date, start_time, procedure_name
            )
        else:
            request_id = None
            
        try:
            # Cria o evento
            if request_id:
                event_result = self.service.events().insert(
                    calendarId=self.calendar_id,
                    body=event,
                    sendNotifications=False,
                    requestId=request_id
                ).execute()
            else:
                event_result = self.service.events().insert(
                    calendarId=self.calendar_id,
                    body=event,
                    sendNotifications=False
                ).execute()
                
            return event_result.get('id')
            
        except HttpError as e:
            if e.resp.status == 409:
                # Evento já existe (idempotência)
                print(f"Evento já existe com request_id: {request_id}")
                # Tenta buscar o evento existente
                return self._find_existing_event(
                    event_date, start_time, client_name, procedure_name
                )
            raise
            
    def _generate_request_id(
        self,
        client_id: int,
        event_date: date,
        start_time: time,
        procedure: str
    ) -> str:
        """Gera um request ID determinístico para idempotência."""
        data = f"{client_id}-{event_date}-{start_time}-{procedure}"
        return hashlib.md5(data.encode()).hexdigest()
        
    def _find_existing_event(
        self,
        event_date: date,
        start_time: time,
        client_name: str,
        procedure_name: str
    ) -> Optional[str]:
        """Busca um evento existente pelos parâmetros."""
        time_min = combine_datetime_tz(event_date, start_time, self.timezone)
        time_max = time_min + timedelta(minutes=5)  # Pequena janela
        
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                q=f"{procedure_name} {client_name}",
                singleEvents=True
            ).execute()
            
            events = events_result.get('items', [])
            if events:
                return events[0].get('id')
                
        except HttpError:
            pass
            
        return None
        
    def update_event(
        self,
        google_event_id: str,
        new_date: Optional[date] = None,
        new_start_time: Optional[time] = None,
        new_end_time: Optional[time] = None,
        new_notes: Optional[str] = None
    ) -> bool:
        """
        Atualiza um evento existente no Google Calendar.
        
        Args:
            google_event_id: ID do evento no Google Calendar
            new_date: Nova data (opcional)
            new_start_time: Novo horário de início (opcional)
            new_end_time: Novo horário de término (opcional)
            new_notes: Novas observações (opcional)
            
        Returns:
            True se atualizado com sucesso
        """
        try:
            # Busca evento atual
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=google_event_id
            ).execute()
            
            # Atualiza campos conforme necessário
            if new_date and new_start_time and new_end_time:
                start_datetime = combine_datetime_tz(new_date, new_start_time, self.timezone)
                end_datetime = combine_datetime_tz(new_date, new_end_time, self.timezone)
                
                event['start'] = {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': str(self.timezone),
                }
                event['end'] = {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': str(self.timezone),
                }
                
            if new_notes:
                current_desc = event.get('description', '')
                # Preserva informações do cliente e adiciona novas observações
                if '\n\nObservações:' in current_desc:
                    base_desc = current_desc.split('\n\nObservações:')[0]
                    event['description'] = f"{base_desc}\n\nObservações: {new_notes}"
                else:
                    event['description'] = f"{current_desc}\n\nObservações: {new_notes}"
                    
            # Atualiza o evento
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=google_event_id,
                body=event
            ).execute()
            
            return True
            
        except HttpError as e:
            print(f"Erro ao atualizar evento: {e}")
            return False
            
    def cancel_event(self, google_event_id: str) -> bool:
        """
        Cancela (deleta) um evento no Google Calendar.
        
        Args:
            google_event_id: ID do evento no Google Calendar
            
        Returns:
            True se cancelado com sucesso
        """
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=google_event_id,
                sendNotifications=False
            ).execute()
            
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                print(f"Evento não encontrado: {google_event_id}")
                return True  # Considera sucesso se já não existe
            print(f"Erro ao cancelar evento: {e}")
            return False
            
            
# Singleton
_service_instance = None

def get_calendar_service() -> CalendarService:
    """Retorna instância singleton do serviço de calendário."""
    global _service_instance
    if _service_instance is None:
        _service_instance = CalendarService()
    return _service_instance