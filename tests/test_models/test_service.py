from pathlib import Path

from kafka_viz.models.service import Service


def test_service_creation():
    path = Path("/test/service")
    service = Service(name="test-service", root_path=path)

    assert service.name == "test-service"
    assert service.root_path == path  # Updated from path to root_path
    assert service.topics == {}  # Updated from kafka_topics to topics


def test_service_add_topic():
    service = Service(name="test-service", root_path=Path("/test"))

    service.add_topic(
        "test-topic", is_producer=True
    )  # Updated from producer to is_producer
    assert "test-topic" in service.topics  # Updated from kafka_topics to topics

    topic = service.topics["test-topic"]  # Updated from kafka_topics to topics
    assert service.name in topic.producers
    assert service.name not in topic.consumers


def test_service_equality():
    service1 = Service(name="test", root_path=Path("/test"))
    service2 = Service(name="test", root_path=Path("/test"))
    service3 = Service(name="other", root_path=Path("/test"))

    assert service1 == service2
    assert service1 != service3
