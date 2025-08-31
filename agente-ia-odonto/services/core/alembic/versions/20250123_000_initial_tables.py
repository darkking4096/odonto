"""initial tables

Revision ID: initial_001
Revises: 
Create Date: 2025-01-23 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'initial_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Criar tabela clients
    op.create_table('clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone')
    )
    
    # Criar tabela conversations
    op.create_table('conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar tabela messages
    op.create_table('messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('direction', sa.String(3), nullable=False),
        sa.Column('whatsapp_message_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar tabela stage_history
    op.create_table('stage_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('stage_from', sa.String(50), nullable=False),
        sa.Column('stage_to', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar índices
    op.create_index('ix_clients_phone', 'clients', ['phone'])
    op.create_index('ix_conversations_client_id', 'conversations', ['client_id'])
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_stage_history_client_id', 'stage_history', ['client_id'])


def downgrade() -> None:
    # Remover índices
    op.drop_index('ix_stage_history_client_id', 'stage_history')
    op.drop_index('ix_messages_conversation_id', 'messages')
    op.drop_index('ix_conversations_client_id', 'conversations')
    op.drop_index('ix_clients_phone', 'clients')
    
    # Remover tabelas (ordem inversa por causa das FKs)
    op.drop_table('stage_history')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('clients')