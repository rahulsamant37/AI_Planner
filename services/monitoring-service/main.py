"""
Monitoring and Health Check Service
Provides centralized health monitoring for all microservices
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel
import logging
import os

app = FastAPI(
    title="AI Planner Monitoring Service",
    description="Health monitoring and metrics collection for AI Planner microservices",
    version="1.0.0"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceHealth(BaseModel):
    service_name: str
    status: str
    response_time: float
    timestamp: datetime
    details: Dict[str, Any] = {}

class SystemHealth(BaseModel):
    overall_status: str
    services: List[ServiceHealth]
    timestamp: datetime

# Service endpoints to monitor
SERVICES = {
    "planner-service": "http://planner-service:8000/health",
    "frontend-service": "http://frontend-service:8501/_stcore/health",
    "redis": None,  # Custom health check
    "elasticsearch": "http://elasticsearch:9200/_cluster/health"
}

async def check_service_health(session: aiohttp.ClientSession, service_name: str, endpoint: str) -> ServiceHealth:
    """Check health of a single service"""
    start_time = datetime.now()
    
    try:
        if service_name == "redis":
            # Custom Redis health check
            import redis
            r = redis.Redis(host='redis', port=6379, decode_responses=True, socket_timeout=5)
            r.ping()
            status = "healthy"
            details = {"connected": True}
        else:
            async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as response:
                status = "healthy" if response.status == 200 else "unhealthy"
                details = {"status_code": response.status}
                
    except Exception as e:
        status = "unhealthy"
        details = {"error": str(e)}
    
    response_time = (datetime.now() - start_time).total_seconds()
    
    return ServiceHealth(
        service_name=service_name,
        status=status,
        response_time=response_time,
        timestamp=datetime.now(),
        details=details
    )

@app.get("/health")
async def health_check():
    """Health check for monitoring service itself"""
    return {"status": "healthy", "service": "monitoring-service", "timestamp": datetime.now()}

@app.get("/system/health", response_model=SystemHealth)
async def system_health():
    """Get overall system health status"""
    health_checks = []
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for service_name, endpoint in SERVICES.items():
            task = check_service_health(session, service_name, endpoint)
            tasks.append(task)
        
        health_checks = await asyncio.gather(*tasks)
    
    # Determine overall status
    unhealthy_services = [h for h in health_checks if h.status != "healthy"]
    overall_status = "unhealthy" if unhealthy_services else "healthy"
    
    return SystemHealth(
        overall_status=overall_status,
        services=health_checks,
        timestamp=datetime.now()
    )

@app.get("/system/metrics")
async def system_metrics():
    """Get system metrics"""
    metrics = {}
    
    try:
        # Redis metrics
        import redis
        r = redis.Redis(host='redis', port=6379, decode_responses=True)
        redis_info = r.info()
        metrics["redis"] = {
            "connected_clients": redis_info.get("connected_clients", 0),
            "used_memory": redis_info.get("used_memory_human", "0B"),
            "keyspace_hits": redis_info.get("keyspace_hits", 0),
            "keyspace_misses": redis_info.get("keyspace_misses", 0)
        }
    except Exception as e:
        metrics["redis"] = {"error": str(e)}
    
    try:
        # Elasticsearch metrics
        async with aiohttp.ClientSession() as session:
            async with session.get("http://elasticsearch:9200/_cluster/stats") as response:
                if response.status == 200:
                    es_stats = await response.json()
                    metrics["elasticsearch"] = {
                        "cluster_name": es_stats.get("cluster_name", "unknown"),
                        "status": es_stats.get("status", "unknown"),
                        "indices_count": es_stats.get("indices", {}).get("count", 0),
                        "docs_count": es_stats.get("indices", {}).get("docs", {}).get("count", 0)
                    }
    except Exception as e:
        metrics["elasticsearch"] = {"error": str(e)}
    
    return metrics

@app.get("/services/{service_name}/health")
async def service_specific_health(service_name: str):
    """Get health status for a specific service"""
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")
    
    endpoint = SERVICES[service_name]
    async with aiohttp.ClientSession() as session:
        health = await check_service_health(session, service_name, endpoint)
    
    return health

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
