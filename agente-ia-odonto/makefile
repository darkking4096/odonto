# Makefile - ETAPA 5
# Comandos úteis para desenvolvimento e operação

.PHONY: help build up down logs test migrate clean backup restore

# Variáveis
COMPOSE = docker-compose
API_CONTAINER = odonto-api
DB_CONTAINER = odonto-db
DB_NAME = odonto_db
DB_USER = odonto

# Cores para output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
NC = \033[0m # No Color

help: ## Mostra esta mensagem de ajuda
	@echo "$(GREEN)Comandos disponíveis:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

# ========== DOCKER ==========

build: ## Constrói as imagens Docker
	@echo "$(GREEN)Construindo imagens...$(NC)"
	$(COMPOSE) build

up: ## Inicia todos os serviços
	@echo "$(GREEN)Iniciando serviços...$(NC)"
	$(COMPOSE) up -d
	@echo "$(GREEN)Serviços iniciados!$(NC)"
	@echo "API: http://localhost:8000"
	@echo "Evolution: http://localhost:8080"
	@echo "PgAdmin: http://localhost:8090 (perfil dev)"

down: ## Para todos os serviços
	@echo "$(YELLOW)Parando serviços...$(NC)"
	$(COMPOSE) down

restart: ## Reinicia todos os serviços
	@echo "$(YELLOW)Reiniciando serviços...$(NC)"
	$(COMPOSE) restart

logs: ## Mostra logs dos serviços
	$(COMPOSE) logs -f

logs-api: ## Mostra logs apenas da API
	$(COMPOSE) logs -f api

ps: ## Lista status dos containers
	$(COMPOSE) ps

# ========== DESENVOLVIMENTO ==========

dev: ## Inicia em modo desenvolvimento com pgAdmin
	@echo "$(GREEN)Iniciando em modo desenvolvimento...$(NC)"
	$(COMPOSE) --profile dev up -d
	@echo "$(GREEN)Modo dev ativado!$(NC)"
	@echo "PgAdmin: http://localhost:8090"
	@echo "Login: admin@odonto.local / admin123"

shell: ## Acessa shell do container da API
	$(COMPOSE) exec api bash

shell-db: ## Acessa psql no banco
	$(COMPOSE) exec db psql -U $(DB_USER) -d $(DB_NAME)

python: ## Acessa Python interativo no container
	$(COMPOSE) exec api python

# ========== BANCO DE DADOS ==========

migrate: ## Executa migrações do banco
	@echo "$(GREEN)Executando migrações...$(NC)"
	$(COMPOSE) exec api alembic upgrade head
	@echo "$(GREEN)Migrações aplicadas!$(NC)"

migrate-down: ## Reverte última migração
	@echo "$(YELLOW)Revertendo última migração...$(NC)"
	$(COMPOSE) exec api alembic downgrade -1

migrate-create: ## Cria nova migração (use: make migrate-create NAME=nome_da_migracao)
	$(COMPOSE) exec api alembic revision -m "$(NAME)"

db-reset: ## Reseta o banco (CUIDADO!)
	@echo "$(RED)ATENÇÃO: Isso apagará todos os dados!$(NC)"
	@echo "Pressione Ctrl+C para cancelar ou Enter para continuar..."
	@read confirm
	$(COMPOSE) exec db psql -U $(DB_USER) -c "DROP DATABASE IF EXISTS $(DB_NAME);"
	$(COMPOSE) exec db psql -U $(DB_USER) -c "CREATE DATABASE $(DB_NAME);"
	$(MAKE) migrate
	@echo "$(GREEN)Banco resetado!$(NC)"

backup: ## Faz backup do banco
	@echo "$(GREEN)Criando backup...$(NC)"
	@mkdir -p backups
	$(COMPOSE) exec db pg_dump -U $(DB_USER) $(DB_NAME) > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup criado em backups/$(NC)"

restore: ## Restaura backup (use: make restore FILE=backup_20240101_120000.sql)
	@echo "$(YELLOW)Restaurando backup...$(NC)"
	$(COMPOSE) exec -T db psql -U $(DB_USER) $(DB_NAME) < backups/$(FILE)
	@echo "$(GREEN)Backup restaurado!$(NC)"

# ========== TESTES ==========

test: ## Executa testes
	@echo "$(GREEN)Executando testes...$(NC)"
	$(COMPOSE) exec api python -m pytest tests/ -v

test-calendar: ## Testa integração com Google Calendar
	@echo "$(GREEN)Testando Google Calendar...$(NC)"
	$(COMPOSE) exec api python tests/test_calendar_integration.py

test-message: ## Envia mensagem de teste (use: make test-message MSG="sua mensagem")
	@echo "$(GREEN)Enviando mensagem de teste...$(NC)"
	@MSG="$${MSG:-Oi, quero agendar uma consulta}"; \
	curl -X POST http://localhost:8000/test/message \
		-H "Content-Type: application/json" \
		-d "{\"phone\": \"5511999999999\", \"message\": \"$$MSG\"}" | python -m json.tool

# ========== GOOGLE CALENDAR ==========

calendar-test: ## Testa conexão com Google Calendar
	@echo "$(GREEN)Testando conexão com Google Calendar...$(NC)"
	@curl -s http://localhost:8000/test/calendar | python -m json.tool

calendar-setup: ## Ajuda na configuração do Google Calendar
	@echo "$(GREEN)=== CONFIGURAÇÃO DO GOOGLE CALENDAR ===$(NC)"
	@echo ""
	@echo "1. Acesse: https://console.cloud.google.com"
	@echo "2. Crie um projeto ou selecione existente"
	@echo "3. Ative a API: Google Calendar API"
	@echo "4. Crie credenciais: Service Account"
	@echo "5. Baixe o JSON e salve como: secrets/google-credentials.json"
	@echo "6. Copie o email da Service Account"
	@echo "7. No Google Calendar, compartilhe com esse email"
	@echo "8. Dê permissão: 'Fazer alterações em eventos'"
	@echo ""
	@echo "$(YELLOW)Arquivo esperado em: ./secrets/google-credentials.json$(NC)"
	@if [ -f ./secrets/google-credentials.json ]; then \
		echo "$(GREEN)✓ Arquivo encontrado!$(NC)"; \
	else \
		echo "$(RED)✗ Arquivo não encontrado$(NC)"; \
	fi

# ========== ESTATÍSTICAS ==========

stats: ## Mostra estatísticas do sistema
	@echo "$(GREEN)=== ESTATÍSTICAS DO SISTEMA ===$(NC)"
	@echo ""
	@echo "Conversas:"
	@curl -s http://localhost:8000/stats/conversations | python -m json.tool
	@echo ""
	@echo "Agendamentos:"
	@curl -s http://localhost:8000/stats/appointments | python -m json.tool

# ========== ADMIN ==========

procedures-list: ## Lista procedimentos cadastrados
	@curl -s http://localhost:8000/admin/procedures | python -m json.tool

hours-list: ## Lista horários de funcionamento
	@curl -s http://localhost:8000/admin/business-hours | python -m json.tool

appointments-today: ## Lista agendamentos de hoje
	@curl -s http://localhost:8000/admin/appointments/today | python -m json.tool

# ========== LIMPEZA ==========

clean: ## Limpa arquivos temporários e caches
	@echo "$(YELLOW)Limpando arquivos temporários...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "$(GREEN)Limpeza concluída!$(NC)"

clean-all: clean down ## Limpa tudo e para containers
	@echo "$(RED)Removendo volumes Docker...$(NC)"
	$(COMPOSE) down -v
	@echo "$(GREEN)Sistema limpo!$(NC)"

# ========== PRODUÇÃO ==========

prod-build: ## Build para produção
	@echo "$(GREEN)Build de produção...$(NC)"
	$(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml build

prod-up: ## Inicia em modo produção
	@echo "$(GREEN)Iniciando em produção...$(NC)"
	$(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml up -d

# ========== MONITORAMENTO ==========

health: ## Verifica saúde do sistema
	@echo "$(GREEN)Verificando saúde do sistema...$(NC)"
	@curl -s http://localhost:8000/health | python -m json.tool

monitor: ## Monitora logs em tempo real
	@echo "$(GREEN)Monitorando sistema...$(NC)"
	$(COMPOSE) logs -f --tail=100