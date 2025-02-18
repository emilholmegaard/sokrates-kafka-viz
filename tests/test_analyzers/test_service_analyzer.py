import pytest
from pathlib import Path
from unittest.mock import mock_open, patch, MagicMock
from kafka_viz.analyzers.service_analyzer import ServiceAnalyzer
from kafka_viz.models.service import Service
from kafka_viz.models.service_registry import AnalysisResult

@pytest.fixture
def service_analyzer():
    return ServiceAnalyzer()

@pytest.fixture
def mock_path():
    return Path("/mock/path")

def test_analyze_python_service(service_analyzer):
    """Test Python service dependency analysis."""
    service = Service(name="test-service", root_path=Path("/mock/path"))
    result = AnalysisResult(affected_service="test-service")
    
    requirements_content = """flask>=2.0.0
auth-service-client>=1.0.0
database-api~=2.1.0
pytest>=6.0.0"""
    
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.read_text") as mock_read_text:
        
        mock_exists.return_value = True
        mock_read_text.return_value = requirements_content
        
        service_analyzer._analyze_python_service(service, result)
        
        # Verify relationships were created
        assert len(result.service_relationships) == 2  # auth-service-client and database-api
        relationships = {r.target: r for r in result.service_relationships}
        assert "auth-service-client" in relationships
        assert "database-api" in relationships
        assert all(r.type == "python-dependency" for r in result.service_relationships)

def test_analyze_python_service_with_spaces(service_analyzer):
    """Test Python service dependency analysis with various spacing."""
    service = Service(name="test-service", root_path=Path("/mock/path"))
    result = AnalysisResult(affected_service="test-service")
    
    requirements_content = """
    flask>=2.0.0
auth-service-client >= 1.0.0
  database-api ~= 2.1.0
pytest>=6.0.0
"""
    
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.read_text") as mock_read_text:
        
        mock_exists.return_value = True
        mock_read_text.return_value = requirements_content
        
        service_analyzer._analyze_python_service(service, result)
        
        assert len(result.service_relationships) == 2
        relationships = {r.target: r for r in result.service_relationships}
        assert "auth-service-client" in relationships
        assert "database-api" in relationships

# ... [rest of the test file remains the same] ...