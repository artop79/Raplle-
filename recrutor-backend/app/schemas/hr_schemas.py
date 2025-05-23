from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime

# Схемы для работы с вакансиями

class VacancyBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    requirements: Dict[str, List[str]] = Field(..., description="Требования к кандидату, например: {'skills': ['Python', 'SQL'], 'experience': ['1 год']}")
    interview_type: str = Field(..., description="Тип интервью: 'smart' или 'manual'")
    evaluation_criteria: Dict[str, Any] = Field(..., description="Критерии оценки кандидата")
    
    @validator('interview_type')
    def validate_interview_type(cls, v):
        if v not in ['smart', 'manual']:
            raise ValueError('Тип интервью должен быть "smart" или "manual"')
        return v

class VacancyCreate(VacancyBase):
    pass

class VacancyUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    requirements: Optional[Dict[str, List[str]]] = None
    interview_type: Optional[str] = None
    evaluation_criteria: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    
    @validator('interview_type')
    def validate_interview_type(cls, v):
        if v is not None and v not in ['smart', 'manual']:
            raise ValueError('Тип интервью должен быть "smart" или "manual"')
        return v

class VacancyResponse(VacancyBase):
    id: int
    is_active: bool
    created_at: datetime
    user_id: int
    
    class Config:
        orm_mode = True

class VacancyListItem(BaseModel):
    id: int
    title: str
    description: str
    requirements: Dict[str, List[str]]
    interview_type: str
    evaluation_criteria: Dict[str, Any]
    is_active: bool
    created_at: datetime
    interview_count: int
    completed_interview_count: int
    
    class Config:
        orm_mode = True

class VacancyListResponse(BaseModel):
    items: List[VacancyListItem]
    total: int
    skip: int
    limit: int

class VacancyStatsInterviews(BaseModel):
    total: int
    completed: int
    in_progress: int
    waiting: int

class VacancyRecommendationStats(BaseModel):
    recommended: int
    additional_interview: int
    not_recommended: int

class VacancyStatsResponse(BaseModel):
    vacancy_id: int
    title: str
    interviews: VacancyStatsInterviews
    avg_score: float
    recommendation_distribution: VacancyRecommendationStats

class InterviewShortInfo(BaseModel):
    id: int
    candidate_name: Optional[str]
    status: str
    scheduled_at: Optional[datetime]
    completed_at: Optional[datetime]
    has_report: bool
    
    class Config:
        orm_mode = True

class VacancyDetailResponse(VacancyResponse):
    stats: VacancyStatsInterviews
    recent_interviews: List[InterviewShortInfo]

# Схемы для работы с интервью

class InterviewQuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1)
    category: Optional[str] = None
    is_required: bool = True

class InterviewQuestion(InterviewQuestionCreate):
    id: int
    interview_id: int
    order: int
    
    class Config:
        orm_mode = True

class InterviewCreate(BaseModel):
    vacancy_id: int
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    questions: Optional[List[InterviewQuestionCreate]] = None

class InterviewResponse(BaseModel):
    id: int
    vacancy_id: int
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    status: str
    access_link: str
    meeting_id: Optional[str]
    meeting_password: Optional[str]
    scheduled_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        orm_mode = True

class InterviewListItem(BaseModel):
    id: int
    vacancy_id: int
    vacancy_title: str
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    status: str
    access_link: str
    scheduled_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    has_report: bool
    meeting_id: Optional[str]
    
    class Config:
        orm_mode = True

class InterviewListResponse(BaseModel):
    items: List[InterviewListItem]
    total: int
    skip: int
    limit: int

class InterviewAnswer(BaseModel):
    id: int
    question_id: int
    answer_text: Optional[str]
    audio_file: Optional[str]
    transcription: Optional[str]
    analysis: Optional[Dict[str, Any]]
    score: Optional[float]
    
    class Config:
        orm_mode = True

class InterviewReport(BaseModel):
    id: int
    interview_id: int
    video_url: Optional[str]
    total_score: Optional[float]
    analysis_summary: Optional[str]
    strengths: Optional[Union[List[str], str]]
    weaknesses: Optional[Union[List[str], str]]
    recommendation: Optional[str]
    created_at: datetime
    
    class Config:
        orm_mode = True

class InterviewDetailResponse(BaseModel):
    id: int
    vacancy_id: int
    vacancy_title: str
    vacancy_description: str
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    status: str
    access_link: str
    meeting_id: Optional[str]
    meeting_password: Optional[str]
    scheduled_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    questions: List[InterviewQuestion]
    report: Optional[InterviewReport] = None
    
    class Config:
        orm_mode = True

class InterviewReportResponse(BaseModel):
    id: int
    interview_id: int
    video_url: Optional[str]
    total_score: Optional[float]
    analysis_summary: Optional[str]
    strengths: Optional[Union[List[str], str]]
    weaknesses: Optional[Union[List[str], str]]
    recommendation: Optional[str]
    created_at: datetime
    candidate_name: Optional[str]
    vacancy_title: str
    questions_and_answers: List[Any]
    
    class Config:
        orm_mode = True

class InterviewLinkResponse(BaseModel):
    interview_id: int
    access_link: str
    full_url: str

class CandidateInterviewResponse(BaseModel):
    interview_id: int
    vacancy_title: str
    candidate_name: Optional[str]
    status: str
    scheduled_at: Optional[datetime]
    meeting_id: Optional[str]
    meeting_password: Optional[str]
    questions: List[InterviewQuestion]
    
    class Config:
        orm_mode = True

# Схемы для работы с уведомлениями

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str
    related_interview_id: Optional[int] = None
    related_vacancy_id: Optional[int] = None

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    
    class Config:
        orm_mode = True

class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int
    
    class Config:
        orm_mode = True
