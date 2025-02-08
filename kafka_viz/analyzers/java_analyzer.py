import re
from typing import Dict, Set, Optional, List
from pathlib import Path
import logging

from ..models.schema import KafkaTopic
from ..models.service import Service
from .base import BaseAnalyzer, KafkaPatterns

logger = logging.getLogger(__name__)

class JavaAnalyzer(BaseAnalyzer):
    """Analyzer for Java source files containing Kafka patterns."""
    
    def __init__(self) -> None:
        super().__init__()
        self.topics: Dict[str, KafkaTopic] = {}
        self.patterns = KafkaPatterns(
            producers={
                r'new\s+ProducerRecord\s*<[^>]*>\s*\(\s*["\']([^"\']+)["\']',
                r'(?:messageProducer|producer|kafkaTemplate|template)\.(publish|send)\s*\(\s*["\']([^"\']+)["\']',
                r'@SendTo\s*\(["\']([^"\']+)["\']',
                r'@Output\s*\(["\']([^"\']+)["\']'
            },
            consumers={
                r'@KafkaListener\s*\(\s*topics\s*=\s*["\']([^"\']+)["\']',
                r'@KafkaListener\s*\(\s*topics\s*=\s*\{([^}]+)\}',
                r'@StreamListener\s*\(["\']([^"\']+)["\']',
                r'@Input\s*\(["\']([^"\']+)["\']',
                r'consumer\.subscribe\s*\(\s*Arrays\.asList\s*\((.*?)\)',
                r'consumer\.subscribe\s*\(\s*List\.of\s*\((.*?)\)',
                r'consumer\.subscribe\s*\(\s*Set\.of\s*\((.*?)\)'
            },
            topic_configs={
                r'@Value\s*\(["\']?\$\{([^}]+)\}["\']?\)',
                r'private\s+(?:static\s+final\s+)?String\s+(\w+)\s*=\s*["\']([^"\']+)["\']'
            }
        )
        self.constant_map: Dict[str, str] = {}  # Map of variable names to values

    def can_analyze(self, file_path: Path) -> bool:
        """Check if this analyzer can handle Java files."""
        return file_path.suffix.lower() == '.java'

    def _normalize_topic_name(self, name: str) -> str:
        """Normalize topic name to ensure consistent format for config values."""
        name = name.strip(' "\'')
        # Check if it's a constant reference
        if name in self.constant_map:
            return self.constant_map[name]
        # Handle Kafka config values
        if name.startswith('${') and name.endswith('}'):
            return name
        if name.startswith('kafka.') or '.kafka.' in name:
            return f"${{{name}}}"
        logger.debug(f"Normalized name:  {name}")
        return name

    def _add_topic(self, name: str, is_producer: bool, file_path: Path, line: int, service_name: str) -> None:
        """Add a topic with proper name normalization and location tracking."""
        name = self._normalize_topic_name(name)
        if name not in self.topics:
            self.topics[name] = KafkaTopic(name)

        topic = self.topics[name]
        location = {
            'file': str(file_path),
            'line': str(line)
        }

        if is_producer:
            topic.producers.add(service_name)
            topic.add_producer_location(service_name, location)
            logger.debug(f"producer {service_name} with topic {topic}")
        else:
            topic.consumers.add(service_name)
            topic.add_consumer_location(service_name, location)
            logger.debug(f"consumer {service_name} with topic {topic}")

    def _extract_constants(self, content: str) -> None:
        """Extract constant topic name definitions."""
        self.constant_map.clear()
        for match in re.finditer(r'private\s+(?:static\s+final\s+)?String\s+(\w+)\s*=\s*["\']([^"\']+)["\']', content):
            var_name, value = match.groups()
            self.constant_map[var_name] = value

    def _analyze_content(self, content: str, file_path: Path, service: Service) -> Dict[str, KafkaTopic]:
        """Analyze file content for Kafka topics."""
        if self.patterns.should_ignore(content):
            logger.debug(f"Ignoring {file_path} - matches ignore pattern")
            return {}

        self.topics.clear()
        self._extract_constants(content)

        # Process producers
        for pattern in self.patterns._compiled_producers:
            for match in re.finditer(pattern.pattern, content, re.MULTILINE):
                topic_name = match.group(match.lastindex or 1)
                line = content[:match.start()].count('\n') + 1
                self._add_topic(topic_name, True, file_path, line, service.name)

        # Process consumers
        for pattern in self.patterns._compiled_consumers:
            for match in re.finditer(pattern.pattern, content, re.MULTILINE):
                line = content[:match.start()].count('\n') + 1
                topics_str = match.group(match.lastindex or 1)
                topics = []
                # Handle different formats
                if '"' in topics_str or "'" in topics_str:
                    topics.extend(re.findall(r'["\']([^"\']+)["\']', topics_str))
                else:
                    # Try variable references
                    topics.extend(t.strip() for t in topics_str.split(',') if t.strip())
                
                for topic_name in topics:
                    self._add_topic(topic_name, False, file_path, line, service.name)

        # Process @Value annotations
        for match in re.finditer(r'@Value\s*\(\s*["\']?\$\{([^}]+)\}["\']?\)', content):
            value = match.group(1)
            if 'kafka' in value.lower() and 'topic' in value.lower():
                topic_name = f"${{{value}}}"
                line = content[:match.start()].count('\n') + 1
                # Look for nearby context to determine producer/consumer
                context = content[max(0, match.start()-200):min(len(content), match.end()+200)]
                is_producer = any(word in context.lower() for word in ['producer', 'send', 'publish', '@sendto'])
                self._add_topic(topic_name, is_producer, file_path, line, service.name)

        # Process Processor.INPUT/OUTPUT references
        processor_patterns = [
            (r'Processor\.INPUT\b', False),  # consumer
            (r'Processor\.OUTPUT\b', True)   # producer
        ]

        for pattern, is_producer in processor_patterns:
            for match in re.finditer(pattern, content):
                topic_name = 'input' if not is_producer else 'output'
                line = content[:match.start()].count('\n') + 1
                self._add_topic(topic_name, is_producer, file_path, line, service.name)

        # Process variable references
        for var_name in self.constant_map:
            # Look for variable usage with producers
            for match in re.finditer(rf'(?:producer|template)\.(?:send|publish)\s*\(\s*{var_name}\b', content):
                line = content[:match.start()].count('\n') + 1
                self._add_topic(var_name, True, file_path, line, service.name)

            # Look for variable usage with consumers
            for match in re.finditer(rf'consumer\.subscribe\s*\([^)]*{var_name}\b', content):
                line = content[:match.start()].count('\n') + 1
                self._add_topic(var_name, False, file_path, line, service.name)

        # Sync with service topics
        for topic_name, topic in self.topics.items():
            if topic_name not in service.topics:
                service.topics[topic_name] = topic
            else:
                existing = service.topics[topic_name]
                existing.producers.update(topic.producers)
                existing.consumers.update(topic.consumers)
                for producer in topic.producer_locations:
                    for location in topic.producer_locations[producer]:
                        existing.add_producer_location(producer, location)
                for consumer in topic.consumer_locations:
                    for location in topic.consumer_locations[consumer]:
                        existing.add_consumer_location(consumer, location)

        return self.topics

    def analyze_file(self, file_path: Path) -> Dict[str, KafkaTopic]:
        """Analyze a Java file for Kafka topics."""
        service = Service(name=file_path.parent.name, path=file_path.parent)
        return self.analyze(file_path, service)