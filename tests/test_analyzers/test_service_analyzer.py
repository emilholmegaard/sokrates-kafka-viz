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

def test_init():
    """Test initialization of ServiceAnalyzer."""
    analyzer = ServiceAnalyzer()
    assert "java" in analyzer.build_patterns
    assert "javascript" in analyzer.build_patterns
    assert "python" in analyzer.build_patterns
    assert "csharp" in analyzer.build_patterns
    assert len(analyzer.name_extractors) == 4
    assert "test" in analyzer.test_dirs

def test_detect_service_java(service_analyzer, mock_path):
    """Test Java service detection."""
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.is_dir") as mock_is_dir, \
         patch.object(service_analyzer, "_extract_service_name") as mock_extract_name, \
         patch.object(service_analyzer, "_create_service") as mock_create_service:
        
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_extract_name.return_value = "test-service"
        mock_service = Service(name="test-service", root_path=mock_path)
        mock_create_service.return_value = mock_service

        service = service_analyzer._detect_service(mock_path)
        
        assert service is not None
        assert service.name == "test-service"
        mock_extract_name.assert_called_once()
        mock_create_service.assert_called_once()

def test_detect_service_no_build_file(service_analyzer, mock_path):
    """Test service detection with no build files."""
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.is_dir") as mock_is_dir:
        
        mock_exists.return_value = False
        mock_is_dir.return_value = True

        service = service_analyzer._detect_service(mock_path)
        assert service is None

def test_create_service(service_analyzer, mock_path):
    """Test service creation."""
    with patch("pathlib.Path.rglob") as mock_rglob:
        mock_rglob.return_value = [
            Path("/mock/path/src/main.py"),
            Path("/mock/path/src/utils.py"),
            Path("/mock/path/tests/test_main.py")
        ]
        
        service = service_analyzer._create_service(
            mock_path, 
            "test-service", 
            "python", 
            mock_path / "pyproject.toml"
        )
        
        assert service.name == "test-service"
        assert service.language == "python"
        assert len(service.source_files) == 2  # Excludes test file

def test_analyze_python_service(service_analyzer):
    """Test Python service dependency analysis."""
    service = Service(name="test-service", root_path=Path("/mock/path"))
    result = AnalysisResult(affected_service="test-service")
    
    requirements_content = "flask>=2.0.0\nauth-service-client>=1.0.0\ndatabase-api~=2.1.0\npytest>=6.0.0"
    
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

def test_analyze_python_service_no_dependencies(service_analyzer):
    """Test Python service analysis with no service dependencies."""
    service = Service(name="test-service", root_path=Path("/mock/path"))
    result = AnalysisResult(affected_service="test-service")
    
    requirements_content = "flask>=2.0.0\npytest>=6.0.0\nrequests==2.26.0"
    
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.read_text") as mock_read_text:
        
        mock_exists.return_value = True
        mock_read_text.return_value = requirements_content
        
        service_analyzer._analyze_python_service(service, result)
        assert len(result.service_relationships) == 0

def test_analyze_python_service_malformed_requirements(service_analyzer):
    """Test Python service analysis with malformed requirements."""
    service = Service(name="test-service", root_path=Path("/mock/path"))
    result = AnalysisResult(affected_service="test-service")
    
    requirements_content = "malformed==content\nauth-service-client"  # Missing version spec
    
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.read_text") as mock_read_text:
        
        mock_exists.return_value = True
        mock_read_text.return_value = requirements_content
        
        service_analyzer._analyze_python_service(service, result)
        assert len(result.service_relationships) == 0  # Should handle malformed content gracefully

def test_analyze_java_service(service_analyzer):
    """Test Java service dependency analysis."""
    service = Service(name="test-service", root_path=Path("/mock/path"))
    result = AnalysisResult(affected_service="test-service")
    
    pom_content = "<dependencies><dependency><groupId>org.springframework.cloud</groupId></dependency></dependencies>"
    application_yaml = "services:\n  auth-service.url=http://auth-service:8080\n  data-service.url=http://data-service:8080"
    
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.read_text") as mock_read_text:
        
        mock_exists.return_value = True
        # First call returns pom_content, second returns application_yaml
        mock_read_text.side_effect = [pom_content, application_yaml]
        
        service_analyzer._analyze_java_service(service, result)
        
        assert len(result.service_relationships) == 2
        relationships = {r.target: r for r in result.service_relationships}
        assert "auth-service" in relationships
        assert "data-service" in relationships
        assert all(r.type == "spring-cloud" for r in result.service_relationships)

def test_find_services_integration(service_analyzer, tmp_path):
    """Integration test for finding services in a directory structure."""
    # Create mock service directory structure
    service1_dir = tmp_path / "service1"
    service1_dir.mkdir()
    (service1_dir / "pom.xml").write_text("<project></project>")
    
    service2_dir = tmp_path / "service2"
    service2_dir.mkdir()
    (service2_dir / "package.json").write_text('{"name": "service2"}')
    
    with patch.object(service_analyzer, "_extract_service_name") as mock_extract_name:
        mock_extract_name.side_effect = ["service1", "service2"]
        
        result = service_analyzer.find_services(tmp_path)
        
        assert len(result.discovered_services) == 2
        assert "service1" in result.discovered_services
        assert "service2" in result.discovered_services

def test_extract_service_name_fallback(service_analyzer, mock_path):
    """Test service name extraction fallback behavior."""
    with patch.object(service_analyzer.name_extractors["python"], "extract") as mock_extract:
        mock_extract.side_effect = Exception("Extraction failed")
        
        name = service_analyzer._extract_service_name(
            mock_path / "pyproject.toml", 
            "python"
        )
        
        assert name == mock_path.name

def test_get_debug_info(service_analyzer):
    """Test debug information retrieval."""
    debug_info = service_analyzer.get_debug_info()
    
    assert "supported_languages" in debug_info
    assert "test_directories" in debug_info
    assert "analyzer_type" in debug_info
    assert debug_info["status"] == "active"
    assert len(debug_info["supported_languages"]) == 4
