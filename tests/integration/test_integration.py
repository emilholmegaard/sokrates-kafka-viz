import pytest
from pathlib import Path
from kafka_viz.kafka_analyzer import KafkaAnalyzer

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

    # Check topic roles based on producers/consumers sets
    producers = {t.name for t in topics if t.producers}
    expected_producers = {
        "record-topic",
        "publish-topic",
        "${kafka.topic.name}",
        "outputChannel",
        "output"
    }
    assert producers == expected_producers

    consumers = {t.name for t in topics if t.consumers}
    expected_consumers = {
        "topic1", "topic2", "topic3", "topic4", "topic5", "topic6",
        "${kafka.topics.custom}",
        "inputChannel",
        "input"
    }
    assert consumers == expected_consumers

    # Check if locations are properly tracked
    for topic in topics:
        if topic.producers:
            for producer in topic.producers:
                assert topic.producer_locations[producer]
        if topic.consumers:
            for consumer in topic.consumers:
                assert topic.consumer_locations[consumer]