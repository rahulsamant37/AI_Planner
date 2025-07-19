# Test configuration and fixtures

import pytest
import asyncio
import redis
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    mock_client = MagicMock(spec=redis.Redis)
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.delete.return_value = True
    mock_client.exists.return_value = False
    mock_client.ping.return_value = True
    return mock_client

@pytest.fixture
def mock_groq_api():
    """Mock GROQ API responses"""
    mock_response = Mock()
    mock_response.content = """
# Day Trip Itinerary for Test City

## Morning (9:00 AM - 12:00 PM)
- Visit Test Museum
- Explore downtown area

## Afternoon (12:00 PM - 5:00 PM)  
- Lunch at local restaurant
- Visit Test Park

## Evening (5:00 PM - 9:00 PM)
- Dinner at recommended restaurant
- Evening stroll
"""
    return mock_response

@pytest.fixture
def sample_travel_data():
    """Sample travel planning data for tests"""
    return {
        "city": "Test City",
        "interests": ["museums", "parks", "food"],
        "expected_output": "Day Trip Itinerary for Test City"
    }
