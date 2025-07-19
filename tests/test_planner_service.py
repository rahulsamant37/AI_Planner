"""
Tests for planner microservice API
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'planner-service'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@patch('redis.Redis')
@patch('services.planner-service.main.TravelPlanner')
class TestPlannerService:
    """Test cases for planner service API"""
    
    def test_health_check(self, mock_planner, mock_redis):
        """Test health check endpoint"""
        from main import app
        client = TestClient(app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "planner-service"
    
    def test_root_endpoint(self, mock_planner, mock_redis):
        """Test root endpoint"""
        from main import app
        client = TestClient(app)
        
        response = client.get("/")
        
        assert response.status_code == 200
        assert "AI Travel Planner Service" in response.json()["message"]
    
    def test_generate_itinerary_success(self, mock_planner, mock_redis):
        """Test successful itinerary generation"""
        from main import app
        
        # Mock Redis cache miss
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = None
        mock_redis_instance.setex.return_value = True
        
        # Mock TravelPlanner
        mock_planner_instance = MagicMock()
        mock_planner.return_value = mock_planner_instance
        mock_planner_instance.create_itineary.return_value = "Test itinerary"
        
        client = TestClient(app)
        
        request_data = {
            "city": "Paris",
            "interests": "museums, art, culture"
        }
        
        response = client.post("/generate-itinerary", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Paris"
        assert data["interests"] == ["museums", "art", "culture"]
        assert data["itinerary"] == "Test itinerary"
        assert data["cached"] == False
    
    def test_generate_itinerary_cached(self, mock_planner, mock_redis):
        """Test itinerary generation from cache"""
        from main import app
        
        # Mock Redis cache hit
        cached_data = {
            "itinerary": "Cached itinerary",
            "city": "Paris",
            "interests": ["museums"],
            "generated_at": "2024-01-01T12:00:00"
        }
        
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = json.dumps(cached_data)
        
        client = TestClient(app)
        
        request_data = {
            "city": "Paris",
            "interests": "museums"
        }
        
        response = client.post("/generate-itinerary", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["cached"] == True
        assert data["itinerary"] == "Cached itinerary"
    
    def test_cache_stats(self, mock_planner, mock_redis):
        """Test cache statistics endpoint"""
        from main import app
        
        # Mock Redis info
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.info.return_value = {
            "connected_clients": 5,
            "used_memory_human": "1.5MB",
        }
        mock_redis_instance.dbsize.return_value = 10
        
        client = TestClient(app)
        
        response = client.get("/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["connected_clients"] == 5
        assert data["used_memory"] == "1.5MB"
        assert data["keyspace"] == 10
    
    def test_clear_cache(self, mock_planner, mock_redis):
        """Test cache clearing endpoint"""
        from main import app
        
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.flushdb.return_value = True
        
        client = TestClient(app)
        
        response = client.delete("/cache/clear")
        
        assert response.status_code == 200
        assert "cleared successfully" in response.json()["message"]
    
    def test_generate_itinerary_custom_exception(self, mock_planner, mock_redis):
        """Test handling of CustomException"""
        from main import app
        from src.utils.custom_exception import CustomException
        
        # Mock Redis cache miss
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = None
        
        # Mock TravelPlanner to raise CustomException
        mock_planner_instance = MagicMock()
        mock_planner.return_value = mock_planner_instance
        mock_planner_instance.create_itineary.side_effect = CustomException("Test error")
        
        client = TestClient(app)
        
        request_data = {
            "city": "Paris",
            "interests": "museums"
        }
        
        response = client.post("/generate-itinerary", json=request_data)
        
        assert response.status_code == 400
        assert "Test error" in response.json()["detail"]
    
    def test_generate_itinerary_server_error(self, mock_planner, mock_redis):
        """Test handling of unexpected exceptions"""
        from main import app
        
        # Mock Redis cache miss
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = None
        
        # Mock TravelPlanner to raise unexpected exception
        mock_planner_instance = MagicMock()
        mock_planner.return_value = mock_planner_instance
        mock_planner_instance.create_itineary.side_effect = Exception("Unexpected error")
        
        client = TestClient(app)
        
        request_data = {
            "city": "Paris",
            "interests": "museums"
        }
        
        response = client.post("/generate-itinerary", json=request_data)
        
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
