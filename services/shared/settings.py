from pydantic_settings import BaseSettings
from typing import Optional

class ServiceSettings(BaseSettings):
    """Shared settings for all microservices"""
    
    # Service identification
    service_name: str = "ai-planner"
    service_version: str = "1.0.0"
    environment: str = "production"
    
    # API Keys
    groq_api_key: Optional[str] = None
    
    # Redis Configuration
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    cache_ttl: int = 3600  # 1 hour
    
    # Elasticsearch Configuration
    elasticsearch_host: str = "elasticsearch"
    elasticsearch_port: int = 9200
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Health Check Configuration
    health_check_timeout: int = 30
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
