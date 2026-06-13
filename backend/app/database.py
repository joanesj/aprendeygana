from motor.motor_asyncio import AsyncIOMotorClient
import certifi
from app.core.config import settings

# Cliente global (se inicializa al arrancar la app)
client: AsyncIOMotorClient = None


def get_database():
    """Retorna la instancia de la base de datos."""
    return client[settings.DB_NAME]


async def connect_db():
    global client
    client = AsyncIOMotorClient(settings.MONGODB_URL, tlsCAFile=certifi.where())
    print(f"✅ Conectado a MongoDB: {settings.DB_NAME}")


async def close_db():
    global client
    if client:
        client.close()
        print("🔌 Conexión a MongoDB cerrada")


# ── Colecciones ────────────────────────────────────────────────
# Accesos rápidos a cada colección de la base de datos
def get_users_collection():
    return get_database()["users"]

def get_courses_collection():
    return get_database()["courses"]

def get_tasks_collection():
    return get_database()["tasks"]

def get_payments_collection():
    return get_database()["payments"]

def get_enrollments_collection():
    return get_database()["enrollments"]
