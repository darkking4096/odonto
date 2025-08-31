"""
Script de teste para validar a Etapa 4
"""
import os
import sys
from datetime import datetime, date, time
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def test_ai_providers():
    """Testa os providers de IA"""
    print("\n=== TESTANDO PROVIDERS DE IA ===")
    
    from ai.factory import AIFactory
    
    provider = AIFactory.create_provider()
    if provider:
        print(f"✅ Provider configurado: {provider.__class__.__name__}")
        
        # Teste simples
        response = provider.generate(
            system_prompt="Você é um assistente de teste. Responda em 5 palavras.",
            user_prompt="Olá, tudo bem?",
            temperature=0.3,
            max_tokens=20
        )
        print(f"✅ Resposta do provider: {response}")
    else:
        print("❌ Nenhum provider configurado")
    
    return provider is not None


def test_extractors():
    """Testa os extratores de dados"""
    print("\n=== TESTANDO EXTRATORES ===")
    
    from stages.extractors import DataExtractor
    extractor = DataExtractor()
    
    # Casos de teste
    test_cases = [
        ("Oi, sou a Maria Silva", "nome"),
        ("Quero marcar uma limpeza", "procedimento"),
        ("Pode ser amanhã de manhã", "data e janela"),
        ("Prefiro às 14:30", "horário"),
        ("Terça-feira à tarde seria bom", "dia da semana e janela")
    ]
    
    for text, expected in test_cases:
        result = extractor.extract_all(text)
        if result:
            print(f"✅ '{text}' → {result}")
        else:
            print(f"⚠️  '{text}' → Nada extraído (esperado: {expected})")
    
    return True


def test_validators():
    """Testa os validadores"""
    print("\n=== TESTANDO VALIDADORES ===")
    
    from stages.validators import DataValidator
    validator = DataValidator()
    
    # Casos de teste
    test_data = {
        "full_name": "maria silva",
        "procedure": "limpeza",
        "desired_time": time(14, 30),
        "desired_window": "tarde"
    }
    
    validated = validator.validate_all(test_data)
    
    for key, value in validated.items():
        original = test_data.get(key)
        print(f"✅ {key}: {original} → {value}")
    
    # Testar caso inválido
    invalid_data = {
        "procedure": "botox",  # Inválido
        "desired_time": time(23, 0)  # Fora do horário
    }
    
    invalid_validated = validator.validate_all(invalid_data)
    if not invalid_validated.get("procedure"):
        print("✅ Procedimento inválido rejeitado")
    if not invalid_validated.get("desired_time"):
        print("✅ Horário inválido rejeitado")
    
    return True


def test_database():
    """Testa conexão com banco"""
    print("\n=== TESTANDO BANCO DE DADOS ===")
    
    from database import test_connection, get_db
    from models import Client, StagePrompt
    
    if test_connection():
        print("✅ Conexão com banco OK")
        
        # Verificar tabelas
        db = next(get_db())
        try:
            # Contar registros
            clients = db.query(Client).count()
            prompts = db.query(StagePrompt).count()
            
            print(f"✅ Tabela clients: {clients} registros")
            print(f"✅ Tabela stage_prompt: {prompts} prompts")
            
            if prompts == 0:
                print("⚠️  Sem prompts no banco. Execute: alembic upgrade head")
            
            return True
        finally:
            db.close()
    else:
        print("❌ Falha na conexão com banco")
        return False


def test_stage_engine():
    """Testa o engine de estágios"""
    print("\n=== TESTANDO ENGINE DE ESTÁGIOS ===")
    
    from database import get_db
    from stages.engine import StageEngine
    from models import Client
    
    db = next(get_db())
    try:
        # Criar cliente de teste
        test_phone = "5511999999999"
        client = db.query(Client).filter_by(phone=test_phone).first()
        if not client:
            client = Client(
                phone=test_phone,
                name="Teste",
                created_at=datetime.utcnow()
            )
            db.add(client)
            db.commit()
            print(f"✅ Cliente de teste criado: ID {client.id}")
        
        # Testar engine
        engine = StageEngine(db)
        
        # Simular conversa
        messages = [
            "Oi, quero marcar consulta",
            "Sou o João Teste",
            "Limpeza dental",
            "Amanhã de manhã"
        ]
        
        for msg in messages:
            response = engine.handle(client.id, msg)
            print(f"👤 Cliente: {msg}")
            print(f"🤖 Bot: {response[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no engine: {str(e)}")
        return False
    finally:
        db.close()


def main():
    """Executa todos os testes"""
    print("=" * 50)
    print("TESTE DA ETAPA 4 - IA + MÁQUINA DE ESTADOS")
    print("=" * 50)
    
    results = []
    
    # Executar testes
    results.append(("Banco de dados", test_database()))
    results.append(("Providers de IA", test_ai_providers()))
    results.append(("Extratores", test_extractors()))
    results.append(("Validadores", test_validators()))
    results.append(("Engine de estágios", test_stage_engine()))
    
    # Resumo
    print("\n" + "=" * 50)
    print("RESUMO DOS TESTES")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    # Verificar se todos passaram
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 TODOS OS TESTES PASSARAM! A Etapa 4 está funcionando.")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os logs acima.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())