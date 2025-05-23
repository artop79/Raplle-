"""
Alembic migration script for Interview and InterviewResult models
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_interview_models'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'interviews',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('zoom_meeting_id', sa.String(length=32), nullable=False),
        sa.Column('join_url', sa.String(length=512), nullable=False),
        sa.Column('start_url', sa.String(length=512), nullable=False),
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), default='scheduled'),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        'interview_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('interview_id', sa.Integer(), sa.ForeignKey('interviews.id'), nullable=False),
        sa.Column('result_json', postgresql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('interview_results')
    op.drop_table('interviews')
