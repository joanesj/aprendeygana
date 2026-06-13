from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
import uuid

from app.database import get_courses_collection, get_enrollments_collection, get_users_collection
from app.models.course import CourseCreate, CourseInDB, CourseResponse, ModuleCreate, ModuleInDB, EnrollmentInDB
from app.routes.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/courses", tags=["Cursos"])


# ── Helper ─────────────────────────────────────────────────────

def course_to_response(doc: dict, module_count: int = 0) -> CourseResponse:
    return CourseResponse(
        id=str(doc["_id"]),
        title=doc["title"],
        description=doc["description"],
        category=doc["category"],
        difficulty=doc["difficulty"],
        thumbnail_url=doc.get("thumbnail_url"),
        is_free=doc["is_free"],
        total_enrollments=doc.get("total_enrollments", 0),
        avg_rating=doc.get("avg_rating", 0.0),
        is_published=doc.get("is_published", False),
        module_count=module_count,
        created_at=doc["created_at"],
    )


# ══════════════════════════════════════════════════════════════
#  CURSOS
# ══════════════════════════════════════════════════════════════

@router.get("/", response_model=List[CourseResponse])
async def list_courses(
    category: Optional[str] = None,
    free_only: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """Lista todos los cursos publicados. Filtra por categoría o plan gratuito."""
    courses = get_courses_collection()
    query = {"is_published": True}

    if category:
        query["category"] = category
    if free_only:
        query["is_free"] = True

    result = []
    async for course in courses.find(query).sort("created_at", -1):
        result.append(course_to_response(course))
    return result


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(course_id: str, current_user: dict = Depends(get_current_user)):
    """Retorna el detalle de un curso específico."""
    courses = get_courses_collection()
    course = await courses.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return course_to_response(course)


@router.post("/", response_model=CourseResponse, status_code=201)
async def create_course(data: CourseCreate, admin: dict = Depends(get_admin_user)):
    """[Admin] Crea un nuevo curso."""
    courses = get_courses_collection()
    new_course = CourseInDB(**data.model_dump())
    result = await courses.insert_one(new_course.model_dump())
    created = await courses.find_one({"_id": result.inserted_id})
    return course_to_response(created)


@router.patch("/{course_id}/publish", response_model=CourseResponse)
async def publish_course(course_id: str, admin: dict = Depends(get_admin_user)):
    """[Admin] Publica un curso para que sea visible a los usuarios."""
    courses = get_courses_collection()
    course = await courses.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    await courses.update_one(
        {"_id": ObjectId(course_id)},
        {"$set": {"is_published": True, "updated_at": datetime.utcnow()}},
    )
    updated = await courses.find_one({"_id": ObjectId(course_id)})
    return course_to_response(updated)


# ══════════════════════════════════════════════════════════════
#  MÓDULOS
# ══════════════════════════════════════════════════════════════

@router.post("/{course_id}/modules", status_code=201)
async def add_module(course_id: str, data: ModuleCreate, admin: dict = Depends(get_admin_user)):
    """[Admin] Agrega un módulo a un curso existente."""
    courses = get_courses_collection()
    course = await courses.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    module = ModuleInDB(
        **data.model_dump(),
        id=str(uuid.uuid4()),
        course_id=course_id,
    )

    await courses.update_one(
        {"_id": ObjectId(course_id)},
        {"$push": {"modules": module.model_dump()}, "$set": {"updated_at": datetime.utcnow()}},
    )
    return {"message": "Módulo agregado", "module_id": module.id}


@router.get("/{course_id}/modules")
async def list_modules(course_id: str, current_user: dict = Depends(get_current_user)):
    """Lista los módulos de un curso. Solo si el usuario está inscrito."""
    courses = get_courses_collection()
    enrollments = get_enrollments_collection()

    course = await courses.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    enrollment = await enrollments.find_one({
        "user_id": str(current_user["_id"]),
        "course_id": course_id,
    })
    if not enrollment:
        raise HTTPException(status_code=403, detail="Debes inscribirte al curso primero")

    modules = sorted(course.get("modules", []), key=lambda m: m["order"])
    return modules


# ══════════════════════════════════════════════════════════════
#  INSCRIPCIONES Y PROGRESO
# ══════════════════════════════════════════════════════════════

@router.post("/{course_id}/enroll", status_code=201)
async def enroll_course(course_id: str, current_user: dict = Depends(get_current_user)):
    """Inscribe al usuario en un curso."""
    courses = get_courses_collection()
    enrollments = get_enrollments_collection()

    course = await courses.find_one({"_id": ObjectId(course_id), "is_published": True})
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado o no publicado")

    # Verificar si ya está inscrito
    existing = await enrollments.find_one({
        "user_id": str(current_user["_id"]),
        "course_id": course_id,
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya estás inscrito en este curso")

    enrollment = EnrollmentInDB(
        user_id=str(current_user["_id"]),
        course_id=course_id,
    )
    await enrollments.insert_one(enrollment.model_dump())

    # Incrementar contador de inscripciones
    await courses.update_one(
        {"_id": ObjectId(course_id)},
        {"$inc": {"total_enrollments": 1}},
    )
    return {"message": f"Inscrito exitosamente al curso: {course['title']}"}


@router.post("/{course_id}/modules/{module_id}/complete")
async def complete_module(
    course_id: str,
    module_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Marca un módulo como completado.
    Si todos los módulos del curso se completan, emite el certificado.
    """
    courses = get_courses_collection()
    enrollments = get_enrollments_collection()
    users = get_users_collection()

    course = await courses.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    enrollment = await enrollments.find_one({
        "user_id": str(current_user["_id"]),
        "course_id": course_id,
    })
    if not enrollment:
        raise HTTPException(status_code=403, detail="No estás inscrito en este curso")

    if module_id in enrollment.get("completed_modules", []):
        return {"message": "Módulo ya completado anteriormente"}

    # Marcar módulo como completado
    await enrollments.update_one(
        {"user_id": str(current_user["_id"]), "course_id": course_id},
        {"$push": {"completed_modules": module_id}},
    )

    # Actualizar módulos completados del usuario
    await users.update_one(
        {"_id": current_user["_id"]},
        {"$addToSet": {"completed_modules": module_id}},
    )

    # Verificar si completó todos los módulos del curso
    total_modules = len(course.get("modules", []))
    updated_enrollment = await enrollments.find_one({
        "user_id": str(current_user["_id"]),
        "course_id": course_id,
    })
    completed_count = len(updated_enrollment.get("completed_modules", []))

    if completed_count >= total_modules and total_modules > 0:
        await enrollments.update_one(
            {"user_id": str(current_user["_id"]), "course_id": course_id},
            {"$set": {
                "is_completed": True,
                "certificate_issued": True,
                "completed_at": datetime.utcnow(),
            }},
        )
        return {
            "message": "🎉 ¡Curso completado! Certificado emitido.",
            "certificate_issued": True,
            "modules_completed": completed_count,
        }

    return {
        "message": "Módulo completado",
        "modules_completed": completed_count,
        "total_modules": total_modules,
    }
