# ETAPA 4 - Integração com IA e Máquina de Estados

## 📋 O que esta etapa implementa

Esta etapa adiciona inteligência artificial ao agente de agendamento odontológico, implementando:

1. **Adapter plugável para LLMs** - Suporte para Claude (Anthropic), GPT (OpenAI) e Gemini (Google)
2. **Máquina de estados com 6 estágios** - Fluxo conversacional estruturado
3. **Extração inteligente de dados** - Nome, procedimento, data/horário desejado
4. **Validação automática** - Normalização e verificação de dados
5. **Prompts contextuais** - Respostas personalizadas por estágio
6. **Persistência completa** - Perfil do cliente e histórico de transições

## 🚀 Como configurar

### 1. Variáveis de ambiente

Adicione estas variáveis ao seu arquivo `.env`:

```env
# Provider de IA (escolha um: anthropic, openai, google)
AI_PROVIDER=anthropic

# Configurações Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-api03-xxx-yyy-zzz
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Configurações OpenAI GPT
OPENAI_API_KEY=sk-xxx-yyy-zzz
OPENAI_MODEL=gpt-4o-mini

# Configurações Google Gemini
GOOGLE_API_KEY=AIza-xxx-yyy-zzz
GOOGLE_MODEL=gemini-1.5-flash

# Parâmetros gerais de IA
AI_TEMPERATURE=0.4
AI_MAX_TOKENS=200

# Evolution API (já existente)
EVOLUTION_API_URL=http://evolution:8080
EVOLUTION_INSTANCE=odonto
EVOLUTION_API_KEY=sua-chave-aqui

# Banco de dados (já existente)
DATABASE_URL=postgresql://user:password@postgres:5432/odonto_db
```

### 2. Instalar dependências

```bash
cd services/core
pip install -r requirements.txt
```

### 3. Aplicar migrações do banco

```bash
# Dentro do container ou ambiente virtual
cd services/core
alembic upgrade head
```

### 4. Verificar tabelas criadas

As migrações criarão duas novas tabelas:

- **client_profile** - Armazena dados extraídos do cliente
- **stage_prompt** - Prompts configuráveis por estágio

Os prompts iniciais já são inseridos automaticamente durante a migração.

## 🧪 Como testar

### Teste 1: Fluxo completo de agendamento

**Envie pelo WhatsApp:**
```
Oi, quero marcar uma limpeza
```

**Resposta esperada:**
```
Olá! Vou ajudar com seu agendamento. Qual procedimento deseja?
```

**Continue:**
```
Limpeza dental. Sou a Sandra
```

**Resposta esperada:**
```
Perfeito Sandra! Quando prefere: manhã ou tarde?
```

**Continue:**
```
Amanhã de manhã seria bom
```

**Resposta esperada:**
```
Tenho estes horários: 09:00, 10:30 ou 11:00. Qual prefere?
```

**Continue:**
```
Pode ser às 10:30
```

**Resposta esperada:**
```
Confirmado! Sandra, limpeza amanhã às 10:30. Correto?
```

**Continue:**
```
Sim, perfeito!
```

**Resposta esperada:**
```
Agendamento finalizado! Sandra, limpeza amanhã 10:30. Obrigado!
```

### Teste 2: Verificar extração de dados

**Envie uma mensagem com múltiplos dados:**
```
Oi, sou o João Silva. Quero marcar avaliação para terça às 14h
```

O sistema deve extrair automaticamente:
- Nome: João Silva
- Procedimento: avaliação
- Dia: próxima terça-feira
- Horário: 14:00

### Teste 3: Verificar validação

**Teste com procedimento inválido:**
```
Quero fazer um procedimento de botox
```

**Resposta esperada:**
```
Não oferecemos esse procedimento. Temos: limpeza, consulta, ortodontia...
```

**Teste com horário inválido:**
```
Pode ser às 23h?
```

**Resposta esperada:**
```
Funcionamos das 8h às 18h. Prefere manhã ou tarde?
```

## 📊 Verificar funcionamento

### 1. Logs do sistema

```bash
docker logs odonto-core-1 -f
```

Você deve ver:
- `Cliente X no estágio: saudacao`
- `Dados extraídos: {'full_name': 'Sandra', ...}`
- `Transição: saudacao → intencao`
- `Resposta gerada: ...`

### 2. Verificar banco de dados

```sql
-- Conectar ao PostgreSQL
docker exec -it odonto-postgres-1 psql -U user -d odonto_db

-- Ver perfis de clientes
SELECT * FROM client_profile;

-- Ver histórico de estágios
SELECT * FROM stage_history ORDER BY created_at DESC;

-- Ver prompts configurados
SELECT stage_name, active FROM stage_prompt;

-- Ver mensagens processadas
SELECT direction, content, created_at 
FROM messages 
ORDER BY created_at DESC 
LIMIT 10;
```

### 3. API de estatísticas

```bash
curl http://localhost:8000/stats
```

Resposta esperada:
```json
{
  "total_clients": 5,
  "total_conversations": 8,
  "total_messages": 42,
  "total_stage_transitions": 35,
  "stages": {
    "saudacao": 8,
    "intencao": 8,
    "coleta_dados": 12,
    "proposta_horarios": 5,
    "confirmacao": 2,
    "fechamento": 0
  }
}
```

### 4. Health check

```bash
curl http://localhost:8000/health
```

Resposta esperada:
```json
{
  "status": "healthy",
  "database": "connected",
  "ai_provider": "configured",
  "evolution_api": "http://evolution:8080",
  "timestamp": "2025-01-23T10:00:00"
}
```

## 🔧 Solução de problemas

### Problema: "Provider de IA não disponível"

**Causa:** API key não configurada ou inválida

**Solução:**
1. Verifique se a variável `AI_PROVIDER` está definida
2. Confirme que a API key correspondente está no `.env`
3. Teste a API key diretamente:

```python
# Para Claude
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-haiku-20240307","messages":[{"role":"user","content":"Hi"}],"max_tokens":10}'
```

### Problema: Timeout nas respostas

**Causa:** LLM demorando muito para responder

**Solução:**
1. Reduza `AI_MAX_TOKENS` para 150 ou 100
2. Use um modelo mais rápido (haiku para Claude, gpt-4o-mini para OpenAI)
3. Aumente o timeout no código se necessário

### Problema: Respostas genéricas ou fora de contexto

**Causa:** Prompts não otimizados para o modelo

**Solução:**
1. Ajuste os prompts na tabela `stage_prompt`:

```sql
UPDATE stage_prompt 
SET system_prompt = 'Novo prompt mais específico...'
WHERE stage_name = 'coleta_dados';
```

2. Reduza `AI_TEMPERATURE` para 0.2 ou 0.3 para respostas mais consistentes

### Problema: Dados não sendo extraídos

**Causa:** Padrões de regex não cobrem o formato usado

**Solução:**
1. Verifique os logs para ver o que foi tentado extrair
2. Ajuste os padrões em `extractors.py` se necessário
3. Teste isoladamente:

```python
from stages.extractors import DataExtractor
extractor = DataExtractor()
result = extractor.extract_all("Sou a Maria, quero limpeza amanhã às 10h")
print(result)
```

## 📈 Métricas de sucesso

✅ **Provider de IA configurado e respondendo**
- Health check mostra `"ai_provider": "configured"`

✅ **Extração funcionando**
- Tabela `client_profile` sendo populada com dados corretos

✅ **Transições de estágio ocorrendo**
- Tabela `stage_history` registrando mudanças

✅ **Respostas contextuais**
- Bot responde diferente baseado no estágio atual

✅ **Validação ativa**
- Procedimentos inválidos são rejeitados
- Horários fora do funcionamento são corrigidos

## 🎯 Critérios de aceite

- [x] `.env` permite escolher Claude/GPT/Gemini sem alterar código
- [x] `alembic upgrade head` cria `client_profile` e `stage_prompt`
- [x] Seed inicial popula prompts por estágio
- [x] Engine conduz usuário pelos 6 estágios com mensagens curtas
- [x] Extração e validação persistem dados no perfil
- [x] Transições gravadas em `stage_history`
- [x] Logs mostram estágio atual → novo, dados capturados, provider usado
- [x] Conversas reais no WhatsApp funcionam com respostas humanizadas

## 📝 Próximas etapas

**Etapa 5** implementará:
- Integração com Google Calendar real
- Verificação de disponibilidade
- Confirmação por e-mail
- Interface web para gestão

---

**Dúvidas?** Verifique os logs primeiro, depois teste cada componente isoladamente.