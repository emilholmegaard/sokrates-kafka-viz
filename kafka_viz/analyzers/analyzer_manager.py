"""Manager class to coordinate different analyzers."""
from typing import Dict, List, Optional
from pathlib import Path

from .kafka_analyzer import KafkaAnalyzer
from .spring_analyzer import SpringCloudStreamAnalyzer
from ..models.service import Service
from ..models.schema import KafkaTopic

class AnalyzerManager:
    """Manages and coordinates different analyzers."""

    def __init__(self):
        self.analyzers = [
            KafkaAnalyzer(),
            SpringCloudStreamAnalyzer()
        ]

    def analyze_file(self, file_path: Path, service: Service) -> Optional[Dict[str, KafkaTopic]]:
        """Analyze a file using all available analyzers."""
        all_topics = {}

        for analyzer in self.analyzers:
            topics = analyzer.analyze(file_path, service)
            if topics:
                for topic_name, topic in topics.items():
                    if topic_name not in all_topics:
                        all_topics[topic_name] = topic
                    else:
                        # Merge producers and consumers
                        all_topics[topic_name].producers.update(topic.producers)
                        all_topics[topic_name].consumers.update(topic.consumers)

        return all_topics if all_topics else None

    def get_debug_info(self) -> List[Dict]:
        """Get debug information from all analyzers."""
        return [analyzer.get_debug_info() for analyzer in self.analyzers]