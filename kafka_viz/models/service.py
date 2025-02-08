from pathlib import Path
from typing import Dict, Optional, Set

from .schema import KafkaTopic, Schema


class Service:
    """Represents a microservice in the system."""

    def __init__(
        self,
        name: str,
        path: Optional[Path] = None,
        root_path: Optional[Path] = None,  # Added for backward compatibility
        language: str = "unknown",
        build_file: Optional[Path] = None,
    ):
        """Initialize a service.

        Args:
            name: Name of the service
            path: Path to the service's root directory (deprecated, use root_path)
            root_path: Path to the service's root directory
            language: Primary programming language used in service
            build_file: Path to the service's build file
        """
        self.name = name
        self.root_path = root_path or path or Path(".")
        self.language = language.lower()
        self.topics: Dict[str, KafkaTopic] = {}
        self.schemas: Dict[str, "Schema"] = {}  # Forward reference
        self.build_file = build_file
        self.source_files: Set[Path] = set()

    def add_topic(
        self, topic_name: str, is_producer: bool = False, is_consumer: bool = False
    ) -> None:
        """Add a topic to this service.

        Args:
            topic_name: Name of the Kafka topic
            is_producer: Whether this service produces to the topic
            is_consumer: Whether this service consumes from the topic
        """
        if topic_name not in self.topics:
            self.topics[topic_name] = KafkaTopic(topic_name)

        topic = self.topics[topic_name]
        if is_producer:
            topic.producers.add(self.name)
        if is_consumer:
            topic.consumers.add(self.name)

    def __eq__(self, other):
        if not isinstance(other, Service):
            return False

        return (
            self.name == other.name
            and self.root_path == other.root_path
            and self.language == other.language
            and self.topics == other.topics
        )

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return f"Service({self.name}, {self.language}, {len(self.topics)} topics)"

    def __repr__(self):
        return self.__str__()
