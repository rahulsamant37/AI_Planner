"""
Configuration Service for AI Planner
Centralized configuration management for all microservices
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import redis
import json
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis for configuration storage
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
security = HTTPBearer()

app = FastAPI(
    title="AI Planner Configuration Service",
    description="Centralized configuration management",
    version="1.0.0"
)

class ConfigItem(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    environment: str = "production"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ConfigUpdate(BaseModel):
    value: Any
    description: Optional[str] = None

class FeatureFlag(BaseModel):
    name: str
    enabled: bool
    description: Optional[str] = None
    rollout_percentage: float = Field(default=100.0, ge=0.0, le=100.0)
    target_audience: List[str] = []

# Default configurations
DEFAULT_CONFIGS = {
    "rate_limiting.api.requests_per_minute": 100,
    "rate_limiting.frontend.requests_per_minute": 300,
    "cache.ttl_seconds": 3600,
    "llm.temperature": 0.3,
    "llm.max_tokens": 2000,
    "monitoring.health_check_interval": 30,
    "logging.level": "INFO",
    "security.jwt_expiry_minutes": 30,
    "api.timeout_seconds": 30,
    "circuit_breaker.failure_threshold": 5,
    "circuit_breaker.recovery_timeout": 60
}

DEFAULT_FEATURE_FLAGS = {
    "enable_caching": {"enabled": True, "description": "Enable Redis caching"},
    "enable_auth": {"enabled": False, "description": "Enable authentication"},
    "enable_rate_limiting": {"enabled": True, "description": "Enable API rate limiting"},
    "enable_metrics": {"enabled": True, "description": "Enable metrics collection"},
    "experimental_llm_model": {"enabled": False, "description": "Use experimental LLM model"}
}

@app.on_event("startup")
async def initialize_configs():
    """Initialize default configurations if they don't exist"""
    try:
        # Initialize default configs
        for key, value in DEFAULT_CONFIGS.items():
            if not redis_client.exists(f"config:{key}"):
                config_item = ConfigItem(
                    key=key,
                    value=value,
                    description=f"Default configuration for {key}",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                redis_client.set(f"config:{key}", json.dumps(config_item.dict(), default=str))
        
        # Initialize default feature flags
        for name, flag_data in DEFAULT_FEATURE_FLAGS.items():
            if not redis_client.exists(f"feature_flag:{name}"):
                feature_flag = FeatureFlag(
                    name=name,
                    enabled=flag_data["enabled"],
                    description=flag_data["description"]
                )
                redis_client.set(f"feature_flag:{name}", json.dumps(feature_flag.dict()))
        
        logger.info("Configuration service initialized with defaults")
    except Exception as e:
        logger.error(f"Failed to initialize configs: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "config-service", "timestamp": datetime.utcnow()}

@app.get("/config")
async def get_all_configs():
    """Get all configuration items"""
    configs = {}
    
    for key in redis_client.scan_iter(match="config:*"):
        config_key = key.replace("config:", "")
        config_data = redis_client.get(key)
        if config_data:
            configs[config_key] = json.loads(config_data)
    
    return {"configs": configs}

@app.get("/config/{key}")
async def get_config(key: str):
    """Get a specific configuration item"""
    config_data = redis_client.get(f"config:{key}")
    
    if not config_data:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return json.loads(config_data)

@app.post("/config/{key}")
async def create_config(key: str, config_update: ConfigUpdate):
    """Create or update a configuration item"""
    existing_config = redis_client.get(f"config:{key}")
    
    if existing_config:
        # Update existing
        existing_data = json.loads(existing_config)
        existing_data["value"] = config_update.value
        existing_data["updated_at"] = datetime.utcnow().isoformat()
        if config_update.description:
            existing_data["description"] = config_update.description
        
        redis_client.set(f"config:{key}", json.dumps(existing_data))
        return {"message": "Configuration updated", "key": key}
    else:
        # Create new
        config_item = ConfigItem(
            key=key,
            value=config_update.value,
            description=config_update.description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        redis_client.set(f"config:{key}", json.dumps(config_item.dict(), default=str))
        return {"message": "Configuration created", "key": key}

@app.delete("/config/{key}")
async def delete_config(key: str):
    """Delete a configuration item"""
    if not redis_client.exists(f"config:{key}"):
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    redis_client.delete(f"config:{key}")
    return {"message": "Configuration deleted", "key": key}

@app.get("/feature-flags")
async def get_all_feature_flags():
    """Get all feature flags"""
    flags = {}
    
    for key in redis_client.scan_iter(match="feature_flag:*"):
        flag_name = key.replace("feature_flag:", "")
        flag_data = redis_client.get(key)
        if flag_data:
            flags[flag_name] = json.loads(flag_data)
    
    return {"feature_flags": flags}

@app.get("/feature-flags/{name}")
async def get_feature_flag(name: str):
    """Get a specific feature flag"""
    flag_data = redis_client.get(f"feature_flag:{name}")
    
    if not flag_data:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    
    return json.loads(flag_data)

@app.post("/feature-flags/{name}")
async def create_or_update_feature_flag(name: str, feature_flag: FeatureFlag):
    """Create or update a feature flag"""
    feature_flag.name = name
    redis_client.set(f"feature_flag:{name}", json.dumps(feature_flag.dict()))
    return {"message": "Feature flag updated", "name": name}

@app.delete("/feature-flags/{name}")
async def delete_feature_flag(name: str):
    """Delete a feature flag"""
    if not redis_client.exists(f"feature_flag:{name}"):
        raise HTTPException(status_code=404, detail="Feature flag not found")
    
    redis_client.delete(f"feature_flag:{name}")
    return {"message": "Feature flag deleted", "name": name}

@app.get("/config/service/{service_name}")
async def get_service_config(service_name: str):
    """Get configuration for a specific service"""
    service_configs = {}
    
    # Get all configs that might be relevant to this service
    for key in redis_client.scan_iter(match="config:*"):
        config_key = key.replace("config:", "")
        config_data = redis_client.get(key)
        if config_data:
            # Include configs that are general or specific to this service
            if service_name in config_key or any(prefix in config_key for prefix in ["rate_limiting", "cache", "logging", "api", "llm"]):
                service_configs[config_key] = json.loads(config_data)
    
    # Get relevant feature flags
    feature_flags = {}
    for key in redis_client.scan_iter(match="feature_flag:*"):
        flag_name = key.replace("feature_flag:", "")
        flag_data = redis_client.get(key)
        if flag_data:
            feature_flags[flag_name] = json.loads(flag_data)
    
    return {
        "service": service_name,
        "configs": service_configs,
        "feature_flags": feature_flags
    }

@app.post("/config/reload/{service_name}")
async def trigger_config_reload(service_name: str):
    """Trigger configuration reload for a service"""
    # In a real implementation, this would send a message to the service
    # For now, we'll just log it
    logger.info(f"Configuration reload triggered for service: {service_name}")
    
    # Publish reload event to Redis pub/sub
    redis_client.publish(f"config_reload:{service_name}", json.dumps({
        "event": "config_reload",
        "service": service_name,
        "timestamp": datetime.utcnow().isoformat()
    }))
    
    return {"message": f"Configuration reload triggered for {service_name}"}

@app.get("/config/environments")
async def get_environments():
    """Get all available environments"""
    environments = set()
    
    for key in redis_client.scan_iter(match="config:*"):
        config_data = redis_client.get(key)
        if config_data:
            config = json.loads(config_data)
            environments.add(config.get("environment", "production"))
    
    return {"environments": list(environments)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
