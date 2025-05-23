"""
Migration: add analysis_feedback table for HR feedback
"""
from sqlalchemy import Column, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import text
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'analysis_feedback',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('analysis_id', sa.Integer(), sa.ForeignKey('analysis_results.id'), nullable=False, index=True),
        sa.Column('hr_rating', sa.Integer(), nullable=False),
        sa.Column('hr_comment', sa.Text(), nullable=True),
        sa.Column('is_successful', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_analysis_feedback_analysis_id', 'analysis_feedback', ['analysis_id'])
    op.create_index('ix_analysis_feedback_hr_rating', 'analysis_feedback', ['hr_rating'])

def downgrade():
    op.drop_index('ix_analysis_feedback_hr_rating', table_name='analysis_feedback')
    op.drop_index('ix_analysis_feedback_analysis_id', table_name='analysis_feedback')
    op.drop_table('analysis_feedback')
