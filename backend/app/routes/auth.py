from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from bson import ObjectId

from app.database import get_users_collection
from app.models.user import UserRegister, UserInDB, UserResponse, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Helper: convertir documento MongoDB a UserResponse ────────

def user_to_response(doc: dict) -> UserResponse:
    return UserResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        email=doc["email"],
        role=doc["role"],
        country=doc.get("country"),
        is_active=doc["is_active"],
        completed_modules=doc.get("completed_modules", []),
        total_earnings=doc.get("total_earnings", 0.0),
        rating=doc.get("rating", 0.0),
        hardware_status=doc.get("hardware_status", "not_eligible"),
        created_at=doc["created_at"],
    )


# ── Dependency: obtener usuario autenticado ────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Verifica el token JWT y retorna el usuario de la base de datos."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    users = get_users_collection()
    user = await users.find_one({"email": payload.get("sub")})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not user.get("is_active"):
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return user


async def get_admin_user(current_user: dict = Depends(get_current_user)):
    """Solo permite acceso a administradores."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return current_user


# ══════════════════════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: UserRegister):
    """
    Registra un nuevo usuario en la plataforma.
    - Verifica que el email no esté en uso
    - Hashea la contraseña
    - Genera un token JWT al instante
    """
    users = get_users_collection()

    # Verificar email único
    existing = await users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    # Crear documento del usuario
    new_user = UserInDB(
        name=data.name,
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        country=data.country,
    )

    result = await users.insert_one(new_user.model_dump())
    created = await users.find_one({"_id": result.inserted_id})

    token = create_access_token({"sub": created["email"]})
    return TokenResponse(access_token=token, user=user_to_response(created))


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """
    Inicia sesión con email y contraseña.
    Retorna un token JWT para usar en las demás rutas.
    """
    users = get_users_collection()
    user = await users.find_one({"email": form.username.lower()})

    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    if not user.get("is_active"):
        raise HTTPException(status_code=400, detail="Cuenta desactivada")

    token = create_access_token({"sub": user["email"]})
    return TokenResponse(access_token=token, user=user_to_response(user))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna los datos del usuario autenticado."""
    return user_to_response(current_user)
