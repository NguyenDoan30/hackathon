from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Register(Input):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128, json_schema_extra={'writeOnly': True})
    @field_validator('password', mode='before')
    @classmethod
    def preserve_password(cls, value):
        # Disable inherited whitespace stripping specifically for passwords.
        return value
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=False)
    @field_validator('name')
    @classmethod
    def name_not_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Tên không được để trống')
        return value

class Login(Input):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=False)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128, json_schema_extra={'writeOnly': True})

class LessonCreate(Input):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default='', max_length=2000)

class LessonUpdate(Input):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    @field_validator('title','description', mode='before')
    @classmethod
    def no_null(cls, value):
        if value is None:
            raise ValueError('Không truyền null; bỏ qua trường nếu không cập nhật')
        return value

class ChatInput(Input):
    lesson_id: str
    question: str = Field(min_length=1, max_length=4000)

class Review(Input):
    rating: Literal['again','hard','good','easy']

class QuizSubmit(Input):
    answers: dict[str, str] = Field(max_length=50)

class ProcessedFile(Input):
    content: str = Field(min_length=1, max_length=1000000)
    transcript: str | None = Field(default=None, max_length=1000000)

class SummaryResult(Input):
    summary: str = Field(min_length=1, max_length=100000)
    key_points: list[str] = Field(max_length=100)

class AnswerResult(Input):
    answer: str = Field(min_length=1, max_length=100000)
    sources: list[str] = Field(default_factory=list, max_length=100)

class CardResult(Input):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=10000)
    difficulty: Literal['easy','medium','hard'] = 'medium'

class QuestionResult(Input):
    id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=2000)
    options: list[str] = Field(min_length=2, max_length=6)
    answer: str = Field(min_length=1, max_length=2000)
    explanation: str = Field(min_length=1, max_length=10000)

class GradeResult(Input):
    correct: int = Field(ge=0)
    total: int = Field(ge=1)
    score: float = Field(ge=0, le=100, allow_inf_nan=False)
    feedback: list[dict] = Field(max_length=50)
