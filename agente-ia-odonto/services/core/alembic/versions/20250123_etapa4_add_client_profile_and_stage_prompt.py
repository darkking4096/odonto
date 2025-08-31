"""etapa4 add client profile and stage prompt

Revision ID: etapa4_001
Revises: 
Create Date: 2025-01-23 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'etapa4_001'
down_revision = 'initial_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Criar tabela client_profile
    op.create_table('client_profile',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.Text(), nullable=True),
        sa.Column('procedure', sa.Text(), nullable=True),
        sa.Column('desired_date', sa.Date(), nullable=True),
        sa.Column('desired_time', sa.Time(), nullable=True),
        sa.Column('desired_window', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_client_profile_client_id'), 'client_profile', ['client_id'], unique=True)

    # Criar tabela stage_prompt
    op.create_table('stage_prompt',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stage_name', sa.Text(), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('user_template', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stage_name')
    )
    op.create_index(op.f('ix_stage_prompt_stage_name'), 'stage_prompt', ['stage_name'], unique=True)

    # Inserir prompts iniciais (seed data)
    op.execute("""
        INSERT INTO stage_prompt (stage_name, system_prompt, user_template, active) VALUES
        ('saudacao', 
         'Você é um assistente de agendamento odontológico. Seja breve, amigável e direto. Responda com no máximo 20 palavras. Cumprimente e pergunte como pode ajudar.',
         'Cliente disse: {message}',
         true),
        
        ('intencao',
         'Identifique a intenção: agendar, reagendar, cancelar ou dúvida. Confirme o que entendeu em no máximo 20 palavras.',
         'Cliente disse: {message}\\nHistórico: {history}',
         true),
        
        ('coleta_dados',
         'Colete nome, procedimento e horário desejado. Faça UMA pergunta por vez. Máximo 20 palavras.',
         'Cliente disse: {message}\\nDados coletados: {collected_data}\\nFaltam: {missing_data}',
         true),
        
        ('proposta_horarios',
         'Proponha 2-3 horários baseados na preferência. Seja direto. Máximo 30 palavras.',
         'Preferência: {preference}\\nProcedimento: {procedure}\\nHorários exemplo: 09:00, 10:30, 14:00, 15:30',
         true),
        
        ('confirmacao',
         'Confirme o horário escolhido. Repita os dados principais. Máximo 25 palavras.',
         'Escolha: {choice}\\nDados: {appointment_data}',
         true),
        
        ('fechamento',
         'Finalize com resumo e agradecimento. Máximo 25 palavras.',
         'Resumo: {summary}',
         true)
    """)


def downgrade() -> None:
    # Remover índices e tabelas
    op.drop_index(op.f('ix_stage_prompt_stage_name'), table_name='stage_prompt')
    op.drop_table('stage_prompt')
    op.drop_index(op.f('ix_client_profile_client_id'), table_name='client_profile')
    op.drop_table('client_profile')