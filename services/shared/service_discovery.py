"""
Service discovery and communication utilities
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
import json
import logging
from datetime import datetime
import redis

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """Service discovery registry using Redis"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 30  # Service registration TTL in seconds
    
    def register_service(self, service_name: str, host: str, port: int, 
                        health_check_url: str = None, metadata: Dict = None):
        """Register a service"""
        service_info = {
            "service_name": service_name,
            "host": host,
            "port": port,
            "health_check_url": health_check_url or f"http://{host}:{port}/health",
            "registered_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        service_key = f"service:{service_name}:{host}:{port}"
        self.redis.setex(service_key, self.ttl, json.dumps(service_info))
        
        # Add to service list
        self.redis.sadd(f"services:{service_name}", service_key)
        
        logger.info(f"Registered service {service_name} at {host}:{port}")
    
    def discover_service(self, service_name: str) -> List[Dict[str, Any]]:
        """Discover all instances of a service"""
        services = []
        service_keys = self.redis.smembers(f"services:{service_name}")
        
        for key in service_keys:
            service_data = self.redis.get(key)
            if service_data:
                try:
                    services.append(json.loads(service_data))
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode service data for {key}")
            else:
                # Remove expired service from set
                self.redis.srem(f"services:{service_name}", key)
        
        return services
    
    def get_service_endpoint(self, service_name: str) -> Optional[str]:
        """Get a random service endpoint (simple load balancing)"""
        services = self.discover_service(service_name)
        if services:
            import random
            service = random.choice(services)
            return f"http://{service['host']}:{service['port']}"
        return None
    
    def deregister_service(self, service_name: str, host: str, port: int):
        """Deregister a service"""
        service_key = f"service:{service_name}:{host}:{port}"
        self.redis.delete(service_key)
        self.redis.srem(f"services:{service_name}", service_key)
        
        logger.info(f"Deregistered service {service_name} at {host}:{port}")

class ServiceClient:
    """HTTP client for inter-service communication"""
    
    def __init__(self, service_registry: ServiceRegistry, timeout: int = 30):
        self.registry = service_registry
        self.timeout = timeout
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def call_service(self, service_name: str, endpoint: str, 
                          method: str = "GET", data: Any = None, 
                          headers: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """Make HTTP call to a service"""
        service_url = self.registry.get_service_endpoint(service_name)
        if not service_url:
            logger.error(f"Service {service_name} not found in registry")
            return None
        
        url = f"{service_url}{endpoint}"
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )
            
            kwargs = {
                "method": method,
                "url": url,
                "headers": headers or {}
            }
            
            if data:
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    kwargs["json"] = data
                else:
                    kwargs["params"] = data
            
            async with self.session.request(**kwargs) as response:
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return {"status": response.status, "text": await response.text()}
                    
        except aiohttp.ClientError as e:
            logger.error(f"Error calling service {service_name} at {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling service {service_name}: {e}")
            return None

class EventBus:
    """Redis-based event bus for microservices communication"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self._subscribers = {}
    
    def publish_event(self, event_type: str, data: Dict[str, Any], 
                     source_service: str = None):
        """Publish an event"""
        event = {
            "event_type": event_type,
            "data": data,
            "source_service": source_service,
            "timestamp": datetime.utcnow().isoformat(),
            "event_id": f"{event_type}_{int(datetime.utcnow().timestamp())}"
        }
        
        channel = f"events:{event_type}"
        self.redis.publish(channel, json.dumps(event, default=str))
        
        # Also store in event log
        self.redis.lpush("event_log", json.dumps(event, default=str))
        self.redis.ltrim("event_log", 0, 1000)  # Keep last 1000 events
        
        logger.info(f"Published event {event_type} from {source_service}")
    
    def subscribe_to_events(self, event_types: List[str], callback):
        """Subscribe to specific event types"""
        channels = [f"events:{event_type}" for event_type in event_types]
        
        pubsub = self.redis.pubsub()
        pubsub.subscribe(*channels)
        
        for event_type in event_types:
            self._subscribers[event_type] = callback
        
        return pubsub
    
    def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent event history"""
        events = []
        event_data = self.redis.lrange("event_log", 0, limit - 1)
        
        for event_json in event_data:
            try:
                events.append(json.loads(event_json))
            except json.JSONDecodeError:
                logger.error("Failed to decode event from history")
        
        return events

class CircuitBreaker:
    """Circuit breaker for service calls"""
    
    def __init__(self, redis_client, failure_threshold: int = 5, 
                 recovery_timeout: int = 60):
        self.redis = redis_client
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
    
    def is_open(self, service_name: str) -> bool:
        """Check if circuit breaker is open for a service"""
        breaker_data = self.redis.get(f"circuit_breaker:{service_name}")
        
        if breaker_data:
            try:
                breaker_info = json.loads(breaker_data)
                return breaker_info.get("state") == "open"
            except json.JSONDecodeError:
                return False
        
        return False
    
    def record_success(self, service_name: str):
        """Record successful service call"""
        self.redis.delete(f"circuit_breaker:{service_name}")
    
    def record_failure(self, service_name: str):
        """Record failed service call"""
        breaker_key = f"circuit_breaker:{service_name}"
        breaker_data = self.redis.get(breaker_key)
        
        if breaker_data:
            try:
                breaker_info = json.loads(breaker_data)
                breaker_info["failures"] += 1
            except json.JSONDecodeError:
                breaker_info = {"failures": 1, "state": "closed"}
        else:
            breaker_info = {"failures": 1, "state": "closed"}
        
        if breaker_info["failures"] >= self.failure_threshold:
            breaker_info["state"] = "open"
            breaker_info["opened_at"] = datetime.utcnow().isoformat()
        
        self.redis.setex(breaker_key, self.recovery_timeout, 
                        json.dumps(breaker_info, default=str))

async def health_check_services(service_registry: ServiceRegistry) -> Dict[str, bool]:
    """Check health of all registered services"""
    health_status = {}
    
    # Get all services
    service_names = set()
    for key in service_registry.redis.scan_iter(match="services:*"):
        service_name = key.split(":")[1]
        service_names.add(service_name)
    
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=10)
    ) as session:
        tasks = []
        
        for service_name in service_names:
            services = service_registry.discover_service(service_name)
            for service_info in services:
                task = check_single_service_health(
                    session, service_name, service_info["health_check_url"]
                )
                tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, dict):
                    health_status.update(result)
    
    return health_status

async def check_single_service_health(session: aiohttp.ClientSession, 
                                    service_name: str, health_url: str) -> Dict[str, bool]:
    """Check health of a single service"""
    try:
        async with session.get(health_url) as response:
            is_healthy = response.status == 200
            return {service_name: is_healthy}
    except Exception:
        return {service_name: False}
