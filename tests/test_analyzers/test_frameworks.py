from pathlib import Path

from kafka_viz.analyzers.spring_analyzer import SpringCloudStreamAnalyzer
from kafka_viz.models.service import Service


def test_spring_cloud_stream_analyzer(spring_service_dir):
    analyzer = SpringCloudStreamAnalyzer()
    service = Service(name="spring-service", path=spring_service_dir)

    # Test source file analysis
    processor_file = (
        spring_service_dir / "src/main/java/com/example/OrderProcessor.java"
    )
    topics = analyzer.analyze(processor_file, service)

    assert topics is not None
    assert "orders" in topics
    assert "processed-orders" in topics

    assert service.name in topics["orders"].consumers
    assert service.name in topics["processed-orders"].producers


def test_spring_analyzer_ignore_test_files():
    analyzer = SpringCloudStreamAnalyzer()
    service = Service(name="spring-service", path=Path("."))

    test_file = Path("OrderProcessorTest.java")
    topics = analyzer.analyze(test_file, service)

    # Should return empty dict for test files
    assert topics == {}
