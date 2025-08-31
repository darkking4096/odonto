"""
Gerenciador de prompts por estágio
"""
import logging
from typing import List, Tuple, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)


class PromptManager:
    """Gerencia prompts para cada estágio da conversa"""
    
    def __init__(self, db: Session):
        self.db = db
        # Prompts default caso não existam no banco
        self.default_prompts = {
            "saudacao": {
                "system": """Você é um assistente de agendamento odontológico. Seja breve, amigável e direto.
                Responda com no máximo 20 palavras. Identifique se é cliente novo ou recorrente.""",
                "template": "Cliente disse: {message}\nContexto: {context}"
            },
            "intencao": {
                "system": """Identifique a intenção do cliente: agendar, reagendar, cancelar ou dúvida.
                Responda confirmando o que entendeu, em no máximo 20 palavras.""",
                "template": "Cliente disse: {message}\nHistórico: {history}"
            },
            "coleta_dados": {
                "system": """Colete os dados necessários: nome, procedimento e horário desejado.
                Faça UMA pergunta por vez. Máximo 20 palavras. Seja específico e claro.""",
                "template": """Cliente disse: {message}
                Dados já coletados: {collected_data}
                Dados faltantes: {missing_data}"""
            },
            "proposta_horarios": {
                "system": """Proponha 2-3 horários disponíveis baseados na preferência do cliente.
                Seja direto e ofereça opções claras. Máximo 30 palavras.""",
                "template": """Cliente deseja: {preference}
                Procedimento: {procedure}
                Horários simulados disponíveis: 09:00, 10:30, 14:00, 15:30"""
            },
            "confirmacao": {
                "system": """Confirme o horário escolhido pelo cliente.
                Repita os dados principais. Máximo 25 palavras.""",
                "template": """Cliente escolheu: {choice}
                Dados do agendamento: {appointment_data}"""
            },
            "fechamento": {
                "system": """Finalize o atendimento com um resumo e agradecimento.
                Máximo 25 palavras. Seja cordial e profissional.""",
                "template": "Resumo do agendamento: {summary}"
            }
        }
    
    def build_prompts(
        self,
        stage: str,
        client_profile: Any,
        recent_messages: List[Any],
        current_message: str
    ) -> Tuple[str, str]:
        """
        Constrói prompts para o estágio atual
        """
        # Tentar buscar prompt do banco
        from models import StagePrompt
        db_prompt = self.db.query(StagePrompt)\
            .filter_by(stage_name=stage, active=True)\
            .first()
        
        if db_prompt:
            system_prompt = db_prompt.system_prompt
            template = db_prompt.user_template
        else:
            # Usar prompt default
            prompt_data = self.default_prompts.get(stage, self.default_prompts["saudacao"])
            system_prompt = prompt_data["system"]
            template = prompt_data["template"]
        
        # Construir contexto
        context = self._build_context(
            stage, 
            client_profile, 
            recent_messages, 
            current_message
        )
        
        # Formatar template com contexto
        user_prompt = self._format_template(template, context)
        
        logger.info(f"Prompts construídos para estágio {stage}")
        return system_prompt, user_prompt
    
    def _build_context(
        self, 
        stage: str, 
        profile: Any, 
        messages: List[Any], 
        current_msg: str
    ) -> dict:
        """Constrói contexto para o prompt"""
        context = {
            "message": current_msg,
            "stage": stage,
            "history": self._format_message_history(messages),
            "context": self._format_client_context(profile)
        }
        
        # Adicionar dados específicos por estágio
        if stage == "coleta_dados":
            context["collected_data"] = self._format_collected_data(profile)
            context["missing_data"] = self._identify_missing_data(profile)
        
        elif stage == "proposta_horarios":
            context["preference"] = self._format_time_preference(profile)
            context["procedure"] = profile.procedure or "consulta"
        
        elif stage == "confirmacao":
            context["choice"] = current_msg
            context["appointment_data"] = self._format_appointment_data(profile)
        
        elif stage == "fechamento":
            context["summary"] = self._format_summary(profile)
        
        return context
    
    def _format_template(self, template: str, context: dict) -> str:
        """Formata template com valores do contexto"""
        try:
            # Substituir placeholders que existem no contexto
            for key, value in context.items():
                placeholder = "{" + key + "}"
                if placeholder in template:
                    template = template.replace(placeholder, str(value))
            
            # Remover placeholders não utilizados
            import re
            template = re.sub(r'\{[^}]+\}', '', template)
            
            return template.strip()
        except Exception as e:
            logger.error(f"Erro ao formatar template: {str(e)}")
            return f"Mensagem: {context.get('message', '')}"
    
    def _format_message_history(self, messages: List[Any]) -> str:
        """Formata histórico de mensagens"""
        if not messages:
            return "Início da conversa"
        
        history = []
        for msg in messages[-3:]:  # Últimas 3 mensagens
            direction = "Cliente" if msg.direction == "in" else "Assistente"
            history.append(f"{direction}: {msg.content[:50]}")
        
        return " | ".join(history)
    
    def _format_client_context(self, profile: Any) -> str:
        """Formata contexto do cliente"""
        parts = []
        
        if profile.full_name:
            parts.append(f"Nome: {profile.full_name}")
        
        if hasattr(profile, 'client') and profile.client:
            if hasattr(profile.client, 'phone'):
                parts.append(f"Telefone: {profile.client.phone}")
        
        return ", ".join(parts) if parts else "Cliente novo"
    
    def _format_collected_data(self, profile: Any) -> str:
        """Formata dados já coletados"""
        collected = []
        
        if profile.full_name:
            collected.append(f"Nome: {profile.full_name}")
        
        if profile.procedure:
            collected.append(f"Procedimento: {profile.procedure}")
        
        if profile.desired_date:
            collected.append(f"Data: {profile.desired_date}")
        
        if profile.desired_time:
            collected.append(f"Horário: {profile.desired_time}")
        
        if profile.desired_window:
            collected.append(f"Período: {profile.desired_window}")
        
        return ", ".join(collected) if collected else "Nenhum dado coletado ainda"
    
    def _identify_missing_data(self, profile: Any) -> str:
        """Identifica dados faltantes"""
        missing = []
        
        if not profile.full_name:
            missing.append("nome")
        
        if not profile.procedure:
            missing.append("procedimento")
        
        if not any([profile.desired_date, profile.desired_time, profile.desired_window]):
            missing.append("horário desejado")
        
        return ", ".join(missing) if missing else "Todos os dados coletados"
    
    def _format_time_preference(self, profile: Any) -> str:
        """Formata preferência de horário"""
        parts = []
        
        if profile.desired_date:
            parts.append(f"Data: {profile.desired_date}")
        
        if profile.desired_time:
            parts.append(f"Horário: {profile.desired_time}")
        
        if profile.desired_window:
            parts.append(f"Período: {profile.desired_window}")
        
        return ", ".join(parts) if parts else "Sem preferência específica"
    
    def _format_appointment_data(self, profile: Any) -> str:
        """Formata dados do agendamento"""
        parts = [
            f"Nome: {profile.full_name or 'A confirmar'}",
            f"Procedimento: {profile.procedure or 'Consulta'}",
            f"Data: {profile.desired_date or 'A confirmar'}",
            f"Horário: {profile.desired_time or profile.desired_window or 'A confirmar'}"
        ]
        
        return ", ".join(parts)
    
    def _format_summary(self, profile: Any) -> str:
        """Formata resumo final"""
        return self._format_appointment_data(profile)