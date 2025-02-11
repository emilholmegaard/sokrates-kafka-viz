"""Kafka-specific patterns and topic analysis."""

import logging
from pathlib import Path
from typing import Dict, Set

from ..models.schema import KafkaTopic
from ..models.service import Service
from ..models.service_registry import AnalysisResult
from .analyzer import Analyzer, KafkaPatterns

logger = logging.getLogger(__name__)


class KafkaAnalyzer(Analyzer):
    """Analyzer for Kafka-specific patterns."""

    def __init__(self):
        super().__init__()
        self.patterns = KafkaPatterns(
            producers={
                # Basic Kafka patterns
                r'producer\.send\(\s*["\']([^"\']+)["\']\s*\)',
                r'producer\.beginTransaction\(\s*["\']([^"\']+)["\']\s*\)',
                r'@SendTo\(\s*["\']([^"\']+)["\']\s*\)',
                r'ProducerRecord\(\s*["\']([^"\']+)["\']\s*\)',
                # Configuration patterns
                r'kafka\.topic\s*=\s*["\']([^"\']+)["\']\s*',
                r'spring\.cloud\.stream\.bindings\.output\.destination\s*=\s*["\']([^"\']+)["\']\s*',
            },
            consumers={
                # Basic Kafka patterns
                r'consumer\.subscribe\(\s*["\']([^"\']+)["\']\s*\)',
                r'@KafkaListener\(\s*topics\s*=\s*["\']([^"\']+)["\']\s*\)',
                r'ConsumerRecord\<[^>]+\>\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[^;]+;',
                # Configuration patterns
                r'spring\.cloud\.stream\.bindings\.input\.destination\s*=\s*["\']([^"\']+)["\']\s*',
            },
            topic_configs={
                # Topic configuration patterns
                r'admin\.createTopics\(\s*["\']([^"\']+)["\']\s*\)',
                r'@Topic\(\s*["\']([^"\']+)["\']\s*\)',
                r'@StreamListener\(\s*["\']([^"\']+)["\']\s*\)',
            },
            ignore_patterns={
                r'@TestConfiguration',
                r'@SpringBootTest',
                r'@Test',
            },
        )

    def can_analyze(self, file_path: Path) -> bool:
        """Check if file can be analyzed for Kafka patterns."""
        return any(
            file_path.suffix.lower() == ext
            for ext in [".java", ".kt", ".py", ".js", ".ts", ".properties", ".yml", ".yaml"]
        )

    def analyze(self, file_path: Path, service: Service) -> AnalysisResult:
        """Analyze a file for Kafka topic usage.

        Args:
            file_path: Path to file to analyze
            service: Service the file belongs to

        Returns:
            AnalysisResult containing found topics and relationships
        """
        result = AnalysisResult(affected_service=service.name)
        
        if not self.can_analyze(file_path):
            logger.debug(f"Skipping {file_path} - not supported by analyzer")
            return result

        try:
            # Get topics from base analyzer
            topics = super()._analyze_content(
                file_path.read_text(), file_path, service
            )
            if topics:
                result.topics.update(topics)
                logger.debug(f"Found topics in {file_path}: {list(topics.keys())}")

                # Add relationships for topics
                for topic_name, topic in topics.items():
                    self._add_topic_relationships(topic, result)

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {str(e)}")

        return result

    def _add_topic_relationships(self, topic: KafkaTopic, result: AnalysisResult) -> None:
        """Add relationships based on topic producers and consumers."""
        # Add relationships between producers and consumers
        for producer in topic.producers:
            for consumer in topic.consumers:
                if producer != consumer:
                    result.add_relationship(
                        source=producer,
                        target=consumer,
                        type_="kafka",
                        details={"topic": topic.name}
                    )
