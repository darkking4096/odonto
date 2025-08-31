"""
Script para popular dados de teste no banco
"""
import sys
from datetime import datetime, timedelta
from database import get_db, init_db
from models import Client, Conversation, Message, StagePrompt, StageHistory

def seed_test_clients(db):
    """Cria clientes de teste"""
    print("Criando clientes de teste...")
    
    test_clients = [
        {"phone": "5511999990001", "name": "Ana Teste", "email": "ana@teste.com"},
        {"phone": "5511999990002", "name": "Bruno Teste", "email": "bruno@teste.com"},
        {"phone": "5511999990003", "name": "Carlos Teste", "email": "carlos@teste.com"},
    ]
    
    for client_data in test_clients:
        existing = db.query(Client).filter_by(phone=client_data["phone"]).first()
        if not existing:
            client = Client(**client_data, created_at=datetime.utcnow())
            db.add(client)
            print(f"  ✅ Cliente criado: {client_data['name']}")
        else:
            print(f"  ⏭️  Cliente já existe: {client_data['name']}")
    
    db.commit()


def seed_conversations(db):
    """Cria conversas de exemplo"""
    print("Criando conversas de exemplo...")
    
    clients = db.query(Client).limit(2).all()
    
    for client in clients:
        existing = db.query(Conversation).filter_by(client_id=client.id, active=True).first()
        if not existing:
            conversation = Conversation(
                client_id=client.id,
                active=True,
                created_at=datetime.utcnow()
            )
            db.add(conversation)
            db.commit()
            
            # Adicionar algumas mensagens de exemplo
            messages = [
                {"content": "Olá, gostaria de agendar uma consulta", "direction": "in"},
                {"content": "Claro! Vou ajudar com seu agendamento. Qual procedimento?", "direction": "out"},
                {"content": "Limpeza dental", "direction": "in"},
                {"content": "Perfeito! Quando prefere: manhã ou tarde?", "direction": "out"},
            ]
            
            for i, msg_data in enumerate(messages):
                message = Message(
                    conversation_id=conversation.id,
                    **msg_data,
                    created_at=datetime.utcnow() + timedelta(minutes=i)
                )
                db.add(message)
            
            print(f"  ✅ Conversa criada para: {client.name}")
        else:
            print(f"  ⏭️  Conversa já existe para: {client.name}")
    
    db.commit()


def update_prompts(db):
    """Atualiza prompts com versões otimizadas"""
    print("Atualizando prompts...")
    
    optimized_prompts = {
        "saudacao": {
            "system": "Seja um assistente amigável de clínica odontológica. Cumprimente e pergunte como ajudar. Máximo 20 palavras.",
            "template": "Nova conversa iniciada. Cliente disse: {message}"
        },
        "intencao": {
            "system": "Identifique se o cliente quer: agendar, reagendar, cancelar ou tirar dúvidas. Confirme entendimento. Máximo 20 palavras.",
            "template": "Cliente disse: {message}"
        },
        "coleta_dados": {
            "system": "Colete dados faltantes (nome, procedimento, horário). Uma pergunta por vez. Seja específico. Máximo 20 palavras.",
            "template": "Mensagem: {message}\nJá temos: {collected_data}\nFalta coletar: {missing_data}"
        },
        "proposta_horarios": {
            "system": "Sugira 3 horários baseados na preferência. Seja claro e direto. Máximo 30 palavras.",
            "template": "Cliente prefere: {preference}\nProcedimento: {procedure}"
        },
        "confirmacao": {
            "system": "Confirme o agendamento repetindo dados principais. Peça confirmação final. Máximo 25 palavras.",
            "template": "Dados do agendamento: {appointment_data}"
        },
        "fechamento": {
            "system": "Agradeça e finalize com resumo do agendamento. Seja cordial. Máximo 25 palavras.",
            "template": "Agendamento confirmado: {summary}"
        }
    }
    
    for stage_name, prompt_data in optimized_prompts.items():
        prompt = db.query(StagePrompt).filter_by(stage_name=stage_name).first()
        if prompt:
            prompt.system_prompt = prompt_data["system"]
            prompt.user_template = prompt_data["template"]
            prompt.updated_at = datetime.utcnow()
            print(f"  ✅ Prompt atualizado: {stage_name}")
        else:
            new_prompt = StagePrompt(
                stage_name=stage_name,
                system_prompt=prompt_data["system"],
                user_template=prompt_data["template"],
                active=True
            )
            db.add(new_prompt)
            print(f"  ✅ Prompt criado: {stage_name}")
    
    db.commit()


def show_statistics(db):
    """Mostra estatísticas do banco"""
    print("\n=== ESTATÍSTICAS DO BANCO ===")
    
    stats = {
        "Clientes": db.query(Client).count(),
        "Conversas": db.query(Conversation).count(),
        "Mensagens": db.query(Message).count(),
        "Prompts": db.query(StagePrompt).count(),
        "Transições": db.query(StageHistory).count(),
    }
    
    for label, count in stats.items():
        print(f"  {label}: {count}")


def main():
    """Executa o seed completo"""
    print("=" * 50)
    print("SEED DE DADOS DE TESTE")
    print("=" * 50)
    
    # Obter sessão do banco
    db = next(get_db())
    
    try:
        # Executar seeds
        seed_test_clients(db)
        seed_conversations(db)
        update_prompts(db)
        
        # Mostrar estatísticas
        show_statistics(db)
        
        print("\n✅ Seed concluído com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro durante seed: {str(e)}")
        db.rollback()
        return 1
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())