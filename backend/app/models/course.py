from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class DifficultyLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class CourseCategory(str, Enum):
    customer_service = "customer_service"   # Atención al cliente
    design = "design"                       # Diseño básico
    tech_support = "tech_support"           # Soporte técnico
    ai_tools = "ai_tools"                   # IA operativa
    freelancing = "freelancing"             # Trabajo remoto


# ── Módulo (unidad dentro de un curso) ────────────────────────

class ModuleCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    description: str
    video_url: Optional[str] = None         # URL del video (bajo consumo)
    content_text: Optional[str] = None      # Texto alternativo sin video
    duration_minutes: int = Field(..., gt=0)
    order: int = Field(..., ge=1)           # Posición dentro del curso


class ModuleInDB(ModuleCreate):
    id: str
    course_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Curso ──────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str
    category: CourseCategory
    difficulty: DifficultyLevel = DifficultyLevel.beginner
    thumbnail_url: Optional[str] = None
    is_free: bool = True                    # Disponible en plan básico


class CourseInDB(CourseCreate):
    total_enrollments: int = 0
    avg_rating: float = 0.0
    total_reviews: int = 0
    is_published: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CourseResponse(BaseModel):
    id: str
    title: str
    description: str
    category: CourseCategory
    difficulty: DifficultyLevel
    thumbnail_url: Optional[str]
    is_free: bool
    total_enrollments: int
    avg_rating: float
    is_published: bool
    module_count: int = 0
    created_at: datetime


# ── Inscripción de usuario a curso ────────────────────────────

class EnrollmentInDB(BaseModel):
    user_id: str
    course_id: str
    completed_modules: List[str] = []       # IDs de módulos terminados
    is_completed: bool = False
    certificate_issued: bool = False
    enrolled_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
