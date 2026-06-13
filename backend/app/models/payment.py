from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class PaymentStatus(str, Enum):
    pending = "pending"         # Generado, pendiente de procesar
    processing = "processing"   # En proceso
    completed = "completed"     # Pagado exitosamente
    failed = "failed"           # Falló el pago


class PaymentMethod(str, Enum):
    platform_credit = "platform_credit"     # Crédito interno
    bank_transfer = "bank_transfer"         # Transferencia bancaria
    mobile_money = "mobile_money"           # Pago móvil (Nequi, etc.)
    paypal = "paypal"


# ── Pago en base de datos ──────────────────────────────────────

class PaymentInDB(BaseModel):
    user_id: str
    task_id: str
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    status: PaymentStatus = PaymentStatus.pending
    payment_method: Optional[PaymentMethod] = None
    transaction_id: Optional[str] = None       # ID externo del proveedor
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None


# ── Respuesta de pago ──────────────────────────────────────────

class PaymentResponse(BaseModel):
    id: str
    task_id: str
    amount: float
    currency: str
    status: PaymentStatus
    payment_method: Optional[PaymentMethod]
    created_at: datetime
    processed_at: Optional[datetime]


# ── Resumen de ingresos del usuario ───────────────────────────

class EarningsSummary(BaseModel):
    user_id: str
    total_earned: float
    total_pending: float
    total_tasks_completed: int
    avg_rating: float
    hardware_progress: dict   # % hacia elegibilidad de hardware
