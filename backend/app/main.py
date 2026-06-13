from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import connect_db, close_db
from app.routes import auth, courses, tasks, payments

# ── Crear aplicación ───────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API Backend para la plataforma AprendeYEmprende",
    docs_url="/docs",       # Documentación automática en /docs
    redoc_url="/redoc",
)

# ── CORS: permite que el frontend (HTML/JS) se comunique ───────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # En producción pon la URL exacta del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Eventos de inicio y cierre ─────────────────────────────────
@app.on_event("startup")
async def startup():
    await connect_db()

@app.on_event("shutdown")
async def shutdown():
    await close_db()

# ── Registrar todas las rutas ──────────────────────────────────
app.include_router(auth.router,     prefix="/v1")
app.include_router(courses.router,  prefix="/v1")
app.include_router(tasks.router,    prefix="/v1")
app.include_router(payments.router, prefix="/v1")

# ── Ruta raíz de verificación ──────────────────────────────────
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "✅ Servidor corriendo",
        "docs": "/docs",
    }
