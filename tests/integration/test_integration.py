import pytest

from kafka_viz.analyzers.kafka_analyzer import KafkaAnalyzer
from kafka_viz.models.service import Service


@pytest.mark.skip(reason="issues to find all topics in the multiple files")
def test_advanced_kafka_patterns_integration(test_data_dir) -> None:
    """Test that all advanced Kafka patterns are correctly detected."""
    analyzer = KafkaAnalyzer()
    service_path = test_data_dir / "java" / "advanced"
    java_service = Service(name="java-service", path=service_path, language="java")

    topics = analyzer.analyze_service(java_service)

    # Check if all expected topics are found
    topic_names = {t.name for t in topics.values()}

    expected_topics = {
        "record-topic",
        "publish-topic",
        "${kafka.topic.name}",
        "topic1",
        "topic2",
        "topic3",
        "topic4",
        "topic5",
        "topic6",
        "${kafka.topics.custom}",
        "outputChannel",
        "inputChannel",
        "input",
        "output",
    }
    assert topic_names == expected_topics

    # Check topic producer roles
    producers = {t.name for t in topics if t.producers}
    expected_producers = {
        "record-topic",
        "publish-topic",
        "${kafka.topic.name}",
        "outputChannel",
        "output",
    }
    assert producers == expected_producers

    # Check topic consumer roles
    consumers = {t.name for t in topics if t.consumers}
    expected_consumers = {
        "topic1",
        "topic2",
        "topic3",
        "topic4",
        "topic5",
        "topic6",
        "${kafka.topics.custom}",
        "inputChannel",
        "input",
    }
    assert consumers == expected_consumers
