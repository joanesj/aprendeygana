from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base de datos
    MONGODB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "aprendeyemprende"

    # JWT
    SECRET_KEY: str = "cambia_esto_en_produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # App
    APP_NAME: str = "AprendeYEmprende API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
