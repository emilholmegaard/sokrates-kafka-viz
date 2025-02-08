from kafka_viz.models.schema import KafkaTopic


def test_topic_creation():
    topic = KafkaTopic(name="test-topic")

    assert topic.name == "test-topic"
    assert len(topic.producers) == 0
    assert len(topic.consumers) == 0


def test_topic_add_producer():
    topic = KafkaTopic(name="test-topic")
    topic.producers.add("service1")

    assert "service1" in topic.producers
    assert len(topic.consumers) == 0


def test_topic_add_consumer():
    topic = KafkaTopic(name="test-topic")
    topic.consumers.add("service1")

    assert "service1" in topic.consumers
    assert len(topic.producers) == 0


def test_topic_equality():
    topic1 = KafkaTopic(name="test")
    topic2 = KafkaTopic(name="test")
    topic3 = KafkaTopic(name="other")

    assert topic1 == topic2
    assert topic1 != topic3
