"""Tests for ServiceRegistry integration."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

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


@pytest.mark.skip(reason="ServiceRegistry is not used in the current implementation")
def test_service_registration(service_registry: ServiceRegistry) -> None:
    # Test basic service registration
    service = Service(name="test-service", root_path=Path("/test"))
    service_registry.register_service(service)
    assert "test-service" in service_registry.services
    assert service_registry.services["test-service"] == service


@pytest.mark.skip(reason="ServiceRegistry is not used in the current implementation")
def test_service_relationship(service_registry: ServiceRegistry) -> None:
    # Test relationship tracking
    service_registry.add_relationship("service-a", "service-b", "kafka")
    relationships = service_registry.get_relationships("service-a")
    assert len(relationships) == 1
    assert relationships[0].source == "service-a"
    assert relationships[0].target == "service-b"
    assert relationships[0].type == "kafka"


@pytest.mark.skip(reason="ServiceRegistry is not used in the current implementation")
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


def test_spring_analyzer_integration() -> None:
    """Test Spring analyzer integration."""
    with patch("pathlib.Path.read_text") as mock_read:
        # Mock a Spring Boot application file with channels
        mock_read.return_value = """
        @SpringBootApplication
        @EnableBinding(MyChannels.class)
        public interface MyChannels {
            @Input("input-channel")
            SubscribableChannel input();
            @Output("output-channel")
            MessageChannel output();
        }
        """

        # Create a test service
        service = Service(name="test-service", root_path=Path("/test"))

        # Analyze with Spring analyzer
        analyzer = SpringCloudStreamAnalyzer()
        analysis_results = analyzer.analyze(Path("/test/MyChannels.java"), service)

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


@pytest.mark.skip(reason="discover_services is out of order...")
def test_service_discovery_integration(
    analyzer_manager: AnalyzerManager, tmp_path: Path
) -> None:
    # Create a mock project structure
    java_project = tmp_path / "java-service"
    java_project.mkdir()
    (java_project / "pom.xml").write_text(
        "<groupId>test</groupId><artifactId>java-service</artifactId>"
    )

    # Test service discovery
    service_collection = analyzer_manager.discover_services(Path(tmp_path))
    assert "java-service" in service_collection.services.keys()


@pytest.mark.skip(reason="ServiceRegistry is not used in the current implementation")
def test_duplicate_service_handling(service_registry: ServiceRegistry) -> None:
    # Test handling of duplicate service registrations
    service1 = Service(name="test", root_path=Path("/test1"))
    service2 = Service(name="test", root_path=Path("/test2"))

    service_registry.register_service(service1)
    service_registry.register_service(service2)

    # Should use the latest path but maintain existing relationships/topics
    assert service_registry.services["test"].root_path == Path("/test2")


@pytest.mark.skip(reason="ServiceRegistry is not used in the current implementation")
def test_service_dependency_tracking(service_registry: ServiceRegistry) -> None:
    # Test service dependency tracking
    service_registry.add_relationship("app", "db", "spring-dependency")
    service_registry.add_relationship("app", "cache", "spring-dependency")

    deps = service_registry.get_service_dependencies("app")
    assert deps == {"db", "cache"}

    dependents = service_registry.get_service_dependents("db")
    assert dependents == {"app"}


@pytest.mark.skip(reason="ServiceRegistry is not used in the current implementation")
def test_topic_merging(service_registry: ServiceRegistry) -> None:
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
