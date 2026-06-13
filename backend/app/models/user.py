from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    student = "student"
    admin = "admin"


class HardwareStatus(str, Enum):
    not_eligible = "not_eligible"   # Aún no califica
    eligible = "eligible"           # Ya puede aplicar
    applied = "applied"             # Aplicó al programa
    approved = "approved"           # Aprobado, laptop en camino


# ── Esquemas de entrada (lo que el cliente envía) ──────────────

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6)
    country: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ── Esquema interno (lo que se guarda en MongoDB) ──────────────

class UserInDB(BaseModel):
    name: str
    email: str
    hashed_password: str
    role: UserRole = UserRole.student
    country: Optional[str] = None
    is_active: bool = True

    # Progreso en la plataforma
    completed_modules: List[str] = []   # IDs de módulos completados
    total_earnings: float = 0.0         # Ingresos acumulados en USD
    rating: float = 0.0                 # Calificación promedio (0-5)
    total_reviews: int = 0

    # Programa de hardware
    hardware_status: HardwareStatus = HardwareStatus.not_eligible

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── Esquema de respuesta (lo que el servidor devuelve) ─────────

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    country: Optional[str]
    is_active: bool
    completed_modules: List[str]
    total_earnings: float
    rating: float
    hardware_status: HardwareStatus
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
