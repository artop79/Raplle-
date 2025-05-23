"""
Alembic migration script for HR platform models
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_hr_models'
down_revision = 'add_analysis_feedback'  # Предполагается, что предыдущая миграция
branch_labels = None
depends_on = None

def upgrade():
    # Создание таблицы вакансий
    op.create_table(
        'vacancies',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('title', sa.String(255), index=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('requirements', postgresql.JSONB(), nullable=False),
        sa.Column('interview_type', sa.String(50), nullable=False),
        sa.Column('evaluation_criteria', postgresql.JSONB(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
    )
    
    # Проверяем, существует ли уже таблица interviews
    # Если да, мы добавим недостающие столбцы, если нет - создадим новую
    # В данном скрипте предполагаем, что таблица interviews уже существует (из alembic_migration_interview.py)
    # и мы просто добавляем недостающие поля для соответствия новой модели
    
    # Добавляем недостающие поля в существующую таблицу interviews
    op.add_column('interviews', sa.Column('vacancy_id', sa.Integer(), sa.ForeignKey('vacancies.id'), nullable=True))
    op.add_column('interviews', sa.Column('candidate_name', sa.String(255), nullable=True))
    op.add_column('interviews', sa.Column('candidate_email', sa.String(255), nullable=True))
    op.add_column('interviews', sa.Column('access_link', sa.String(255), unique=True, index=True, nullable=True))
    op.add_column('interviews', sa.Column('meeting_password', sa.String(100), nullable=True))
    
    # Переименовываем столбцы, если имена не совпадают с новой моделью
    op.alter_column('interviews', 'zoom_meeting_id', new_column_name='meeting_id', nullable=True)
    op.alter_column('interviews', 'scheduled_time', new_column_name='scheduled_at', nullable=True)
    
    # Создаем индекс для access_link
    op.create_index('ix_interviews_access_link', 'interviews', ['access_link'], unique=True)
    
    # Создание таблицы вопросов интервью
    op.create_table(
        'interview_questions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('interview_id', sa.Integer(), sa.ForeignKey('interviews.id'), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('is_required', sa.Boolean(), default=True),
    )
    
    # Создание таблицы ответов на вопросы интервью
    op.create_table(
        'interview_answers',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('question_id', sa.Integer(), sa.ForeignKey('interview_questions.id'), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=True),
        sa.Column('audio_file', sa.String(255), nullable=True),
        sa.Column('transcription', sa.Text(), nullable=True),
        sa.Column('analysis', postgresql.JSONB(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
    )
    
    # Создание таблицы отчетов по интервью
    op.create_table(
        'interview_reports',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('interview_id', sa.Integer(), sa.ForeignKey('interviews.id'), nullable=False),
        sa.Column('video_url', sa.String(255), nullable=True),
        sa.Column('total_score', sa.Float(), nullable=True),
        sa.Column('analysis_summary', sa.Text(), nullable=True),
        sa.Column('strengths', postgresql.JSONB(), nullable=True),
        sa.Column('weaknesses', postgresql.JSONB(), nullable=True),
        sa.Column('recommendation', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Создание таблицы уведомлений
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('type', sa.String(100), nullable=False),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('related_interview_id', sa.Integer(), sa.ForeignKey('interviews.id'), nullable=True),
        sa.Column('related_vacancy_id', sa.Integer(), sa.ForeignKey('vacancies.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    # Удаление всех созданных таблиц в обратном порядке
    op.drop_table('notifications')
    op.drop_table('interview_reports')
    op.drop_table('interview_answers')
    op.drop_table('interview_questions')
    
    # Удаление добавленных колонок из interviews
    op.drop_column('interviews', 'vacancy_id')
    op.drop_column('interviews', 'candidate_name')
    op.drop_column('interviews', 'candidate_email')
    op.drop_column('interviews', 'access_link')
    op.drop_column('interviews', 'meeting_password')
    
    # Возврат переименованных колонок
    op.alter_column('interviews', 'meeting_id', new_column_name='zoom_meeting_id')
    op.alter_column('interviews', 'scheduled_at', new_column_name='scheduled_time')
    
    # Удаление таблицы вакансий
    op.drop_table('vacancies')
