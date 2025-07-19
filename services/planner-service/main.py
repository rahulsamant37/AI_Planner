from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import redis
import json
import hashlib
from datetime import datetime, timedelta
import logging

# Import existing planner logic
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.planner import TravelPlanner
from src.utils.logger import get_logger
from src.utils.custom_exception import CustomException

app = FastAPI(
    title="AI Travel Planner Service",
    description="Microservice for generating travel itineraries",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection for caching
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
logger = get_logger(__name__)

class PlannerRequest(BaseModel):
    city: str
    interests: str

class PlannerResponse(BaseModel):
    itinerary: str
    city: str
    interests: List[str]
    cached: bool = False
    generated_at: datetime

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    service: str

def get_cache_key(city: str, interests: str) -> str:
    """Generate a cache key for the request"""
    data = f"{city.lower()}:{interests.lower()}"
    return hashlib.md5(data.encode()).hexdigest()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        service="planner-service"
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "AI Travel Planner Service", "version": "1.0.0"}

@app.post("/generate-itinerary", response_model=PlannerResponse)
async def generate_itinerary(request: PlannerRequest):
    """Generate travel itinerary"""
    try:
        logger.info(f"Received request for city: {request.city}, interests: {request.interests}")
        
        # Check cache first
        cache_key = get_cache_key(request.city, request.interests)
        cached_result = redis_client.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for key: {cache_key}")
            cached_data = json.loads(cached_result)
            return PlannerResponse(
                itinerary=cached_data['itinerary'],
                city=cached_data['city'],
                interests=cached_data['interests'],
                cached=True,
                generated_at=datetime.fromisoformat(cached_data['generated_at'])
            )
        
        # Generate new itinerary using existing logic
        planner = TravelPlanner()
        planner.set_city(request.city)
        planner.set_interests(request.interests)
        itinerary = planner.create_itineary()
        
        interests_list = [i.strip() for i in request.interests.split(",")]
        response_data = {
            "itinerary": itinerary,
            "city": request.city,
            "interests": interests_list,
            "cached": False,
            "generated_at": datetime.now().isoformat()
        }
        
        # Cache the result for 1 hour
        redis_client.setex(cache_key, 3600, json.dumps(response_data, default=str))
        logger.info(f"Cached result with key: {cache_key}")
        
        return PlannerResponse(**response_data)
        
    except CustomException as e:
        logger.error(f"Custom exception: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics"""
    try:
        info = redis_client.info()
        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory_human", "0B"),
            "keyspace": redis_client.dbsize()
        }
    except Exception as e:
        return {"error": str(e)}

@app.delete("/cache/clear")
async def clear_cache():
    """Clear all cache"""
    try:
        redis_client.flushdb()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
