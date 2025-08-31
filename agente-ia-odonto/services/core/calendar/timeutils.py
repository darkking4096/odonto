"""
services/core/calendar/timeutils.py
"""

import os
from datetime import datetime, date, time, timedelta
from typing import Optional, Tuple
import pytz


def get_timezone():
    """Retorna o timezone configurado."""
    tz_name = os.getenv("CLINIC_TIMEZONE", "America/Sao_Paulo")
    return pytz.timezone(tz_name)
    

def parse_date(date_str: str) -> Optional[date]:
    """
    Parse de string de data em vários formatos.
    
    Formatos aceitos:
    - DD/MM/YYYY
    - DD/MM/YY
    - DD/MM
    - YYYY-MM-DD
    """
    if not date_str:
        return None
        
    # Remove espaços
    date_str = date_str.strip()
    
    # Tenta diferentes formatos
    formats = [
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d/%m",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d-%m-%y"
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            
            # Se não tem ano, usa o ano atual
            if fmt in ["%d/%m", "%d-%m"]:
                current_year = datetime.now().year
                parsed = parsed.replace(year=current_year)
                
                # Se a data já passou, usa próximo ano
                if parsed.date() < datetime.now().date():
                    parsed = parsed.replace(year=current_year + 1)
                    
            return parsed.date()
        except ValueError:
            continue
            
    return None
    

def parse_time(time_str: str) -> Optional[time]:
    """
    Parse de string de horário.
    
    Formatos aceitos:
    - HH:MM
    - HH:MM:SS
    - HHhMM
    - HH h MM
    """
    if not time_str:
        return None
        
    # Remove espaços extras e normaliza
    time_str = time_str.strip().lower()
    time_str = time_str.replace('h', ':').replace(' ', '')
    
    # Remove "hs" ou "hrs" do final
    time_str = time_str.replace('hs', '').replace('hrs', '').replace('hr', '')
    
    # Tenta parse
    formats = [
        "%H:%M:%S",
        "%H:%M",
        "%H%M"
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(time_str, fmt)
            return parsed.time()
        except ValueError:
            continue
            
    # Tenta parse simplificado (só hora)
    try:
        hour = int(time_str)
        if 0 <= hour <= 23:
            return time(hour, 0)
    except ValueError:
        pass
        
    return None
    

def combine_datetime_tz(date_obj: date, time_obj: time, timezone) -> datetime:
    """Combina data e hora com timezone."""
    dt = datetime.combine(date_obj, time_obj)
    return timezone.localize(dt)
    

def format_time_br(time_obj: time) -> str:
    """Formata horário no padrão brasileiro."""
    return time_obj.strftime("%H:%M")
    

def format_date_br(date_obj: date) -> str:
    """Formata data no padrão brasileiro."""
    return date_obj.strftime("%d/%m/%Y")
    

def get_weekday(date_obj: date) -> str:
    """Retorna o nome do dia da semana em português."""
    weekdays = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
        "Domingo"
    ]
    return weekdays[date_obj.weekday()]
    

def parse_window(window: Optional[str]) -> Tuple[Optional[time], Optional[time]]:
    """
    Parse de janela de horário preferida.
    
    Args:
        window: "manhã", "tarde", "noite" ou None
        
    Returns:
        Tupla (início, fim) ou (None, None)
    """
    if not window:
        return (None, None)
        
    window = window.lower().strip()
    
    # Lê configurações do ambiente
    if window in ["manhã", "manha"]:
        config = os.getenv("WINDOW_MANHA", "08:00-12:00")
    elif window == "tarde":
        config = os.getenv("WINDOW_TARDE", "12:00-18:00")
    elif window == "noite":
        config = os.getenv("WINDOW_NOITE", "18:00-21:00")
    else:
        return (None, None)
        
    # Parse da configuração
    try:
        parts = config.split('-')
        if len(parts) == 2:
            start = parse_time(parts[0])
            end = parse_time(parts[1])
            return (start, end)
    except:
        pass
        
    return (None, None)
    

def is_business_day(date_obj: date) -> bool:
    """Verifica se é dia útil (segunda a sábado)."""
    return date_obj.weekday() < 6  # 0=segunda, 5=sábado
    

def next_business_day(date_obj: date) -> date:
    """Retorna o próximo dia útil."""
    next_day = date_obj + timedelta(days=1)
    while not is_business_day(next_day):
        next_day += timedelta(days=1)
    return next_day
    

def parse_relative_date(text: str) -> Optional[date]:
    """
    Parse de datas relativas em português.
    
    Exemplos:
    - "hoje"
    - "amanhã"
    - "depois de amanhã"
    - "segunda-feira"
    - "próxima terça"
    """
    text = text.lower().strip()
    today = datetime.now().date()
    
    # Datas relativas simples
    if text in ["hoje", "hj"]:
        return today
    elif text in ["amanhã", "amanha"]:
        return today + timedelta(days=1)
    elif text in ["depois de amanhã", "depois de amanha"]:
        return today + timedelta(days=2)
        
    # Dias da semana
    weekday_map = {
        "segunda": 0, "segunda-feira": 0, "seg": 0,
        "terça": 1, "terça-feira": 1, "terca": 1, "ter": 1,
        "quarta": 2, "quarta-feira": 2, "qua": 2,
        "quinta": 3, "quinta-feira": 3, "qui": 3,
        "sexta": 4, "sexta-feira": 4, "sex": 4,
        "sábado": 5, "sabado": 5, "sab": 5,
        "domingo": 6, "dom": 6
    }
    
    # Remove "próxima" ou "próximo"
    text = text.replace("próxima", "").replace("próximo", "").replace("proxima", "").replace("proximo", "").strip()
    
    if text in weekday_map:
        target_weekday = weekday_map[text]
        current_weekday = today.weekday()
        
        # Calcula dias até o próximo dia da semana
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0:  # Já passou esta semana
            days_ahead += 7
            
        return today + timedelta(days=days_ahead)
        
    return None