from kafka_viz.analyzers.kafka_analyzer import KafkaAnalyzer
from kafka_viz.models.service import Service


def test_java_patterns(test_data_dir):
    analyzer = KafkaAnalyzer()
    service_path = test_data_dir / "java_service"
    java_service = Service(name="java-service", path=service_path, language="java")

    topics = analyzer.analyze_service(java_service)

    assert "orders" in topics
    assert "processed-orders" in topics
    assert "notifications" in topics

    assert java_service.name in topics["orders"].consumers
    assert java_service.name in topics["processed-orders"].producers
    assert java_service.name in topics["notifications"].producers
