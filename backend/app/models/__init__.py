"""Public response entities. SQL persistence schema lives in migrations/."""
from typing import Any,Literal
from pydantic import BaseModel

class UserPublic(BaseModel):
    id:str
    name:str
    email:str
    created_at:str

class SessionPublic(BaseModel):
    access_token:str
    token_type:str
    expires_at:str
    user:UserPublic

class LessonPublic(BaseModel):
    id:str
    user_id:str
    title:str
    description:str
    created_at:str
    updated_at:str

class LessonListItem(LessonPublic):
    document_count:int
    chat_count:int

class LessonPage(BaseModel):
    items:list[LessonListItem]
    total:int
    limit:int
    offset:int

class DocumentPublic(BaseModel):
    id:str
    lesson_id:str
    filename:str
    media_type:str
    size_bytes:int
    status:Literal['pending','processing','ready','failed']
    content:str
    error_code:str|None
    source_mode:Literal['demo','production']
    created_at:str
    updated_at:str

class TranscriptPublic(BaseModel):
    id:str
    document_id:str
    content:str
    created_at:str

class AttemptBrief(BaseModel):
    id:str
    quiz_id:str
    lesson_id:str
    correct:int
    total:int
    score:float
    source_mode:str
    created_at:str

class ProgressPublic(BaseModel):
    attempts:int
    average_score:float
    best_score:float
    correct_answers:int
    answered_questions:int
    recent_attempts:list[AttemptBrief]
    flashcard_reviews:int

class LessonDetail(LessonPublic):
    documents:list[DocumentPublic]
    transcripts:list[TranscriptPublic]
    progress:ProgressPublic

class SummaryPublic(BaseModel):
    lesson_id:str
    summary:str
    key_points:list[str]
    source_mode:str
    updated_at:str

class ChatPublic(BaseModel):
    id:str
    lesson_id:str
    question:str
    answer:str
    sources:list[str]
    source_mode:str
    created_at:str

class ChatPage(BaseModel):
    items:list[ChatPublic]
    total:int
    limit:int
    offset:int

class CardPublic(BaseModel):
    id:str
    lesson_id:str
    question:str
    answer:str
    difficulty:str
    source_mode:str
    created_at:str

class CardPage(BaseModel):
    items:list[CardPublic]

class ReviewPublic(BaseModel):
    id:str
    flashcard_id:str
    user_id:str
    rating:str
    created_at:str

class QuestionPublic(BaseModel):
    id:str
    question:str
    options:list[str]

class QuizPublic(BaseModel):
    id:str
    lesson_id:str
    questions:list[QuestionPublic]
    source_mode:str
    created_at:str

class AttemptPublic(AttemptBrief):
    feedback:list[dict[str,Any]]

class HealthPublic(BaseModel):
    status:str
    database:str
    mode:str
    integrations:dict[str,str]
    version:str

class ErrorDetail(BaseModel):
    code:str
    message:str
    details:Any=None

class ErrorEnvelope(BaseModel):
    error:ErrorDetail
    request_id:str|None=None
