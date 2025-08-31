#!/usr/bin/env python3
"""
setup_calendar.py - Script de configuração do Google Calendar
"""

import os
import sys
import json
from pathlib import Path


def check_credentials():
    """Verifica se as credenciais existem."""
    cred_path = Path("secrets/google-credentials.json")
    
    if not cred_path.exists():
        print("❌ Arquivo de credenciais não encontrado!")
        print(f"   Esperado em: {cred_path.absolute()}")
        return False
        
    # Verificar se é um JSON válido
    try:
        with open(cred_path, 'r') as f:
            data = json.load(f)
            
        # Verificar campos essenciais
        required_fields = ['type', 'project_id', 'client_email']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            print(f"❌ Credenciais incompletas. Faltando: {', '.join(missing)}")
            return False
            
        # Verificar tipo de credencial
        if data['type'] != 'service_account':
            print(f"⚠️  Tipo de credencial: {data['type']} (esperado: service_account)")
            
        print("✅ Arquivo de credenciais válido!")
        print(f"   Project ID: {data['project_id']}")
        print(f"   Service Account: {data['client_email']}")
        print()
        print("📋 PRÓXIMOS PASSOS:")
        print(f"1. Compartilhe seu calendário com: {data['client_email']}")
        print("2. Dê permissão: 'Fazer alterações em eventos'")
        print("3. Configure GOOGLE_CALENDAR_ID no .env (ou use 'primary')")
        
        return True
        
    except json.JSONDecodeError:
        print("❌ Arquivo de credenciais inválido (não é um JSON válido)")
        return False
    except Exception as e:
        print(f"❌ Erro ao ler credenciais: {str(e)}")
        return False


def create_env_file():
    """Cria arquivo .env baseado no exemplo."""
    if Path(".env").exists():
        print("ℹ️  Arquivo .env já existe")
        return
        
    if not Path(".env.example").exists():
        print("⚠️  Arquivo .env.example não encontrado")
        return
        
    print("📝 Criando arquivo .env...")
    
    # Copiar .env.example para .env
    with open(".env.example", 'r') as src:
        with open(".env", 'w') as dst:
            dst.write(src.read())
            
    print("✅ Arquivo .env criado! Configure as variáveis necessárias.")


def test_connection():
    """Testa a conexão com o Google Calendar."""
    print("\n🔍 Testando conexão com Google Calendar...")
    
    try:
        # Importar apenas se o ambiente estiver configurado
        sys.path.insert(0, 'services')
        from services.core.calendar import get_calendar_client
        
        client = get_calendar_client()
        if client.test_connection():
            print("✅ Conexão estabelecida com sucesso!")
            return True
        else:
            print("❌ Falha na conexão")
            return False
            
    except ImportError as e:
        print(f"⚠️  Dependências não instaladas: {str(e)}")
        print("   Execute: pip install google-auth google-auth-oauthlib google-api-python-client")
        return False
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False


def main():
    """Função principal."""
    print("🏥 CONFIGURAÇÃO DO GOOGLE CALENDAR - ODONTO IA")
    print("=" * 50)
    print()
    
    # 1. Criar diretório secrets se não existir
    Path("secrets").mkdir(exist_ok=True)
    
    # 2. Verificar credenciais
    print("📁 Verificando credenciais...")
    if not check_credentials():
        print()
        print("📚 COMO OBTER CREDENCIAIS:")
        print("-" * 30)
        print("1. Acesse: https://console.cloud.google.com")
        print("2. Crie um novo projeto (ou use existente)")
        print("3. Vá para 'APIs & Services' > 'Library'")
        print("4. Busque e ative: 'Google Calendar API'")
        print("5. Vá para 'APIs & Services' > 'Credentials'")
        print("6. Clique em 'Create Credentials' > 'Service Account'")
        print("7. Preencha o nome (ex: odonto-calendar)")
        print("8. Clique em 'Create and Continue' > 'Done'")
        print("9. Clique na Service Account criada")
        print("10. Vá para aba 'Keys' > 'Add Key' > 'Create new key'")
        print("11. Escolha 'JSON' e baixe o arquivo")
        print("12. Salve como: secrets/google-credentials.json")
        print()
        return
        
    # 3. Criar .env se não existir
    create_env_file()
    
    # 4. Perguntar se quer testar a conexão
    print()
    response = input("Deseja testar a conexão agora? (s/n): ").lower()
    if response == 's':
        test_connection()
        
    print()
    print("✨ Configuração concluída!")
    print()
    print("PRÓXIMOS COMANDOS:")
    print("-" * 30)
    print("make up           # Iniciar serviços")
    print("make migrate      # Executar migrações")
    print("make test-calendar # Testar calendário")
    print("make help         # Ver todos os comandos")


if __name__ == "__main__":
    main()