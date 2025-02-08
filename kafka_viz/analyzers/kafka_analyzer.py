import logging
import re
from pathlib import Path
from typing import Dict

from kafka_viz.models import KafkaTopic, Service

from .base import BaseAnalyzer, KafkaPatterns

logger = logging.getLogger(__name__)


class KafkaAnalyzer(BaseAnalyzer):
    """Analyzer for finding Kafka usage patterns in code."""

    def __init__(self):
        super().__init__()
        # Define regex patterns for Kafka usage
        self.patterns = KafkaPatterns(
            producers={
                # Plain Kafka patterns
                # ProducerRecord constructor
                r'new\s+ProducerRecord\s*<[^>]*>\s*\(\s*"([^"]+)"',
                # Direct send
                r'\.send\s*\(\s*"([^"]+)"',
                # KafkaTemplate send
                r'kafkaTemplate\.send\s*\(\s*"([^"]+)"',
                # KafkaTemplate with constant
                r"kafkaTemplate\.send\s*\(\s*([A-Z_]+)",
                # Producer with constant
                r"producer\.send\s*\(\s*([A-Z_]+)",
                # Producer Record with constant
                r"new\s+ProducerRecord\s*<[^>]*>\s*\(\s*([A-Z_]+)",
                # Spring Cloud Stream patterns
                # SendTo annotation
                r'@SendTo\s*\(\s*"([^"]+)"\s*\)',
                # Output channel
                r'@Output\s*\(\s*"([^"]+)"\s*\)',
            },
            consumers={
                # Plain Kafka patterns
                # Subscribe with literal
                r'\.subscribe\s*\(\s*(?:Arrays\.asList|List\.of)\s*\(\s*"([^"]+)"\s*\)',
                # Subscribe with constant
                r"\.subscribe\s*\(\s*(?:Arrays\.asList|List\.of)\s*\(\s*([A-Z_]+)\s*\)",
                # Single topic literal
                r'@KafkaListener\s*\(\s*topics\s*=\s*"([^"]+)"\s*\)',
                # Single topic constant
                r"@KafkaListener\s*\(\s*topics\s*=\s*([A-Z_]+)\s*\)",
                # Array topics
                r'@KafkaListener\s*\(\s*topics\s*=\s*\{\s*"([^"]+)"(?:\s*,\s*"[^"]+")*\s*\}\s*\)',
                # Array constants
                r"@KafkaListener\s*\(\s*topics\s*=\s*\{\s*([A-Z_]+)(?:\s*,\s*[A-Z_]+)*\s*\}\s*\)",
                # Spring Cloud Stream patterns
                # StreamListener
                r'@StreamListener\s*\(\s*"([^"]+)"\s*\)',
                # Input channel
                r'@Input\s*\(\s*"([^"]+)"\s*\)',
            },
            topic_configs={
                # Configuration patterns
                # Constants
                r'(?:private|public|static)\s+(?:final\s+)?String\s+([A-Z_]+)\s*=\s*"([^"]+)"',
                # Spring config
                r'@Value\s*\(\s*"\$\{([^}]+\.topic)\}"\s*\)\s*private\s+String\s+([^;\s]+)',
                # Stream binding
                r"spring\.cloud\.stream\.bindings\.([^.]+)\.destination\s*=",
                # Topic config
                r'@TopicConfig\s*\(\s*name\s*=\s*"([^"]+)"',
            },
        )

    def can_analyze(self, file_path: Path) -> bool:
        """Check if file is a Java source file."""
        return file_path.suffix.lower() == ".java"

    def _extract_topic_vars(self, content: str) -> Dict[str, str]:
        """Extract topic variables and constants from file content."""
        topic_vars = {}
        for pattern in self.patterns.topic_configs:
            matches = re.finditer(pattern, content)
            for match in matches:
                groups = match.groups()
                if len(groups) == 2:  # For constant declarations
                    var_name, topic_name = groups
                    topic_vars[var_name] = topic_name
                elif len(groups) == 1:  # For Spring config and topic config
                    # Extract the last part as the variable name
                    parts = groups[0].split(".")
                    if len(parts) > 1:
                        # For spring.cloud.stream.bindings.<name>.destination
                        # we want <name> as both key and value since it's the topic name
                        topic_vars[parts[-2]] = parts[-2]
                    else:
                        # For @TopicConfig(name="topic") just use the topic name directly
                        topic_vars[groups[0]] = groups[0]
        return topic_vars

    def analyze_service(self, service: Service) -> Dict[str, KafkaTopic]:
        """Analyze a service for Kafka usage.

        Args:
            service: Service to analyze

        Returns:
            Dict[str, KafkaTopic]: Dictionary of topics found
        """
        # Make sure we're working with an absolute path
        base_path = service.root_path.resolve()

        # Find all Java files
        java_files = list(base_path.rglob("*.java"))
        logger.debug(f"Found {len(java_files)} Java files in {base_path}")

        for file_path in java_files:
            # Include test data files but exclude regular test files
            if ("src/test" not in str(file_path) and "test/" not in str(file_path)) or (
                "tests/test_data" in str(file_path)
            ):
                try:
                    found_topics = self.analyze(file_path, service)
                    if found_topics:
                        for topic_name, topic in found_topics.items():
                            if topic_name not in service.topics:
                                service.topics[topic_name] = topic
                            else:
                                # Merge producers and consumers
                                service.topics[topic_name].producers.update(
                                    topic.producers
                                )
                                service.topics[topic_name].consumers.update(
                                    topic.consumers
                                )
                                # Update producer/consumer locations if they exist
                                for (
                                    service_name,
                                    locations,
                                ) in topic.producer_locations.items():
                                    for location in locations:
                                        service.topics[
                                            topic_name
                                        ].add_producer_location(service_name, location)
                                for (
                                    service_name,
                                    locations,
                                ) in topic.consumer_locations.items():
                                    for location in locations:
                                        service.topics[
                                            topic_name
                                        ].add_consumer_location(service_name, location)
                except Exception as e:
                    logger.error(f"Error analyzing {file_path}: {str(e)}")

        return service.topics

    def analyze(self, file_path: Path, service: Service) -> Dict[str, KafkaTopic]:
        """Analyze Java file for Kafka patterns.

        Args:
            file_path: Path to Java file
            service: Service to analyze

        Returns:
            Dict[str, KafkaTopic]: Dictionary of topics found
        """
        content = file_path.read_text()

        # First pass: collect topic variables/constants
        topic_vars = self._extract_topic_vars(content)

        # Track found topics
        topics: Dict[str, KafkaTopic] = {}

        # Helper function to process matches
        def process_match(match, is_producer: bool):
            topic_name = match.group(1)
            # Check if it's a variable reference
            if topic_name in topic_vars:
                topic_name = topic_vars[topic_name]

            if topic_name not in topics:
                topics[topic_name] = KafkaTopic(topic_name)

            location = {
                "file": str(file_path.relative_to(service.root_path)),
                "line": len(content[: match.start()].splitlines()) + 1,
                "column": match.start(1)
                - len(content[: match.start()].splitlines()[-1]),
            }

            if is_producer:
                topics[topic_name].producers.add(service.name)
                topics[topic_name].add_producer_location(service.name, location)
            else:
                topics[topic_name].consumers.add(service.name)
                topics[topic_name].add_consumer_location(service.name, location)

        # Analyze producers
        for pattern in self.patterns.producers:
            for match in re.finditer(pattern, content):
                process_match(match, True)

        # Analyze consumers
        for pattern in self.patterns.consumers:
            for match in re.finditer(pattern, content):
                process_match(match, False)

        return topics
