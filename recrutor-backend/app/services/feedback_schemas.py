from pydantic import BaseModel, Field
from typing import Optional

class FeedbackCreate(BaseModel):
    hr_rating: int = Field(..., ge=1, le=5, description="Оценка HR от 1 до 5")
    hr_comment: Optional[str] = Field(None, description="Комментарий HR")
    is_successful: Optional[bool] = Field(None, description="Кандидат принят/отклонён")

class FeedbackOut(BaseModel):
    id: int
    analysis_id: int
    hr_rating: int
    hr_comment: Optional[str]
    is_successful: Optional[bool]
    created_at: str

    class Config:
        orm_mode = True
