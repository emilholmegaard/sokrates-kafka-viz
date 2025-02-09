import logging
import re
from pathlib import Path
from typing import Any, Dict, NamedTuple, Optional, Set

from ..models.schema import KafkaTopic
from ..models.service import Service

logger = logging.getLogger(__name__)


class KafkaPatternMatch(NamedTuple):
    """Information about a matched Kafka pattern."""

    topic_name: str
    file_path: Path
    line_number: int
    context: str
    pattern_type: str
    framework: str
    confidence: float = 1.0


class KafkaPatterns:
    """Container for Kafka-related regex patterns."""

    def __init__(
        self,
        producers: Optional[Set[str]] = None,
        consumers: Optional[Set[str]] = None,
        topic_configs: Optional[Set[str]] = None,
        ignore_patterns: Optional[Set[str]] = None,
        custom_patterns: Optional[Dict[str, Set[str]]] = None,
    ):
        self.producers = producers or set()
        self.consumers = consumers or set()
        self.topic_configs = topic_configs or set()
        self.ignore_patterns = ignore_patterns or set()
        self.custom_patterns = custom_patterns or {}

        # Compile patterns for efficiency
        self._compiled_producers = {re.compile(p, re.MULTILINE) for p in self.producers}
        self._compiled_consumers = {re.compile(p, re.MULTILINE) for p in self.consumers}
        self._compiled_configs = {
            re.compile(p, re.MULTILINE) for p in self.topic_configs
        }
        self._compiled_ignore = {
            re.compile(p, re.MULTILINE) for p in self.ignore_patterns
        }

    def should_ignore(self, content: str) -> bool:
        """Check if content matches any ignore patterns."""
        return any(p.search(content) for p in self._compiled_ignore)


class BaseAnalyzer:
    """Base class for Kafka topic analyzers."""

    def __init__(self):
        """Initialize the analyzer."""
        self.patterns = None

    def get_patterns(self) -> KafkaPatterns:
        """Get the patterns to use for analysis.

        Returns:
            KafkaPatterns: The patterns to use
        """
        return self.patterns

    def can_analyze(self, file_path: Path) -> bool:
        """Check if this analyzer can handle the given file.

        Args:
            file_path: Path to the file to check

        Returns:
            bool: True if this analyzer can handle the file
        """
        raise NotImplementedError()

    def analyze(self, file_path: Path, service: Service) -> Dict[str, KafkaTopic]:
        """Analyze a file for Kafka topic usage.

        Args:
            file_path: Path to file to analyze
            service: Service the file belongs to

        Returns:
            Dict[str, KafkaTopic]: Dictionary of topics found
        """
        if not self.can_analyze(file_path):
            logger.debug(f"Skipping {file_path} - not supported by analyzer")
            return {}

        try:
            with open(file_path) as f:
                content = f.read()
                if not content.strip():
                    logger.debug(f"Skipping {file_path} - empty file")
                    return {}
        except (IOError, UnicodeDecodeError) as e:
            logger.error(f"Error reading {file_path}: {str(e)}")
            return {}

        topics = self._analyze_content(content, file_path, service)
        if topics:
            logger.debug(f"Found topics in {file_path}: {list(topics.keys())}")
        return topics

    def _analyze_content(
        self, content: str, file_path: Path, service: Service
    ) -> Dict[str, KafkaTopic]:
        """Analyze file content for Kafka topics.

        Args:
            content: File content to analyze
            file_path: Path to the file (for error reporting)
            service: Service the file belongs to

        Returns:
            Dict[str, KafkaTopic]: Dictionary of topics found
        """
        patterns = self.get_patterns()
        if not patterns:
            logger.warning(
                f"No patterns defined for analyzer {self.__class__.__name__}"
            )
            return {}

        if patterns.should_ignore(content):
            logger.debug(f"Ignoring {file_path} - matches ignore pattern")
            return {}

        topics: Dict[str, KafkaTopic] = {}

        def add_topic(topic_name: str, role: str):
            """Helper to add a topic with proper role."""
            if not topic_name:
                return

            if topic_name not in topics:
                topics[topic_name] = KafkaTopic(topic_name)
            if role == "producer":
                topics[topic_name].producers.add(service.name)
            elif role == "consumer":
                topics[topic_name].consumers.add(service.name)

        # Find producer patterns
        for pattern in patterns._compiled_producers:
            for match in pattern.finditer(content):
                topic_name = match.group(1)
                add_topic(topic_name, "producer")
                logger.debug(
                    f"Found producer pattern for topic '{topic_name}' in {file_path}"
                )

        # Find consumer patterns
        for pattern in patterns._compiled_consumers:
            for match in pattern.finditer(content):
                topic_name = match.group(1)
                add_topic(topic_name, "consumer")
                logger.debug(
                    f"Found consumer pattern for topic '{topic_name}' in {file_path}"
                )

        # Find topic configurations
        for pattern in patterns._compiled_configs:
            for match in pattern.finditer(content):
                topic_name = match.group(1)
                if topic_name not in topics:
                    topics[topic_name] = KafkaTopic(topic_name)
                logger.debug(
                    f"Found topic configuration for '{topic_name}' in {file_path}"
                )

        # Update service topics
        for topic_name, topic in topics.items():
            if topic_name not in service.topics:
                service.topics[topic_name] = topic
            else:
                # Merge producers and consumers
                service.topics[topic_name].producers.update(topic.producers)
                service.topics[topic_name].consumers.update(topic.consumers)

        return topics

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information from the analyzer.

        Returns:
            Dictionary containing debug information about the analyzer's state
        """
        return {"analyzer_type": self.__class__.__name__, "status": "active"}
