"""
services/core/stages/engine.py - VERSÃO ATUALIZADA ETAPA 5
"""

import json
from typing import Dict, Optional, Tuple
from datetime import datetime, date, time
from sqlalchemy import select, update

from services.core.database import get_db
from services.core.ai.adapter import get_llm_adapter
from services.core.stages.extractors import extract_client_info
from services.core.stages.prompts import get_prompt_for_stage
from services.core.stages.validators import validate_stage_data
from services.core.calendar import (
    get_calendar_service,
    parse_date,
    parse_time,
    parse_relative_date,
    format_date_br,
    format_time_br
)


class ConversationEngine:
    """Motor principal de conversação com integração ao Google Calendar."""
    
    def __init__(self):
        self.llm = get_llm_adapter()
        self.calendar = get_calendar_service()
        
    def process_message(
        self,
        message: str,
        conversation_id: str,
        phone: str
    ) -> Tuple[str, str]:
        """
        Processa mensagem e retorna resposta com novo estágio.
        
        Returns:
            Tuple (resposta, novo_estágio)
        """
        with get_db() as db:
            # Busca estado atual da conversa
            current_state = self._get_conversation_state(db, conversation_id)
            
            if not current_state:
                # Nova conversa
                current_stage = "saudacao"
                client_profile = {}
            else:
                current_stage = current_state.get("current_stage", "saudacao")
                client_profile = current_state.get("client_profile", {})
                
            # Processa baseado no estágio atual
            if current_stage == "saudacao":
                response, next_stage = self._handle_greeting(message, client_profile)
                
            elif current_stage == "intencao":
                response, next_stage = self._handle_intention(message, client_profile)
                
            elif current_stage == "coleta_dados":
                response, next_stage = self._handle_data_collection(
                    message, client_profile, conversation_id, phone, db
                )
                
            elif current_stage == "proposta_horarios":
                response, next_stage = self._handle_schedule_proposal(
                    message, client_profile, conversation_id, db
                )
                
            elif current_stage == "confirmacao":
                response, next_stage = self._handle_confirmation(
                    message, client_profile, conversation_id, db
                )
                
            elif current_stage == "fechamento":
                response, next_stage = self._handle_closing(message)
                
            else:
                response = "Desculpe, houve um erro. Vamos recomeçar?"
                next_stage = "saudacao"
                
            # Salva estado atualizado
            self._save_conversation_state(
                db, conversation_id, next_stage, client_profile
            )
            
            db.commit()
            
        return response, next_stage
        
    def _handle_greeting(self, message: str, profile: Dict) -> Tuple[str, str]:
        """Lida com estágio de saudação."""
        # Extrai nome se possível
        extracted = extract_client_info(message)
        if extracted.get("full_name"):
            profile["full_name"] = extracted["full_name"]
            
        # Gera resposta
        prompt = get_prompt_for_stage("saudacao", message, profile)
        response = self.llm.generate(prompt)
        
        # Determina próximo estágio
        if any(word in message.lower() for word in ["agendar", "marcar", "consulta", "horário"]):
            next_stage = "intencao"
        else:
            next_stage = "saudacao"  # Continua em saudação
            
        return response, next_stage
        
    def _handle_intention(self, message: str, profile: Dict) -> Tuple[str, str]:
        """Lida com identificação de intenção."""
        # Extrai informações do procedimento
        extracted = extract_client_info(message)
        
        if extracted.get("procedure"):
            profile["procedure"] = extracted["procedure"]
            
        # Mapeia procedimentos comuns
        procedure_map = {
            "limpeza": "limpeza",
            "consulta": "consulta",
            "avaliação": "avaliacao",
            "avaliacao": "avaliacao",
            "ortodontia": "ortodontia",
            "aparelho": "ortodontia",
            "restauração": "restauracao",
            "restauracao": "restauracao",
            "obturação": "restauracao",
            "obturacao": "restauracao",
            "canal": "canal",
            "extração": "extracao",
            "extracao": "extracao",
            "arrancar": "extracao",
            "clareamento": "clareamento",
            "branqueamento": "clareamento",
            "implante": "implante"
        }
        
        # Normaliza procedimento
        if "procedure" in profile:
            for key, value in procedure_map.items():
                if key in profile["procedure"].lower():
                    profile["procedure"] = value
                    break
                    
        # Verifica se tem informação suficiente
        if profile.get("procedure"):
            response = f"Ótimo! Vamos agendar {profile['procedure']}. "
            
            if not profile.get("full_name"):
                response += "Primeiro, qual é o seu nome completo?"
                next_stage = "coleta_dados"
            else:
                response += "Tem alguma preferência de horário? Manhã, tarde ou um dia específico?"
                next_stage = "coleta_dados"
        else:
            response = "Que tipo de atendimento você precisa? Temos limpeza, consulta, restauração, canal, entre outros."
            next_stage = "intencao"
            
        return response, next_stage
        
    def _handle_data_collection(
        self,
        message: str,
        profile: Dict,
        conversation_id: str,
        phone: str,
        db
    ) -> Tuple[str, str]:
        """Lida com coleta de dados do cliente."""
        # Extrai informações
        extracted = extract_client_info(message)
        
        # Atualiza profile
        for key in ["full_name", "email", "desired_date", "desired_time", "desired_window"]:
            if extracted.get(key):
                profile[key] = extracted[key]
                
        # Tenta parse de data relativa
        date_parsed = parse_relative_date(message)
        if date_parsed:
            profile["desired_date"] = date_parsed.isoformat()
            
        # Salva telefone se não tiver
        if not profile.get("phone"):
            profile["phone"] = phone
            
        # Valida dados necessários
        missing = []
        if not profile.get("full_name"):
            missing.append("nome")
        if not profile.get("procedure"):
            missing.append("procedimento")
            
        if missing:
            if "nome" in missing:
                response = "Por favor, me informe seu nome completo."
            else:
                response = "Que tipo de atendimento você precisa?"
            next_stage = "coleta_dados"
        else:
            # Cria ou atualiza cliente no banco
            self._ensure_client_exists(db, profile, conversation_id)
            
            # Vai para proposta de horários
            response = "Aguarde um momento enquanto verifico os horários disponíveis..."
            next_stage = "proposta_horarios"
            
        return response, next_stage
        
    def _handle_schedule_proposal(
        self,
        message: str,
        profile: Dict,
        conversation_id: str,
        db
    ) -> Tuple[str, str]:
        """Propõe horários reais disponíveis no Google Calendar."""
        
        # Busca duração do procedimento no banco
        procedure_code = profile.get("procedure", "consulta")
        result = db.execute(
            """
            SELECT duration_min, name
            FROM procedure_catalog
            WHERE code = :code AND active = true
            """,
            {"code": procedure_code}
        ).fetchone()
        
        if result:
            duration_min = result[0]
            procedure_name = result[1]
        else:
            duration_min = 45  # Default
            procedure_name = "Consulta"
            
        # Define parâmetros de busca
        date_from = None
        date_to = None
        window = profile.get("desired_window")
        
        # Se tem data específica desejada
        if profile.get("desired_date"):
            try:
                date_from = date.fromisoformat(profile["desired_date"])
                date_to = date_from
            except:
                pass
                
        # Busca slots disponíveis
        slots = self.calendar.list_free_slots(
            date_from=date_from,
            date_to=date_to,
            duration_min=duration_min,
            window=window,
            limit=3
        )
        
        if not slots:
            # Não há horários disponíveis
            if date_from:
                response = f"Não temos horários disponíveis em {format_date_br(date_from)}. "
                response += "Posso verificar outras datas. Qual seria sua segunda opção?"
            else:
                response = "No momento estamos com a agenda lotada. "
                response += "Podemos agendar para daqui 2 semanas. Tudo bem para você?"
                
            next_stage = "coleta_dados"
        else:
            # Salva slots propostos no profile para referência
            profile["proposed_slots"] = [
                {
                    "date": slot["date"].isoformat(),
                    "start_time": slot["start_time"].isoformat(),
                    "end_time": slot["end_time"].isoformat(),
                    "formatted": slot["formatted"]
                }
                for slot in slots
            ]
            
            # Monta resposta com opções
            response = f"Tenho os seguintes horários disponíveis para {procedure_name}:\n\n"
            
            for i, slot in enumerate(slots, 1):
                response += f"{i}. {slot['weekday']}, {slot['formatted']}\n"
                
            response += "\nQual horário prefere? (responda 1, 2 ou 3)"
            next_stage = "confirmacao"
            
        return response, next_stage
        
    def _handle_confirmation(
        self,
        message: str,
        profile: Dict,
        conversation_id: str,
        db
    ) -> Tuple[str, str]:
        """Confirma agendamento e cria evento no Google Calendar."""
        
        # Detecta cancelamento ou reagendamento
        lower_msg = message.lower()
        if any(word in lower_msg for word in ["cancelar", "cancela", "desmarcar"]):
            return self._handle_cancellation(profile, conversation_id, db)
            
        if any(word in lower_msg for word in ["remarcar", "reagendar", "mudar", "trocar"]):
            response = "Claro! Para qual data e horário você gostaria de remarcar?"
            return response, "coleta_dados"
            
        # Interpreta escolha do usuário
        chosen_slot = None
        proposed_slots = profile.get("proposed_slots", [])
        
        # Tenta identificar escolha por número
        if message.strip() in ["1", "2", "3"]:
            idx = int(message.strip()) - 1
            if 0 <= idx < len(proposed_slots):
                chosen_slot = proposed_slots[idx]
        else:
            # Tenta identificar por horário mencionado
            time_mentioned = parse_time(message)
            if time_mentioned:
                for slot in proposed_slots:
                    slot_time = time.fromisoformat(slot["start_time"])
                    if slot_time == time_mentioned:
                        chosen_slot = slot
                        break
                        
            # Ou aceita qualquer confirmação positiva para o primeiro slot
            if not chosen_slot and any(word in lower_msg for word in ["sim", "ok", "pode", "confirma", "isso", "perfeito"]):
                if proposed_slots:
                    chosen_slot = proposed_slots[0]
                    
        if not chosen_slot:
            response = "Por favor, escolha um dos horários sugeridos (1, 2 ou 3) ou digite 'cancelar' para desistir."
            return response, "confirmacao"
            
        # Cria evento no Google Calendar
        client_name = profile.get("full_name", "Cliente")
        procedure_code = profile.get("procedure", "consulta")
        
        # Busca nome do procedimento
        result = db.execute(
            """
            SELECT name FROM procedure_catalog
            WHERE code = :code
            """,
            {"code": procedure_code}
        ).fetchone()
        
        procedure_name = result[0] if result else "Consulta"
        
        # Recupera client_id
        client_id = self._get_client_id(db, conversation_id)
        
        # Cria evento
        event_date = date.fromisoformat(chosen_slot["date"])
        start_time = time.fromisoformat(chosen_slot["start_time"])
        end_time = time.fromisoformat(chosen_slot["end_time"])
        
        google_event_id = self.calendar.create_event(
            client_name=client_name,
            procedure_name=procedure_name,
            event_date=event_date,
            start_time=start_time,
            end_time=end_time,
            client_phone=profile.get("phone"),
            notes=profile.get("notes"),
            client_id=client_id
        )
        
        if google_event_id:
            # Salva no banco de dados
            db.execute(
                """
                INSERT INTO appointments (
                    client_id, conversation_id, procedure_code,
                    date, start_time, end_time, status, google_event_id
                ) VALUES (
                    :client_id, :conversation_id, :procedure_code,
                    :date, :start_time, :end_time, 'confirmed', :google_event_id
                )
                """,
                {
                    "client_id": client_id,
                    "conversation_id": conversation_id,
                    "procedure_code": procedure_code,
                    "date": event_date,
                    "start_time": start_time,
                    "end_time": end_time,
                    "google_event_id": google_event_id
                }
            )
            
            # Resposta de confirmação
            response = f"✅ Agendamento confirmado!\n\n"
            response += f"📅 {chosen_slot['formatted']}\n"
            response += f"👤 {client_name}\n"
            response += f"🦷 {procedure_name}\n\n"
            response += "Enviaremos um lembrete no dia anterior. Até lá!"
            
            next_stage = "fechamento"
        else:
            response = "Houve um erro ao confirmar o agendamento. Por favor, tente novamente."
            next_stage = "confirmacao"
            
        return response, next_stage
        
    def _handle_cancellation(
        self,
        profile: Dict,
        conversation_id: str,
        db
    ) -> Tuple[str, str]:
        """Cancela um agendamento existente."""
        
        # Busca agendamento ativo
        client_id = self._get_client_id(db, conversation_id)
        
        result = db.execute(
            """
            SELECT id, google_event_id, date, start_time, procedure_code
            FROM appointments
            WHERE client_id = :client_id
              AND status = 'confirmed'
              AND date >= CURRENT_DATE
            ORDER BY date, start_time
            LIMIT 1
            """,
            {"client_id": client_id}
        ).fetchone()
        
        if result:
            appointment_id = result[0]
            google_event_id = result[1]
            
            # Cancela no Google Calendar
            if google_event_id:
                self.calendar.cancel_event(google_event_id)
                
            # Atualiza status no banco
            db.execute(
                """
                UPDATE appointments
                SET status = 'cancelled',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """,
                {"id": appointment_id}
            )
            
            response = "Seu agendamento foi cancelado com sucesso. "
            response += "Gostaria de marcar um novo horário?"
            next_stage = "intencao"
        else:
            response = "Não encontrei nenhum agendamento ativo para cancelar. "
            response += "Posso ajudar com algo mais?"
            next_stage = "fechamento"
            
        return response, next_stage
        
    def _handle_closing(self, message: str) -> Tuple[str, str]:
        """Lida com fechamento da conversa."""
        response = "Foi um prazer atender você! Qualquer dúvida, estamos à disposição. 😊"
        return response, "fechamento"
        
    def _get_conversation_state(self, db, conversation_id: str) -> Optional[Dict]:
        """Busca estado atual da conversa."""
        result = db.execute(
            """
            SELECT current_stage, client_profile
            FROM conversation_state
            WHERE conversation_id = :id
            """,
            {"id": conversation_id}
        ).fetchone()
        
        if result:
            return {
                "current_stage": result[0],
                "client_profile": json.loads(result[1]) if result[1] else {}
            }
        return None
        
    def _save_conversation_state(
        self,
        db,
        conversation_id: str,
        stage: str,
        profile: Dict
    ):
        """Salva ou atualiza estado da conversa."""
        profile_json = json.dumps(profile, ensure_ascii=False)
        
        # Tenta atualizar primeiro
        result = db.execute(
            """
            UPDATE conversation_state
            SET current_stage = :stage,
                client_profile = :profile,
                updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = :id
            RETURNING id
            """,
            {
                "id": conversation_id,
                "stage": stage,
                "profile": profile_json
            }
        ).fetchone()
        
        # Se não atualizou, insere
        if not result:
            db.execute(
                """
                INSERT INTO conversation_state (
                    conversation_id, current_stage, client_profile
                ) VALUES (:id, :stage, :profile)
                """,
                {
                    "id": conversation_id,
                    "stage": stage,
                    "profile": profile_json
                }
            )
            
    def _ensure_client_exists(self, db, profile: Dict, conversation_id: str):
        """Garante que o cliente existe no banco."""
        phone = profile.get("phone", "")
        
        # Busca cliente existente
        result = db.execute(
            """
            SELECT id FROM clients
            WHERE phone = :phone
            """,
            {"phone": phone}
        ).fetchone()
        
        if result:
            client_id = result[0]
            # Atualiza dados se necessário
            db.execute(
                """
                UPDATE clients
                SET full_name = COALESCE(:name, full_name),
                    email = COALESCE(:email, email),
                    last_interaction = CURRENT_TIMESTAMP
                WHERE id = :id
                """,
                {
                    "id": client_id,
                    "name": profile.get("full_name"),
                    "email": profile.get("email")
                }
            )
        else:
            # Cria novo cliente
            db.execute(
                """
                INSERT INTO clients (
                    phone, full_name, email, active
                ) VALUES (
                    :phone, :name, :email, true
                )
                """,
                {
                    "phone": phone,
                    "name": profile.get("full_name", ""),
                    "email": profile.get("email")
                }
            )
            
    def _get_client_id(self, db, conversation_id: str) -> Optional[int]:
        """Busca ID do cliente pela conversa."""
        # Primeiro tenta pela tabela de appointments
        result = db.execute(
            """
            SELECT DISTINCT client_id
            FROM appointments
            WHERE conversation_id = :conv_id
            LIMIT 1
            """,
            {"conv_id": conversation_id}
        ).fetchone()
        
        if result:
            return result[0]
            
        # Senão, busca pelo telefone no estado da conversa
        state = self._get_conversation_state(db, conversation_id)
        if state:
            profile = state.get("client_profile", {})
            phone = profile.get("phone")
            
            if phone:
                result = db.execute(
                    """
                    SELECT id FROM clients
                    WHERE phone = :phone
                    """,
                    {"phone": phone}
                ).fetchone()
                
                if result:
                    return result[0]
                    
        return None