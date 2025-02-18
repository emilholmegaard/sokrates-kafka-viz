from pathlib import Path

import pytest

from kafka_viz.analyzers.kafka_analyzer import KafkaAnalyzer
from kafka_viz.models.service import Service


@pytest.fixture
def test_service(test_data_dir: Path) -> Service:
    return Service(name="java-service", root_path=test_data_dir)


def test_java_patterns(test_data_dir: Path) -> None:
    analyzer = KafkaAnalyzer()
    service_path = test_data_dir / "java_service"
    java_service = Service(name="java-service", root_path=service_path, language="java")

    topics = analyzer.analyze_service(java_service)

    assert "orders" in topics
    assert "processed-orders" in topics
    assert "notifications" in topics

    assert java_service.name in topics["orders"].consumers
    assert java_service.name in topics["processed-orders"].producers
    assert java_service.name in topics["notifications"].producers


def test_topic_pattern_detection(test_data_dir: Path, test_service: Service) -> None:
    """Test detection of different Kafka topic patterns"""

    content = """
    @KafkaListener(topics = "user-events")
    public void processUserEvent(String event) {
        // process
    }
    """
    file_path = test_data_dir / "OrderProducer.java"
    file_path.write_text(content)
    test_service.root_path = test_data_dir
    analyzer = KafkaAnalyzer()
    analysis_result = analyzer.analyze(file_path, test_service)

    assert "user-events" in analysis_result.topics


@pytest.mark.skip("Missing the functionlaity in kafka_analyzer.py")
def test_consumer_group_detection(test_data_dir: Path, test_service: Service):
    """Test detection of consumer group configurations"""
    analyzer = KafkaAnalyzer()

    content = """
    spring.kafka.consumer.group-id=user-service-group
    """
    file_path = test_data_dir / "application.properties"
    file_path.write_text(content)
    test_service.root_path = test_data_dir
    analyzer = KafkaAnalyzer()
    analysis_result = analyzer.analyze(file_path, test_service)

    assert analysis_result.consumer_group == "user-service-group"
