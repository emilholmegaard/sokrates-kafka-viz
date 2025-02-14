from pathlib import Path

import pytest

from kafka_viz.analyzers.java_analyzer import JavaAnalyzer
from kafka_viz.models.service import Service


@pytest.fixture
def test_service():
    return Service(name="test-service", language="java")


@pytest.fixture
def test_data_path(test_data_dir):
    return Path(test_data_dir) / "java" / "advanced"


def test_record_based_producers(test_data_path, test_service):
    analyzer = JavaAnalyzer()
    analysis_result = analyzer.analyze(
        test_data_path / "RecordProducer.java", test_service
    )

    assert len(analysis_result.topics) == 3
    expected_topics = {
        "record-topic": {"producers"},
        "publish-topic": {"producers"},
        "${kafka.topic.name}": {"producers"},
    }

    for topic in analysis_result.topics.values():
        expected_sets = expected_topics[topic.name]
        if "producers" in expected_sets:
            assert len(topic.producers) > 0
        if "consumers" in expected_sets:
            assert len(topic.consumers) > 0


def test_collection_based_consumers(test_data_path, test_service):
    analyzer = JavaAnalyzer()
    analysis_result = analyzer.analyze(
        test_data_path / "CollectionConsumer.java", test_service
    )

    assert len(analysis_result.topics) == 6
    for i in range(1, 7):
        found = False
        for topic in analysis_result.topics.values():
            if topic.name == f"topic{i}":
                assert len(topic.consumers) > 0
                found = True
        assert found, f"topic{i} not found"


def test_container_factory_config(test_data_path, test_service):
    analyzer = JavaAnalyzer()
    analysis_result = analyzer.analyze(
        test_data_path / "ContainerConfig.java", test_service
    )

    assert len(analysis_result.topics) == 1
    topic = next(iter(analysis_result.topics.values()))
    assert topic.name == "${kafka.topics.custom}"
    assert len(topic.consumers) > 0


def test_stream_processor(test_data_path, test_service):
    analyzer = JavaAnalyzer()
    analysis_result = analyzer.analyze(
        test_data_path / "StreamProcessor.java", test_service
    )

    expected_topics = {
        "outputChannel": {"producers"},
        "inputChannel": {"consumers"},
        "input": {"consumers"},
        "output": {"producers"},
    }

    assert len(analysis_result.topics) == len(expected_topics)
    for topic in analysis_result.topics.values():
        expected_sets = expected_topics[topic.name]
        if "producers" in expected_sets:
            assert len(topic.producers) > 0
        if "consumers" in expected_sets:
            assert len(topic.consumers) > 0


def test_location_tracking(test_data_path, test_service):
    analyzer = JavaAnalyzer()
    analysis_result = analyzer.analyze(
        test_data_path / "RecordProducer.java", test_service
    )

    for topic in analysis_result.topics.values():
        if topic.producers:
            for service in topic.producers:
                locations = topic.producer_locations[service]
                assert len(locations) > 0
                for location in locations:
                    assert "file" in location
                    assert "line" in location
        if topic.consumers:
            for service in topic.consumers:
                locations = topic.consumer_locations[service]
                assert len(locations) > 0
                for location in locations:
                    assert "file" in location
                    assert "line" in location
