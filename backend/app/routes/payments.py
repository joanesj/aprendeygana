from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from app.database import get_payments_collection, get_users_collection
from app.models.payment import PaymentInDB, PaymentResponse, EarningsSummary
from app.routes.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/payments", tags=["Pagos"])


def payment_to_response(doc: dict) -> PaymentResponse:
    return PaymentResponse(
        id=str(doc["_id"]),
        task_id=doc["task_id"],
        amount=doc["amount"],
        currency=doc.get("currency", "USD"),
        status=doc["status"],
        payment_method=doc.get("payment_method"),
        created_at=doc["created_at"],
        processed_at=doc.get("processed_at"),
    )


# ── Historial de pagos del usuario ────────────────────────────

@router.get("/my-payments", response_model=List[PaymentResponse])
async def my_payments(current_user: dict = Depends(get_current_user)):
    """Retorna el historial de pagos del usuario autenticado."""
    payments = get_payments_collection()
    result = []
    async for payment in payments.find(
        {"user_id": str(current_user["_id"])}
    ).sort("created_at", -1):
        result.append(payment_to_response(payment))
    return result


# ── Resumen de ingresos ────────────────────────────────────────

@router.get("/my-earnings", response_model=EarningsSummary)
async def my_earnings(current_user: dict = Depends(get_current_user)):
    """
    Retorna el resumen de ingresos del usuario:
    total ganado, pendiente y progreso hacia el hardware.
    """
    payments = get_payments_collection()
    user_id = str(current_user["_id"])

    # Total ganado (pagos completados)
    total_earned = 0.0
    async for p in payments.find({"user_id": user_id, "status": "completed"}):
        total_earned += p["amount"]

    # Total pendiente
    total_pending = 0.0
    async for p in payments.find({"user_id": user_id, "status": "pending"}):
        total_pending += p["amount"]

    # Progreso hardware (meta: $50.00)
    HARDWARE_GOAL = 50.0
    hardware_progress = {
        "current": total_earned,
        "goal": HARDWARE_GOAL,
        "percentage": min(round((total_earned / HARDWARE_GOAL) * 100, 1), 100),
        "eligible": total_earned >= HARDWARE_GOAL,
    }

    return EarningsSummary(
        user_id=user_id,
        total_earned=total_earned,
        total_pending=total_pending,
        total_tasks_completed=current_user.get("tasksCompleted", 0),
        avg_rating=current_user.get("rating", 0.0),
        hardware_progress=hardware_progress,
    )


# ── Crear pago (interno, llamado al aprobar tarea) ─────────────

@router.post("/create")
async def create_payment(
    user_id: str,
    task_id: str,
    amount: float,
    admin: dict = Depends(get_admin_user),
):
    """[Admin] Registra un pago al completar una tarea."""
    payments = get_payments_collection()

    new_payment = PaymentInDB(
        user_id=user_id,
        task_id=task_id,
        amount=amount,
    )
    result = await payments.insert_one(new_payment.model_dump())
    return {"message": "Pago registrado", "payment_id": str(result.inserted_id)}


# ── Procesar pago pendiente (admin) ───────────────────────────

@router.patch("/{payment_id}/process")
async def process_payment(payment_id: str, admin: dict = Depends(get_admin_user)):
    """[Admin] Marca un pago como procesado/completado."""
    payments = get_payments_collection()

    payment = await payments.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if payment["status"] == "completed":
        raise HTTPException(status_code=400, detail="Este pago ya fue procesado")

    await payments.update_one(
        {"_id": ObjectId(payment_id)},
        {"$set": {"status": "completed", "processed_at": datetime.utcnow()}},
    )
    return {"message": "Pago procesado exitosamente"}
