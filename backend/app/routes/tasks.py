from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from app.database import get_tasks_collection, get_users_collection, get_enrollments_collection
from app.models.task import TaskCreate, TaskInDB, TaskResponse, TaskSubmission, TaskReview
from app.routes.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/tasks", tags=["Micro-Tareas"])


def task_to_response(doc: dict) -> TaskResponse:
    return TaskResponse(
        id=str(doc["_id"]),
        title=doc["title"],
        description=doc["description"],
        category=doc["category"],
        required_course_id=doc["required_course_id"],
        payment_amount=doc["payment_amount"],
        estimated_hours=doc["estimated_hours"],
        deadline_hours=doc["deadline_hours"],
        status=doc["status"],
        assigned_to=doc.get("assigned_to"),
        applicants_count=len(doc.get("applicants", [])),
        created_at=doc["created_at"],
    )


# ── Listar tareas disponibles ──────────────────────────────────

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Lista todas las tareas abiertas disponibles."""
    tasks = get_tasks_collection()
    query = {"status": "open"}
    if category:
        query["category"] = category

    result = []
    async for task in tasks.find(query).sort("created_at", -1):
        result.append(task_to_response(task))
    return result


@router.get("/my-tasks", response_model=List[TaskResponse])
async def my_tasks(current_user: dict = Depends(get_current_user)):
    """Retorna las tareas asignadas al usuario autenticado."""
    tasks = get_tasks_collection()
    result = []
    async for task in tasks.find({"assigned_to": str(current_user["_id"])}):
        result.append(task_to_response(task))
    return result


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """Detalle de una tarea específica."""
    tasks = get_tasks_collection()
    task = await tasks.find_one({"_id": ObjectId(task_id)})
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task_to_response(task)


# ── Crear tarea (solo admin) ───────────────────────────────────

@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, admin: dict = Depends(get_admin_user)):
    """[Admin] Crea una nueva micro-tarea disponible en la bolsa."""
    tasks = get_tasks_collection()
    new_task = TaskInDB(**data.model_dump(), posted_by=str(admin["_id"]))
    result = await tasks.insert_one(new_task.model_dump())
    created = await tasks.find_one({"_id": result.inserted_id})
    return task_to_response(created)


# ── Aplicar a una tarea ────────────────────────────────────────

@router.post("/{task_id}/apply")
async def apply_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """
    Aplica a una tarea disponible.
    Verifica que el usuario haya completado el curso requerido.
    """
    tasks = get_tasks_collection()
    enrollments = get_enrollments_collection()

    task = await tasks.find_one({"_id": ObjectId(task_id), "status": "open"})
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no disponible")

    user_id = str(current_user["_id"])

    # Verificar que completó el curso requerido
    enrollment = await enrollments.find_one({
        "user_id": user_id,
        "course_id": task["required_course_id"],
        "is_completed": True,
    })
    if not enrollment:
        raise HTTPException(
            status_code=403,
            detail=f"Debes completar el curso requerido antes de aplicar a esta tarea",
        )

    # Verificar que no aplicó ya
    if user_id in task.get("applicants", []):
        raise HTTPException(status_code=400, detail="Ya aplicaste a esta tarea")

    # Si hay cupo, asignar directamente
    if len(task.get("applicants", [])) < task["max_applicants"]:
        await tasks.update_one(
            {"_id": ObjectId(task_id)},
            {
                "$push": {"applicants": user_id},
                "$set": {
                    "assigned_to": user_id,
                    "status": "in_progress",
                    "assigned_at": datetime.utcnow(),
                },
            },
        )
        return {"message": "¡Tarea asignada! Tienes plazo para entregarla.", "task_id": task_id}

    raise HTTPException(status_code=400, detail="No hay cupos disponibles para esta tarea")


# ── Entregar tarea ─────────────────────────────────────────────

@router.post("/{task_id}/submit")
async def submit_task(
    task_id: str,
    data: TaskSubmission,
    current_user: dict = Depends(get_current_user),
):
    """El usuario entrega su trabajo para revisión."""
    tasks = get_tasks_collection()
    user_id = str(current_user["_id"])

    task = await tasks.find_one({
        "_id": ObjectId(task_id),
        "assigned_to": user_id,
        "status": "in_progress",
    })
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no te pertenece")

    await tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {
            "status": "in_review",
            "submission_url": data.submission_url,
            "submission_notes": data.submission_notes,
            "submitted_at": datetime.utcnow(),
        }},
    )
    return {"message": "Entrega recibida. Esperando revisión del cliente."}


# ── Revisar y aprobar tarea (admin) ───────────────────────────

@router.post("/{task_id}/review")
async def review_task(
    task_id: str,
    data: TaskReview,
    admin: dict = Depends(get_admin_user),
):
    """
    [Admin] Aprueba o rechaza la entrega de una tarea.
    Si aprueba, el pago se acredita al usuario automáticamente.
    """
    tasks = get_tasks_collection()
    users = get_users_collection()

    task = await tasks.find_one({"_id": ObjectId(task_id), "status": "in_review"})
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no está en revisión")

    if data.approved:
        # Acreditar pago al usuario
        await users.update_one(
            {"_id": ObjectId(task["assigned_to"])},
            {"$inc": {"total_earnings": task["payment_amount"]}},
        )
        await tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "status": "completed",
                "client_feedback": data.feedback,
                "client_rating": data.rating,
                "completed_at": datetime.utcnow(),
            }},
        )
        return {"message": f"Tarea aprobada. Se acreditaron ${task['payment_amount']} al usuario."}
    else:
        # Devolver a in_progress para que rehaga
        await tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "status": "in_progress",
                "client_feedback": data.feedback,
            }},
        )
        return {"message": "Tarea rechazada. El usuario debe corregir y volver a entregar."}
