"""Tests for ServiceRegistry integration."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from kafka_viz.models.service import Service
from kafka_viz.models.service_registry import ServiceRegistry, AnalysisResult, ServiceRelationship
from kafka_viz.analyzers.analyzer_manager import AnalyzerManager
from kafka_viz.analyzers.spring_analyzer import SpringCloudStreamAnalyzer

@pytest.fixture
def service_registry():
    return ServiceRegistry()

@pytest.fixture
def analyzer_manager():
    return AnalyzerManager()

def test_service_registration(service_registry):
    # Test basic service registration
    service = Service(name="test-service", root_path=Path("/test"))
    service_registry.register_service(service)
    assert "test-service" in service_registry.services
    assert service_registry.services["test-service"] == service

def test_service_relationship(service_registry):
    # Test relationship tracking
    service_registry.add_relationship("service-a", "service-b", "kafka")
    relationships = service_registry.get_relationships("service-a")
    assert len(relationships) == 1
    assert relationships[0].source == "service-a"
    assert relationships[0].target == "service-b"
    assert relationships[0].type == "kafka"

def test_analysis_result_application(service_registry):
    # Test applying analysis results
    result = AnalysisResult("service-a")
    result.discovered_services["service-b"] = Service(name="service-b")
    result.service_relationships.append(
        ServiceRelationship("service-a", "service-b", "spring-dependency")
    )
    
    service_registry.apply_analysis_result(result)
    assert "service-b" in service_registry.services
    assert len(service_registry.get_relationships("service-a")) == 1

def test_spring_analyzer_integration(analyzer_manager):
    # Test Spring analyzer integration with registry
    with patch('pathlib.Path.read_text') as mock_read:
        # Mock a Spring Boot application file
        mock_read.return_value = """
        @SpringBootApplication
        @EnableBinding(MyChannels.class)
        public class Application {
            @Autowired
            private UserService userService;
        }
        """
        
        # Create a test service
        service = Service(name="test-service", root_path=Path("/test"))
        analyzer_manager.service_registry.register_service(service)
        
        # Analyze with Spring analyzer
        analyzer = SpringCloudStreamAnalyzer()
        result = analyzer.analyze(Path("/test/Application.java"), service)
        
        # Check if dependencies were discovered
        assert "user-service" in result.discovered_services
        assert any(r.type == "spring-dependency" for r in result.service_relationships)

def test_service_discovery_integration(analyzer_manager, tmp_path):
    # Create a mock project structure
    java_project = tmp_path / "java-service"
    java_project.mkdir()
    (java_project / "pom.xml").write_text("<groupId>test</groupId><artifactId>java-service</artifactId>")
    
    # Test service discovery
    analyzer_manager.discover_services(tmp_path)
    assert "java-service" in analyzer_manager.service_registry.services

def test_duplicate_service_handling(service_registry):
    # Test handling of duplicate service registrations
    service1 = Service(name="test", root_path=Path("/test1"))
    service2 = Service(name="test", root_path=Path("/test2"))
    
    service_registry.register_service(service1)
    service_registry.register_service(service2)
    
    # Should use the latest path but maintain existing relationships/topics
    assert service_registry.services["test"].root_path == Path("/test2")

def test_service_dependency_tracking(service_registry):
    # Test service dependency tracking
    service_registry.add_relationship("app", "db", "spring-dependency")
    service_registry.add_relationship("app", "cache", "spring-dependency")
    
    deps = service_registry.get_service_dependencies("app")
    assert deps == {"db", "cache"}
    
    dependents = service_registry.get_service_dependents("db")
    assert dependents == {"app"}

def test_topic_merging(service_registry):
    # Test merging of topic information from different analyzers
    result1 = AnalysisResult("service-a")
    result1.topics["topic1"] = Mock(producers={"service-a"}, consumers=set())
    
    result2 = AnalysisResult("service-b")
    result2.topics["topic1"] = Mock(producers=set(), consumers={"service-b"})
    
    service_registry.apply_analysis_result(result1)
    service_registry.apply_analysis_result(result2)
    
    # Get service-a and check its topics
    service_a = service_registry.get_or_create_service("service-a")
    assert "topic1" in service_a.topics
    assert "service-a" in service_a.topics["topic1"].producers
    assert "service-b" in service_a.topics["topic1"].consumers
