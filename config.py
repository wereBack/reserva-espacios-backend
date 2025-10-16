"""
Configuración de la aplicación usando Pydantic v2
"""
import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings as PydanticBaseSettings


class Settings(PydanticBaseSettings):
    """Configuración principal de la aplicación"""
    
    # Configuración de la aplicación
    FLASK_APP_NAME: str = Field(default="Reserva Espacios Backend", description="Nombre de la aplicación")
    FLASK_APP_VERSION: str = Field(default="1.0.0", description="Versión de la aplicación")
    FLASK_DEBUG: bool = Field(default=False, description="Modo debug")
    FLASK_SECRET_KEY: str = Field("your-super-secret-key-please-change-me", description="Clave secreta para la aplicación.")
    
    # Configuración del servidor
    FLASK_HOST: str = Field(default="0.0.0.0", description="Host del servidor")
    FLASK_PORT: int = Field(default=5000, ge=1, le=65535, description="Puerto del servidor")
    
    # Configuración de la base de datos
    FLASK_DATABASE_URL: str = Field(pattern=r"^sqlite:///.*|postgresql://.*", default="sqlite:///reserva_espacios.db", description="URL de la base de datos")
    
    # Configuración de logging
    FLASK_LOG_LEVEL: str = Field(default="INFO", description="Nivel de logging")
    FLASK_LOG_FILE: Optional[str] = Field(default=None, description="Archivo de log")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
    
    @field_validator("FLASK_LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Valida el nivel de logging"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level debe ser uno de: {', '.join(valid_levels)}")
        return v.upper()

# Instancia global de configuración
settings = Settings()


def get_settings() -> Settings:
    """Función para obtener la configuración (útil para testing)"""
    return settings


# Configuración de desarrollo
class DevelopmentSettings(Settings):
    """Configuración específica para desarrollo"""
    FLASK_DEBUG: bool = True
    FLASK_LOG_LEVEL: str = "DEBUG"


# Configuración de producción
class ProductionSettings(Settings):
    """Configuración específica para producción"""
    FLASK_DEBUG: bool = False
    FLASK_LOG_LEVEL: str = "INFO"


# Configuración de testing
class TestingSettings(Settings):
    """Configuración específica para testing"""
    FLASK_DEBUG: bool = True
    FLASK_DATABASE_URL: str = "sqlite:///:memory:"
    FLASK_LOG_LEVEL: str = "DEBUG"


def get_settings_by_env(env: str = None) -> Settings:
    """Obtiene configuración basada en el entorno"""
    if env is None:
        env = os.getenv("FLASK_ENVIRONMENT", "development")
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()
