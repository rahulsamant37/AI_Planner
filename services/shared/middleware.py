"""
Middleware for microservices
Provides common middleware for authentication, rate limiting, CORS, etc.
"""

from fastapi import Request, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import redis
from typing import Callable
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    def __init__(self, app, redis_client, requests_per_minute: int = 60):
        super().__init__(app)
        self.redis_client = redis_client
        self.requests_per_minute = requests_per_minute
        
    async def dispatch(self, request: Request, call_next: Callable):
        # Get client IP
        client_ip = request.client.host
        
        # Create rate limit key
        current_minute = int(time.time() / 60)
        rate_limit_key = f"rate_limit:{client_ip}:{current_minute}"
        
        # Get current request count
        current_requests = self.redis_client.get(rate_limit_key)
        
        if current_requests is None:
            # First request in this minute
            self.redis_client.setex(rate_limit_key, 60, 1)
        elif int(current_requests) >= self.requests_per_minute:
            # Rate limit exceeded
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": 60 - (int(time.time()) % 60)
                }
            )
        else:
            # Increment request count
            self.redis_client.incr(rate_limit_key)
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - int(current_requests or 0) - 1)
        )
        
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url}")
        
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """Circuit breaker pattern implementation"""
    
    def __init__(self, app, redis_client, failure_threshold: int = 5, recovery_timeout: int = 60):
        super().__init__(app)
        self.redis_client = redis_client
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
    async def dispatch(self, request: Request, call_next: Callable):
        service_key = f"circuit_breaker:{request.url.path}"
        
        # Check circuit breaker state
        breaker_data = self.redis_client.get(service_key)
        if breaker_data:
            breaker_info = json.loads(breaker_data)
            
            if breaker_info["state"] == "open":
                # Check if recovery timeout has passed
                if datetime.fromisoformat(breaker_info["last_failure"]) + timedelta(seconds=self.recovery_timeout) > datetime.now():
                    return JSONResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={"detail": "Service temporarily unavailable (Circuit Breaker Open)"}
                    )
                else:
                    # Move to half-open state
                    breaker_info["state"] = "half-open"
                    self.redis_client.set(service_key, json.dumps(breaker_info))
        
        try:
            response = await call_next(request)
            
            # Success - reset or keep circuit closed
            if response.status_code < 500:
                if breaker_data:
                    self.redis_client.delete(service_key)
            else:
                # Server error - count as failure
                self._record_failure(service_key)
                
            return response
            
        except Exception as e:
            # Exception - count as failure
            self._record_failure(service_key)
            raise e
    
    def _record_failure(self, service_key: str):
        """Record a failure and potentially open the circuit"""
        breaker_data = self.redis_client.get(service_key)
        
        if breaker_data:
            breaker_info = json.loads(breaker_data)
            breaker_info["failures"] += 1
            breaker_info["last_failure"] = datetime.now().isoformat()
            
            if breaker_info["failures"] >= self.failure_threshold:
                breaker_info["state"] = "open"
        else:
            breaker_info = {
                "failures": 1,
                "state": "closed",
                "last_failure": datetime.now().isoformat()
            }
        
        self.redis_client.setex(service_key, self.recovery_timeout * 2, json.dumps(breaker_info))

def setup_cors_middleware(app, origins: list = None):
    """Setup CORS middleware"""
    if origins is None:
        origins = ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
    )

def setup_common_middleware(app, redis_client, config: dict = None):
    """Setup all common middleware"""
    if config is None:
        config = {}
    
    # Rate limiting
    if config.get("enable_rate_limiting", True):
        app.add_middleware(
            RateLimitMiddleware,
            redis_client=redis_client,
            requests_per_minute=config.get("rate_limit_requests", 60)
        )
    
    # Circuit breaker
    if config.get("enable_circuit_breaker", True):
        app.add_middleware(
            CircuitBreakerMiddleware,
            redis_client=redis_client,
            failure_threshold=config.get("circuit_breaker_threshold", 5),
            recovery_timeout=config.get("circuit_breaker_timeout", 60)
        )
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request logging
    if config.get("enable_request_logging", True):
        app.add_middleware(RequestLoggingMiddleware)
    
    # CORS
    setup_cors_middleware(app, config.get("cors_origins"))
