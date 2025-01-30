import pytest
from pathlib import Path
from sokrates_kafka_viz.analyzers.java_analyzer import JavaAnalyzer
from sokrates_kafka_viz.models import KafkaTopic, TopicType

@pytest.fixture
def test_data_path(test_data_dir):
    return Path(test_data_dir) / "java" / "advanced"

def test_record_based_producers(test_data_path):
    analyzer = JavaAnalyzer()
    topics = analyzer.analyze_file(test_data_path / "RecordProducer.java")
    
    assert len(topics) == 3
    assert any(t.name == "record-topic" and t.type == TopicType.PRODUCER for t in topics)
    assert any(t.name == "publish-topic" and t.type == TopicType.PRODUCER for t in topics)
    assert any(t.name == "${kafka.topic.name}" and t.type == TopicType.PRODUCER for t in topics)

def test_collection_based_consumers(test_data_path):
    analyzer = JavaAnalyzer()
    topics = analyzer.analyze_file(test_data_path / "CollectionConsumer.java")
    
    assert len(topics) == 6
    for i in range(1, 3):
        assert any(t.name == f"topic{i}" and t.type == TopicType.CONSUMER for t in topics)
    for i in range(3, 5):
        assert any(t.name == f"topic{i}" and t.type == TopicType.CONSUMER for t in topics)
    for i in range(5, 7):
        assert any(t.name == f"topic{i}" and t.type == TopicType.CONSUMER for t in topics)

def test_container_factory_config(test_data_path):
    analyzer = JavaAnalyzer()
    topics = analyzer.analyze_file(test_data_path / "ContainerConfig.java")
    
    assert len(topics) == 1
    assert any(t.name == "${kafka.topics.custom}" and t.type == TopicType.CONSUMER for t in topics)

def test_stream_processor(test_data_path):
    analyzer = JavaAnalyzer()
    topics = analyzer.analyze_file(test_data_path / "StreamProcessor.java")
    
    assert len(topics) == 4
    assert any(t.name == "outputChannel" and t.type == TopicType.PRODUCER for t in topics)
    assert any(t.name == "inputChannel" and t.type == TopicType.CONSUMER for t in topics)
    assert any(t.name == "input" and t.type == TopicType.CONSUMER for t in topics)
    assert any(t.name == "output" and t.type == TopicType.PRODUCER for t in topics)
