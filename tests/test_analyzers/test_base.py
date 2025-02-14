from pathlib import Path

from kafka_viz.analyzers.analyzer import Analyzer, KafkaPatterns
from kafka_viz.models.service import Service


class SimpleTestAnalyzer(Analyzer):
    def __init__(self):
        super().__init__()
        self.patterns = KafkaPatterns(
            producers={r"producer\.send\s*\(\s*[\"\']([^\"\']+)"},
            consumers={r"KafkaConsumer\s*\([\"\']([^\"\']+)"},  # Simplified pattern
            topic_configs={r"topic:\s*[\"\']([^\"\']+)"},
        )

    def can_analyze(self, file_path: Path) -> bool:
        return file_path.suffix in {".py", ".java"}


def test_base_analyzer_can_analyze(test_data_dir):
    analyzer = SimpleTestAnalyzer()

    assert analyzer.can_analyze(Path("test.py"))
    assert analyzer.can_analyze(Path("test.java"))
    assert not analyzer.can_analyze(Path("test.txt"))


def test_base_analyzer_find_topics(python_service_dir):
    analyzer = SimpleTestAnalyzer()
    service = Service(name="test-service", path=python_service_dir)

    analysis_result = analyzer.analyze(python_service_dir / "kafka_client.py", service)

    assert analysis_result.topics is not None
    assert "orders" in analysis_result.topics
    assert "processed-orders" in analysis_result.topics

    orders_topic = analysis_result.topics["orders"]
    assert service.name in orders_topic.producers

    processed_topic = analysis_result.topics["processed-orders"]
    assert service.name in processed_topic.consumers
