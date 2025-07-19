"""
Unit tests for the TravelPlanner core functionality
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.core.planner import TravelPlanner
from src.utils.custom_exception import CustomException

class TestTravelPlanner:
    """Test cases for TravelPlanner class"""
    
    def test_planner_initialization(self):
        """Test TravelPlanner initialization"""
        planner = TravelPlanner()
        
        assert planner.messages == []
        assert planner.city == ""
        assert planner.interests == []
        assert planner.itineary == ""
    
    def test_set_city_success(self):
        """Test setting city successfully"""
        planner = TravelPlanner()
        city = "New York"
        
        planner.set_city(city)
        
        assert planner.city == city
        assert len(planner.messages) == 1
        assert planner.messages[0].content == city
    
    def test_set_city_exception(self):
        """Test set_city raises CustomException on error"""
        planner = TravelPlanner()
        
        # Mock the logger to raise an exception
        with patch('src.core.planner.logger') as mock_logger:
            with patch.object(planner, 'messages') as mock_messages:
                mock_messages.append.side_effect = Exception("Test error")
                
                with pytest.raises(CustomException):
                    planner.set_city("Test City")
    
    def test_set_interests_success(self):
        """Test setting interests successfully"""
        planner = TravelPlanner()
        interests_str = "museums, parks, food"
        
        planner.set_interests(interests_str)
        
        expected_interests = ["museums", "parks", "food"]
        assert planner.interests == expected_interests
        assert len(planner.messages) == 1
        assert planner.messages[0].content == interests_str
    
    def test_set_interests_with_spaces(self):
        """Test setting interests with extra spaces"""
        planner = TravelPlanner()
        interests_str = "  museums  ,  parks  ,  food  "
        
        planner.set_interests(interests_str)
        
        expected_interests = ["museums", "parks", "food"]
        assert planner.interests == expected_interests
    
    def test_set_interests_exception(self):
        """Test set_interests raises CustomException on error"""
        planner = TravelPlanner()
        
        with patch('src.core.planner.logger'):
            with patch.object(planner, 'messages') as mock_messages:
                mock_messages.append.side_effect = Exception("Test error")
                
                with pytest.raises(CustomException):
                    planner.set_interests("test interests")
    
    @patch('src.core.planner.generate_itineary')
    def test_create_itineary_success(self, mock_generate):
        """Test successful itinerary creation"""
        planner = TravelPlanner()
        planner.city = "Test City"
        planner.interests = ["museums", "parks"]
        
        mock_itinerary = "Test itinerary content"
        mock_generate.return_value = mock_itinerary
        
        result = planner.create_itineary()
        
        assert result == mock_itinerary
        assert planner.itineary == mock_itinerary
        assert len(planner.messages) == 1
        assert planner.messages[0].content == mock_itinerary
        
        mock_generate.assert_called_once_with("Test City", ["museums", "parks"])
    
    @patch('src.core.planner.generate_itineary')
    def test_create_itineary_exception(self, mock_generate):
        """Test create_itineary raises CustomException on error"""
        planner = TravelPlanner()
        planner.city = "Test City"
        planner.interests = ["museums"]
        
        mock_generate.side_effect = Exception("API Error")
        
        with pytest.raises(CustomException):
            planner.create_itineary()

class TestTravelPlannerIntegration:
    """Integration tests for TravelPlanner"""
    
    @patch('src.core.planner.generate_itineary')
    def test_full_planning_workflow(self, mock_generate):
        """Test complete planning workflow"""
        planner = TravelPlanner()
        
        # Mock the itinerary generation
        mock_itinerary = "# Day Trip for Paris\n\n## Morning\n- Visit Louvre"
        mock_generate.return_value = mock_itinerary
        
        # Complete workflow
        planner.set_city("Paris")
        planner.set_interests("museums, art, culture")
        result = planner.create_itineary()
        
        # Verify the complete state
        assert planner.city == "Paris"
        assert planner.interests == ["museums", "art", "culture"]
        assert planner.itineary == mock_itinerary
        assert result == mock_itinerary
        
        # Should have 3 messages: city, interests, and itinerary
        assert len(planner.messages) == 3
