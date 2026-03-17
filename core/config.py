import os
import yaml
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    name: str = "SiliconDNA"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"


class MongoDBConfig(BaseModel):
    uri: str = "mongodb://localhost:27017"
    database_name: str = "silicon_dna"
    connection_pool: int = 10
    server_selection_timeout_ms: int = 5000
    connect_timeout_ms: int = 5000


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5


class RethinkDBConfig(BaseModel):
    host: str = "localhost"
    port: int = 28015
    database: str = "silicon_dna"


class DatabaseConfig(BaseModel):
    mongodb: MongoDBConfig = Field(default_factory=MongoDBConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    rethinkdb: RethinkDBConfig = Field(default_factory=RethinkDBConfig)


class SecurityConfig(BaseModel):
    bot_token: str = ""
    owner_ids: List[str] = Field(default_factory=list)
    guild_id: Optional[str] = None


class MLConfig(BaseModel):
    dry_run_mode: bool = True
    retrain_interval_seconds: int = 3600
    model_storage_path: str = "./models"
    shadow_testing: bool = True
    max_model_age_hours: int = 24


class PerformanceConfig(BaseModel):
    max_concurrent_operations: int = 5
    command_timeout_seconds: int = 30
    graceful_shutdown_timeout: int = 10
    rate_limit_per_minute: int = 60


class FeaturesConfig(BaseModel):
    hot_reload_enabled: bool = True
    metrics_dashboard: bool = True
    colored_logging: bool = True


class SiliconDNAConfig(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    ml: MLConfig = Field(default_factory=MLConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DATABASE: str = "silicon_dna"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    RETHINKDB_HOST: str = "localhost"
    RETHINKDB_PORT: int = 28015
    RETHINKDB_DATABASE: str = "silicon_dna"
    BOT_TOKEN: str = ""
    OWNER_ID_1: str = ""
    GUILD_ID: Optional[str] = None
    ML_DRY_RUN: str = "true"
    ML_RETRAIN_INTERVAL: int = 3600
    MODEL_STORAGE_PATH: str = "./models"
    APP_ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"


def load_config(config_path: Optional[str] = None) -> SiliconDNAConfig:
    """Load configuration from YAML and environment variables."""
    settings = Settings()

    config_data = {}
    if config_path and Path(config_path).exists():
        with open(config_path, "r") as f:
            yaml_content = f.read()

        for key, value in settings.model_dump().items():
            if value:
                yaml_content = yaml_content.replace(f"${{{key}}}", str(value))

        config_data = yaml.safe_load(yaml_content) or {}

    config_data.setdefault("app", {})
    config_data["app"].setdefault("name", "SiliconDNA")
    config_data["app"].setdefault("version", "0.1.0")
    config_data["app"]["environment"] = settings.APP_ENVIRONMENT
    config_data["app"]["log_level"] = settings.LOG_LEVEL

    config_data.setdefault("database", {})
    config_data["database"].setdefault("mongodb", {})
    config_data["database"]["mongodb"]["uri"] = settings.MONGO_URI
    config_data["database"]["mongodb"]["database_name"] = settings.MONGO_DATABASE

    config_data["database"].setdefault("redis", {})
    config_data["database"]["redis"]["host"] = settings.REDIS_HOST
    config_data["database"]["redis"]["port"] = settings.REDIS_PORT
    config_data["database"]["redis"]["db"] = settings.REDIS_DB

    config_data["database"].setdefault("rethinkdb", {})
    config_data["database"]["rethinkdb"]["host"] = settings.RETHINKDB_HOST
    config_data["database"]["rethinkdb"]["port"] = settings.RETHINKDB_PORT
    config_data["database"]["rethinkdb"]["database"] = settings.RETHINKDB_DATABASE

    config_data.setdefault("security", {})
    config_data["security"]["bot_token"] = settings.BOT_TOKEN
    config_data["security"]["owner_ids"] = (
        [settings.OWNER_ID_1] if settings.OWNER_ID_1 else []
    )
    config_data["security"]["guild_id"] = settings.GUILD_ID

    config_data.setdefault("ml", {})
    config_data["ml"]["dry_run_mode"] = settings.ML_DRY_RUN.lower() == "true"
    config_data["ml"]["retrain_interval_seconds"] = settings.ML_RETRAIN_INTERVAL
    config_data["ml"]["model_storage_path"] = settings.MODEL_STORAGE_PATH

    config_data.setdefault("performance", {})
    config_data.setdefault("features", {})

    return SiliconDNAConfig(**config_data)


config: Optional[SiliconDNAConfig] = None


def get_config(config_path: Optional[str] = None) -> SiliconDNAConfig:
    """Get the global configuration instance."""
    global config
    if config is None:
        config = load_config(config_path)
    return config
