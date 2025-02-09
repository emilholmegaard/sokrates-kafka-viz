"""Integration tests for service-level analysis."""

from pathlib import Path

from kafka_viz.analyzers.analyzer_manager import AnalyzerManager
from kafka_viz.models.schema import KafkaTopic
from kafka_viz.models.service import Service
from kafka_viz.models.service_collection import ServiceCollection


def create_test_service(name: str, root_path: str) -> Service:
    """Helper function to create a test service."""
    return Service(name=name, root_path=Path(root_path), language="java")


def test_service_level_analysis_basic():
    """Test basic service-level analysis with a simple producer-consumer setup."""
    # Create test services
    services = ServiceCollection()

    # Create producer service
    producer = create_test_service("producer-service", "/fake/path/producer")
    producer_topic = KafkaTopic("test-topic")
    producer_topic.producers.add("producer-service")
    producer.topics["test-topic"] = producer_topic
    services.add_service(producer)

    # Create consumer service
    consumer = create_test_service("consumer-service", "/fake/path/consumer")
    consumer_topic = KafkaTopic("test-topic")
    consumer_topic.consumers.add("consumer-service")
    consumer.topics["test-topic"] = consumer_topic
    services.add_service(consumer)

    # Initialize and run analysis
    manager = AnalyzerManager()
    manager.analyze_service_dependencies(services)

    # Get dependency analyzer results
    dep_analyzer = manager.service_level_analyzers[0]

    # Verify dependencies were correctly identified
    assert "producer-service" in dep_analyzer.graph
    assert "consumer-service" in dep_analyzer.graph
    assert list(dep_analyzer.get_dependencies("producer-service")) == [
        "consumer-service"
    ]
    assert list(dep_analyzer.get_dependents("consumer-service")) == ["producer-service"]


def test_service_level_analysis_with_multiple_topics() -> None:
    """Test service-level analysis with multiple topics and services."""
    services = ServiceCollection()

    # Create services
    service_a = create_test_service("service-a", "/fake/path/a")
    service_b = create_test_service("service-b", "/fake/path/b")
    service_c = create_test_service("service-c", "/fake/path/c")

    # Set up topics for service A (produces to B and C)
    topic_ab = KafkaTopic("topic-ab")
    topic_ab.producers.add("service-a")
    topic_ab.consumers.add("service-b")
    service_a.topics["topic-ab"] = topic_ab

    topic_ac = KafkaTopic("topic-ac")
    topic_ac.producers.add("service-a")
    topic_ac.consumers.add("service-c")
    service_a.topics["topic-ac"] = topic_ac

    # Set up topics for service B (produces to C)
    topic_bc = KafkaTopic("topic-bc")
    topic_bc.producers.add("service-b")
    topic_bc.consumers.add("service-c")
    service_b.topics["topic-bc"] = topic_bc

    # Add all services to collection
    services.add_service(service_a)
    services.add_service(service_b)
    services.add_service(service_c)

    # Run analysis
    manager = AnalyzerManager()
    manager.analyze_service_dependencies(services)

    # Get dependency analyzer
    dep_analyzer = manager.service_level_analyzers[0]

    # Verify service dependencies
    assert set(dep_analyzer.get_dependencies("service-a")) == {"service-b", "service-c"}
    assert set(dep_analyzer.get_dependencies("service-b")) == {"service-c"}
    assert set(dep_analyzer.get_dependencies("service-c")) == set()

    # Verify dependents
    assert set(dep_analyzer.get_dependents("service-a")) == set()
    assert set(dep_analyzer.get_dependents("service-b")) == {"service-a"}
    assert set(dep_analyzer.get_dependents("service-c")) == {"service-a", "service-b"}

    # Test critical services detection
    critical_services = dep_analyzer.get_critical_services()
    assert "service-c" in critical_services  # Should be critical due to many dependents


def test_service_level_analysis_cycle_detection() -> None:
    """Test detection of dependency cycles between services."""
    services = ServiceCollection()

    # Create services in a cycle: A -> B -> C -> A
    service_a = create_test_service("service-a", "/fake/path/a")
    service_b = create_test_service("service-b", "/fake/path/b")
    service_c = create_test_service("service-c", "/fake/path/c")

    # Create topics forming a cycle
    topic_ab = KafkaTopic("topic-ab")
    topic_ab.producers.add("service-a")
    topic_ab.consumers.add("service-b")
    service_a.topics["topic-ab"] = topic_ab

    topic_bc = KafkaTopic("topic-bc")
    topic_bc.producers.add("service-b")
    topic_bc.consumers.add("service-c")
    service_b.topics["topic-bc"] = topic_bc

    topic_ca = KafkaTopic("topic-ca")
    topic_ca.producers.add("service-c")
    topic_ca.consumers.add("service-a")
    service_c.topics["topic-ca"] = topic_ca

    # Add services to collection
    services.add_service(service_a)
    services.add_service(service_b)
    services.add_service(service_c)

    # Run analysis
    manager = AnalyzerManager()
    manager.analyze_service_dependencies(services)

    # Get dependency analyzer
    dep_analyzer = manager.service_level_analyzers[0]

    # Verify cycle is detected
    cycles = dep_analyzer._detect_cycles()
    assert len(cycles) > 0

    # The cycle should contain all three services
    cycle_services = set()
    for cycle in cycles:
        cycle_services.update(cycle)
    assert cycle_services == {"service-a", "service-b", "service-c"}

    # All services should be marked as critical due to being in a cycle
    critical_services = dep_analyzer.get_critical_services()
    assert critical_services == {"service-a", "service-b", "service-c"}
