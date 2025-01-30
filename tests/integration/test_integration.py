import pytest
from pathlib import Path
from kafka_viz.kafka_analyzer import KafkaAnalyzer
from kafka_viz.models import TopicType

@pytest.fixture
def test_project_path(test_data_dir):
    return Path(test_data_dir) / "java"

def test_advanced_kafka_patterns_integration(test_project_path):
    analyzer = KafkaAnalyzer(test_project_path / "advanced")
    topics = analyzer.analyze()
    
    # Check if all expected topics are found
    topic_names = {t.name for t in topics}
    expected_topics = {
        "record-topic",
        "publish-topic",
        "${kafka.topic.name}",
        "topic1", "topic2", "topic3", "topic4", "topic5", "topic6",
        "${kafka.topics.custom}",
        "outputChannel",
        "inputChannel",
        "input",
        "output"
    }
    assert topic_names == expected_topics

    # Check topic types
    producers = {t.name for t in topics if t.type == TopicType.PRODUCER}
    consumers = {t.name for t in topics if t.type == TopicType.CONSUMER}

    assert "record-topic" in producers
    assert "publish-topic" in producers
    assert "${kafka.topic.name}" in producers
    assert "outputChannel" in producers
    assert "output" in producers

    assert "topic1" in consumers
    assert "topic2" in consumers
    assert "${kafka.topics.custom}" in consumers
    assert "inputChannel" in consumers
    assert "input" in consumers

    # Check topology
    topology = analyzer.get_topology()
    assert any(node["configBased"] for node in topology["nodes"] 
              if node["id"].startswith("${"))
    assert any(edge["type"] == "produces" for edge in topology["edges"])
    assert any(edge["type"] == "consumes" for edge in topology["edges"])
