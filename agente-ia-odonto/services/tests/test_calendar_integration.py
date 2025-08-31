"""
services/tests/test_calendar_integration.py
"""

import os
import sys
from datetime import datetime, date, time, timedelta

# Adiciona o diretório services ao path
sys.path.insert(0, '/app')

from services.core.calendar import (
    get_calendar_service,
    parse_date,
    parse_time,
    parse_relative_date,
    format_date_br,
    format_time_br
)
from services.core.database import get_db


def test_connection():
    """Testa conexão com Google Calendar."""
    print("=" * 50)
    print("TESTE 1: Conexão com Google Calendar")
    print("-" * 50)
    
    try:
        service = get_calendar_service()
        client = service.client
        
        if client.test_connection():
            print("✅ Conexão estabelecida com sucesso!")
        else:
            print("❌ Falha na conexão")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False
        
    return True
    

def test_list_slots():
    """Testa listagem de slots disponíveis."""
    print("\n" + "=" * 50)
    print("TESTE 2: Listar Slots Disponíveis")
    print("-" * 50)
    
    try:
        service = get_calendar_service()
        
        # Busca slots para limpeza (30 min) nos próximos 7 dias
        slots = service.list_free_slots(
            duration_min=30,
            limit=5
        )
        
        if slots:
            print(f"✅ Encontrados {len(slots)} slots disponíveis:")
            for i, slot in enumerate(slots, 1):
                print(f"   {i}. {slot['formatted']} ({slot['weekday']})")
        else:
            print("⚠️ Nenhum slot disponível encontrado")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False
        
    return True
    

def test_time_parsing():
    """Testa parsing de datas e horários."""
    print("\n" + "=" * 50)
    print("TESTE 3: Parsing de Datas e Horários")
    print("-" * 50)
    
    test_cases = [
        # Datas
        ("31/12/2024", "31/12/2024"),
        ("15/08", f"15/08/{datetime.now().year}"),
        ("amanhã", format_date_br(date.today() + timedelta(days=1))),
        ("segunda-feira", "próxima segunda"),
        
        # Horários
        ("14:30", "14:30"),
        ("9:00", "09:00"),
        ("15h30", "15:30"),
        ("10", "10:00"),
    ]
    
    print("Datas:")
    for input_str, expected in test_cases[:4]:
        if input_str == "segunda-feira":
            result = parse_relative_date(input_str)
            if result:
                print(f"  '{input_str}' → {format_date_br(result)} ✅")
            else:
                print(f"  '{input_str}' → Erro ❌")
        else:
            result = parse_date(input_str) or parse_relative_date(input_str)
            if result:
                formatted = format_date_br(result)
                print(f"  '{input_str}' → {formatted} ✅")
            else:
                print(f"  '{input_str}' → Erro ❌")
                
    print("\nHorários:")
    for input_str, expected in test_cases[4:]:
        result = parse_time(input_str)
        if result:
            formatted = format_time_br(result)
            print(f"  '{input_str}' → {formatted} ✅")
        else:
            print(f"  '{input_str}' → Erro ❌")
            
    return True
    

def test_create_event():
    """Testa criação de evento no calendário."""
    print("\n" + "=" * 50)
    print("TESTE 4: Criar Evento de Teste")
    print("-" * 50)
    
    try:
        service = get_calendar_service()
        
        # Data e horário de teste (amanhã às 14h)
        test_date = date.today() + timedelta(days=1)
        test_start = time(14, 0)
        test_end = time(14, 30)
        
        print(f"Criando evento de teste:")
        print(f"  Data: {format_date_br(test_date)}")
        print(f"  Horário: {format_time_br(test_start)} - {format_time_br(test_end)}")
        
        event_id = service.create_event(
            client_name="TESTE - Pedro Silva",
            procedure_name="TESTE - Consulta",
            event_date=test_date,
            start_time=test_start,
            end_time=test_end,
            client_phone="11999999999",
            notes="Este é um evento de teste. Pode ser deletado.",
            client_id=999999  # ID fictício para teste
        )
        
        if event_id:
            print(f"✅ Evento criado com sucesso!")
            print(f"   ID: {event_id}")
            
            # Aguarda 2 segundos
            import time as time_module
            time_module.sleep(2)
            
            # Tenta cancelar o evento
            print("\nCancelando evento de teste...")
            if service.cancel_event(event_id):
                print("✅ Evento cancelado com sucesso!")
            else:
                print("⚠️ Não foi possível cancelar o evento de teste")
                
        else:
            print("❌ Falha ao criar evento")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False
        
    return True
    

def test_database_seed():
    """Verifica se o seed do banco foi executado."""
    print("\n" + "=" * 50)
    print("TESTE 5: Verificar Seed do Banco")
    print("-" * 50)
    
    try:
        with get_db() as db:
            # Verifica procedimentos
            procedures = db.execute(
                "SELECT code, name, duration_min FROM procedure_catalog WHERE active = true ORDER BY name"
            ).fetchall()
            
            print(f"Procedimentos cadastrados: {len(procedures)}")
            for proc in procedures[:5]:  # Mostra apenas os 5 primeiros
                print(f"  • {proc[1]} ({proc[0]}): {proc[2]} min")
                
            # Verifica horários de funcionamento
            hours = db.execute(
                "SELECT weekday, open_time, close_time, closed FROM business_hours ORDER BY weekday"
            ).fetchall()
            
            print(f"\nHorários de funcionamento:")
            weekdays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            for h in hours:
                day = weekdays[h[0]]
                if h[3]:  # closed
                    print(f"  {day}: FECHADO")
                else:
                    open_time = h[1].strftime("%H:%M") if h[1] else "?"
                    close_time = h[2].strftime("%H:%M") if h[2] else "?"
                    print(f"  {day}: {open_time} - {close_time}")
                    
        print("\n✅ Dados do banco verificados com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False
        
    return True
    

def main():
    """Executa todos os testes."""
    print("\n" + "🏥 TESTES DE INTEGRAÇÃO - GOOGLE CALENDAR " + "🏥")
    print("=" * 50)
    
    tests = [
        test_connection,
        test_list_slots,
        test_time_parsing,
        test_create_event,
        test_database_seed
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ Teste {test.__name__} falhou com exceção: {str(e)}")
            failed += 1
            
    print("\n" + "=" * 50)
    print("RESUMO DOS TESTES")
    print("-" * 50)
    print(f"✅ Passou: {passed}")
    print(f"❌ Falhou: {failed}")
    print(f"📊 Taxa de sucesso: {(passed/(passed+failed)*100):.1f}%")
    print("=" * 50)
    
    return failed == 0
    

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)