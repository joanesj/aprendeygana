from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class TaskStatus(str, Enum):
    open = "open"               # Disponible para aplicar
    in_progress = "in_progress" # Asignada a un usuario
    in_review = "in_review"     # Entregada, esperando aprobación
    completed = "completed"     # Aprobada y pagada
    cancelled = "cancelled"     # Cancelada


class TaskCategory(str, Enum):
    customer_service = "customer_service"
    design = "design"
    tech_support = "tech_support"
    ai_tools = "ai_tools"
    data_entry = "data_entry"
    translation = "translation"


# ── Creación de tarea ──────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=150)
    description: str
    category: TaskCategory
    required_course_id: str             # Curso que debe completar para aplicar
    payment_amount: float = Field(..., gt=0)    # Pago en USD
    estimated_hours: float = Field(..., gt=0)   # Horas estimadas
    deadline_hours: int = Field(..., gt=0)      # Horas para entregar desde asignación
    max_applicants: int = Field(default=5, ge=1)


# ── Tarea en base de datos ─────────────────────────────────────

class TaskInDB(TaskCreate):
    status: TaskStatus = TaskStatus.open
    assigned_to: Optional[str] = None      # user_id del trabajador
    posted_by: Optional[str] = None        # user_id del admin/cliente
    applicants: List[str] = []             # user_ids que aplicaron
    submission_url: Optional[str] = None   # Enlace a la entrega
    submission_notes: Optional[str] = None
    client_feedback: Optional[str] = None
    client_rating: Optional[float] = None  # 1-5 estrellas
    assigned_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Respuestas ─────────────────────────────────────────────────

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    category: TaskCategory
    required_course_id: str
    payment_amount: float
    estimated_hours: float
    deadline_hours: int
    status: TaskStatus
    assigned_to: Optional[str]
    applicants_count: int = 0
    created_at: datetime


class TaskSubmission(BaseModel):
    submission_url: str
    submission_notes: Optional[str] = None


class TaskReview(BaseModel):
    approved: bool
    feedback: Optional[str] = None
    rating: Optional[float] = Field(None, ge=1, le=5)
