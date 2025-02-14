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
    analysis_result = analyzer.analyze(processor_file, service)

    assert analysis_result is not None
    assert "orders" in analysis_result.topics
    assert "processed-orders" in analysis_result.topics

    assert service.name in analysis_result.topics["orders"].consumers
    assert service.name in analysis_result.topics["processed-orders"].producers


def test_spring_analyzer_ignore_test_files():
    analyzer = SpringCloudStreamAnalyzer()
    service = Service(name="spring-service", path=Path("."))

    test_file = Path("OrderProcessorTest.java")
    analysis_result = analyzer.analyze(test_file, service)

    # Should return empty dict for test files
    assert analysis_result.discovered_services == {}
