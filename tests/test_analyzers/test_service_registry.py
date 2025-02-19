"""Tests for ServiceRegistry integration."""

# Standard library imports
from pathlib import Path

# Third-party imports
import pytest

# Local application imports
from kafka_viz.analyzers.analyzer_manager import AnalyzerManager
from kafka_viz.analyzers.spring_analyzer import SpringCloudStreamAnalyzer
from kafka_viz.models.schema import KafkaTopic
from kafka_viz.models.service import Service
from kafka_viz.models.service_registry import (
    AnalysisResult,
    ServiceRegistry,
    ServiceRelationship,
)


@pytest.fixture
def service_registry() -> ServiceRegistry:
    return ServiceRegistry()


@pytest.fixture
def analyzer_manager() -> AnalyzerManager:
    return AnalyzerManager()


def test_service_registration(service_registry: ServiceRegistry) -> None:
    # Test basic service registration
    service = Service(name="test-service", root_path=Path("/test"))
    service_registry.register_service(service)
    assert "test-service" in service_registry.services
    assert service_registry.services["test-service"] == service


def test_service_relationship(service_registry: ServiceRegistry) -> None:
    # Test relationship tracking
    service_registry.add_relationship("service-a", "service-b", "kafka")
    relationships = service_registry.get_relationships("service-a")
    assert len(relationships) == 1
    assert relationships[0].source == "service-a"
    assert relationships[0].target == "service-b"
    assert relationships[0].type == "kafka"


def test_analysis_result_application(service_registry: ServiceRegistry) -> None:
    # Test applying analysis results
    result = AnalysisResult("service-a")
    result.discovered_services["service-b"] = Service(
        name="service-b", root_path=Path("/test")
    )
    result.service_relationships.append(
        ServiceRelationship("service-a", "service-b", "spring-dependency")
    )

    service_registry.apply_analysis_result(result)
    assert "service-b" in service_registry.services
    assert len(service_registry.get_relationships("service-a")) == 1


def test_spring_analyzer_integration(tmp_path: Path) -> None:
    """Test Spring analyzer integration."""
    # Create test file content
    test_content = """
    @SpringBootApplication
    @EnableBinding(MyChannels.class)
    public interface MyChannels {
        @Input("input-channel")
        SubscribableChannel input();
        @Output("output-channel")
        MessageChannel output();
    }
    """

    # Create temporary test file
    test_file = tmp_path / "MyChannels.java"
    test_file.write_text(test_content)

    # Create a test service
    service = Service(name="test-service", root_path=tmp_path)

    # Analyze with Spring analyzer
    analyzer = SpringCloudStreamAnalyzer()
    analysis_results = analyzer.analyze(test_file, service)

    # Verify topics were found
    assert analysis_results.topics is not None
    assert isinstance(analysis_results.topics, dict)
    assert "input-channel" in analysis_results.topics
    assert "output-channel" in analysis_results.topics

    # Verify topic properties
    input_topic = analysis_results.topics["input-channel"]
    assert isinstance(input_topic, KafkaTopic)
    assert service.name in input_topic.consumers

    output_topic = analysis_results.topics["output-channel"]
    assert isinstance(output_topic, KafkaTopic)
    assert service.name in output_topic.producers


def test_duplicate_service_handling(service_registry: ServiceRegistry) -> None:
    # Test handling of duplicate service registrations
    service1 = Service(name="test", root_path=Path("/test1"))
    service2 = Service(name="test", root_path=Path("/test2"))

    service_registry.register_service(service1)
    service_registry.register_service(service2)

    # Should use the latest path but maintain existing relationships/topics
    assert service_registry.services["test"].root_path == Path("/test2")


def test_service_dependency_tracking(service_registry: ServiceRegistry) -> None:
    # Test service dependency tracking
    service_registry.add_relationship("app", "db", "spring-dependency")
    service_registry.add_relationship("app", "cache", "spring-dependency")

    deps = service_registry.get_service_dependencies("app")
    assert deps == {"db", "cache"}

    dependents = service_registry.get_service_dependents("db")
    assert dependents == {"app"}
