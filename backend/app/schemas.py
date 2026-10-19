from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr


# Auth schemas
class UserRegister(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# Plan Generation & Storage Schemas
class SubjectInput(BaseModel):
    name: str
    topics: List[str]


class PlanGenerateRequest(BaseModel):
    title: str
    exam_date: str
    subjects: List[SubjectInput]
    daily_hours: float = 2.0
    study_days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    preferred_slots: List[str] = ["Morning (09:00 - 11:00)", "Evening (18:00 - 20:00)"]
    unavailable_weeks: List[Dict[str, Any]] = []


class SessionItem(BaseModel):
    date: str
    time_slot: str
    subject: str
    topic: str
    duration_minutes: int
    actionable_task: Optional[str] = None


class PlanCreateRequest(BaseModel):
    title: str
    exam_date: str
    daily_hours: float
    preferred_slots: List[str]
    study_days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    subjects: List[SubjectInput]
    sessions: List[SessionItem]
    unavailable_weeks: List[Dict[str, Any]] = []


class SessionOut(BaseModel):
    id: int
    plan_id: int
    date: str
    time_slot: str
    subject: str
    topic: str
    duration_minutes: int
    actionable_task: Optional[str]
    status: str
    completed_at: Optional[str]


class PlanOut(BaseModel):
    id: int
    title: str
    exam_date: str
    daily_hours: float
    preferred_slots: List[str]
    study_days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    unavailable_weeks: List[Dict[str, Any]] = []
    status: str
    created_at: str
    total_sessions: int
    completed_sessions: int
    days_left: int



class GoalCreate(BaseModel):
    title: str
    target_hours: float = 10.0


class GoalOut(BaseModel):
    id: int
    title: str
    target_hours: float
    achieved_hours: float
    is_completed: bool
    created_at: str
