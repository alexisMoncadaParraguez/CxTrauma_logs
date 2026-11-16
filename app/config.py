"""Configuración de la aplicación, leída desde variables de entorno (o `.env`)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Formato "combined" de Apache: %h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-agent}i"
COMBINED_REGEX = (
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+)? ?(?P<path>\S+)? ?\S*" (?P<status>\d{3}) \S+'
    r'(?: "(?P<referer>[^"]*)" "(?P<ua>[^"]*)")?'
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_token: str = ""

    # Logs de Apache (montados en solo lectura en el contenedor)
    apache_log_glob: str = "/logs/access.log*"
    log_format_regex: str = COMBINED_REGEX
    zona_horaria: str = "America/Santiago"

    # Listas de IP
    data_dir: Path = Path("/data")
    incluir_aws: bool = False
    timeout_descarga: float = 30.0

    # Google Data Manager API → Google Analytics 4
    ga4_property_id: str = ""
    ga4_measurement_id: str = ""
    google_application_credentials: str = "/secrets/service-account.json"
    dm_validate_only: bool = True
    dm_endpoint: str = "https://datamanager.googleapis.com/v1/events:ingest"
    dm_event_name: str = "bot_traffic_daily"

    # Job diario
    scheduler_activo: bool = True
    hora_envio: str = "11:00"

    @property
    def sources_dir(self) -> Path:
        return self.data_dir / "sources"

    @property
    def envios_path(self) -> Path:
        return self.data_dir / "envios.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
