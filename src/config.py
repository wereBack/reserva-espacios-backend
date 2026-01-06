"""
Configuración de la aplicación usando Pydantic v2
Documentación de Pydantic: https://docs.pydantic.dev/2.12/concepts/pydantic_settings/
"""
from typing import Optional
from pydantic import Field, field_validator, PostgresDsn
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

    # Configuración de logging
    FLASK_LOG_LEVEL: str = Field(default="INFO", description="Nivel de logging")
    FLASK_LOG_FILE: Optional[str] = Field(default=None, description="Archivo de log")
    
    # Configuración de base de datos
    DATABASE_URL: PostgresDsn = Field(default="postgresql://postgres:postgres@localhost:5432/reserva_espacios_um", description="URL de conexión a la base de datos")
    DATABASE_ECHO: bool = Field(default=False, description="Mostrar queries SQL en logs")
    DATABASE_POOL_SIZE: int = Field(default=5, ge=1, le=20, description="Tamaño del pool de conexiones")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=30, description="Overflow máximo del pool")
    
    # Configuración de AWS S3
    AWS_ACCESS_KEY_ID: str = Field(default="AKIAIOSFODNN7EXAMPLE", description="AWS Access Key ID")
    AWS_SECRET_ACCESS_KEY: str = Field(default="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", description="AWS Secret Access Key")
    AWS_S3_BUCKET_NAME: str = Field(default="reserva-espacios-um", description="Nombre del bucket S3")
    AWS_S3_REGION: str = Field(default="us-east-1", description="Región de AWS S3")
    
    # Configuración de Keycloak para autenticación
    # KEYCLOAK_URL: URL interna para conectarse a Keycloak (obtener claves publicas)
    #   - En Docker: http://keycloak:8080
    #   - Local: http://localhost:8080
    # KEYCLOAK_ISSUER_URL: URL del issuer en los tokens (como el navegador ve a Keycloak)
    #   - Generalmente: http://localhost:8080
    KEYCLOAK_URL: str = Field(default="http://keycloak:8080", description="URL interna para conectarse a Keycloak")
    KEYCLOAK_ISSUER_URL: str = Field(default="http://localhost:8080", description="URL del issuer en los tokens")
    KEYCLOAK_REALM: str = Field(default="reserva-espacios", description="Nombre del realm de Keycloak")
    KEYCLOAK_CLIENT_ID: str = Field(default="front-admin", description="Client ID de la aplicación en Keycloak")

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
    DATABASE_URL: str = "sqlite:///:memory:"
    DATABASE_ECHO: bool = False
    FLASK_LOG_LEVEL: str = "DEBUG"


# Instancia global de configuración
settings = Settings()
