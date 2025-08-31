"""
services/core/alembic/versions/20250123_000_etapa5_calendar_tables.py
"""

"""Etapa 5: Adiciona tabelas para integração com Google Calendar

Revision ID: etapa5_calendar
Revises: etapa4_add_client_profile_and_conversation_state
Create Date: 2025-01-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import time, datetime

# revision identifiers, used by Alembic.
revision = 'etapa5_calendar'
down_revision = 'etapa4_add_client_profile_and_conversation_state'
branch_labels = None
depends_on = None


def upgrade():
    # Tabela de catálogo de procedimentos
    op.create_table('procedure_catalog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('duration_min', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # Tabela de horários de funcionamento
    op.create_table('business_hours',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('weekday', sa.Integer(), nullable=False),  # 0=segunda, 6=domingo
        sa.Column('open_time', sa.Time(), nullable=True),
        sa.Column('close_time', sa.Time(), nullable=True),
        sa.Column('closed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('weekday >= 0 AND weekday <= 6', name='check_weekday_range')
    )
    
    # Tabela de agendamentos
    op.create_table('appointments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('conversation_id', sa.Text(), nullable=True),
        sa.Column('procedure_code', sa.Text(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('google_event_id', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('tentative', 'confirmed', 'cancelled')", name='check_appointment_status')
    )
    
    # Índices para performance
    op.create_index('ix_appointments_date', 'appointments', ['date'])
    op.create_index('ix_appointments_google_event_id', 'appointments', ['google_event_id'])
    op.create_index('ix_appointments_status', 'appointments', ['status'])
    op.create_index('ix_business_hours_weekday', 'business_hours', ['weekday'])
    
    # Seed data para procedure_catalog
    procedures = [
        ('limpeza', 'Limpeza', 30),
        ('consulta', 'Consulta', 45),
        ('avaliacao', 'Avaliação', 30),
        ('ortodontia', 'Ortodontia', 60),
        ('restauracao', 'Restauração', 45),
        ('canal', 'Tratamento de Canal', 90),
        ('extracao', 'Extração', 60),
        ('clareamento', 'Clareamento', 60),
        ('implante', 'Implante', 120),
    ]
    
    conn = op.get_bind()
    for code, name, duration in procedures:
        conn.execute(
            sa.text(
                "INSERT INTO procedure_catalog (code, name, duration_min, active) "
                "VALUES (:code, :name, :duration, true)"
            ),
            {"code": code, "name": name, "duration": duration}
        )
    
    # Seed data para business_hours
    # Segunda a Sexta: 08:00 - 18:00
    for weekday in range(0, 5):  # 0=segunda até 4=sexta
        conn.execute(
            sa.text(
                "INSERT INTO business_hours (weekday, open_time, close_time, closed) "
                "VALUES (:weekday, :open_time, :close_time, false)"
            ),
            {
                "weekday": weekday,
                "open_time": time(8, 0),
                "close_time": time(18, 0)
            }
        )
    
    # Sábado: 08:00 - 12:00
    conn.execute(
        sa.text(
            "INSERT INTO business_hours (weekday, open_time, close_time, closed) "
            "VALUES (:weekday, :open_time, :close_time, false)"
        ),
        {
            "weekday": 5,
            "open_time": time(8, 0),
            "close_time": time(12, 0)
        }
    )
    
    # Domingo: Fechado
    conn.execute(
        sa.text(
            "INSERT INTO business_hours (weekday, open_time, close_time, closed) "
            "VALUES (:weekday, NULL, NULL, true)"
        ),
        {"weekday": 6}
    )


def downgrade():
    op.drop_index('ix_business_hours_weekday', table_name='business_hours')
    op.drop_index('ix_appointments_status', table_name='appointments')
    op.drop_index('ix_appointments_google_event_id', table_name='appointments')
    op.drop_index('ix_appointments_date', table_name='appointments')
    op.drop_table('appointments')
    op.drop_table('business_hours')
    op.drop_table('procedure_catalog')