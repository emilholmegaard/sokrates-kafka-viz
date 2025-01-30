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
    
    def __init__(self):
        super().__init__()
        self.topics: Dict[str, KafkaTopic] = {}
        self.patterns = KafkaPatterns(
            producers={
                r'new\s+ProducerRecord\s*<[^>]*>\s*\(\s*["\']([^"\']+)["\']',
                r'(?:messageProducer|producer|kafkaTemplate|template)\.(publish|send)\s*\(\s*["\']([^"\']+)["\']',
                r'@SendTo\s*\(\s*["\']([^"\']+)["\']',
                r'@Output\s*\(\s*["\']([^"\']+)["\']'
            },
            consumers={
                r'@KafkaListener\s*\(\s*topics\s*=\s*["\']([^"\']+)["\']',
                r'@KafkaListener\s*\(\s*topics\s*=\s*\{([^}]+)\}',
                r'@StreamListener\s*\(\s*["\']([^"\']+)["\']',
                r'@Input\s*\(\s*["\']([^"\']+)["\']'
            },
            topic_configs={
                r'@Value\s*\(\s*["\']?\$\{([^}]+)\}["\']?',
                r'private\s+(?:static\s+final\s+)?String\s+\w+\s*=\s*["\']([^"\']+)["\']'
            }
        )

    def can_analyze(self, file_path: Path) -> bool:
        """Check if this analyzer can handle Java files."""
        return file_path.suffix.lower() == '.java'

    def _analyze_content(self, content: str, file_path: Path, service: Service) -> Dict[str, KafkaTopic]:
        """
        Analyze file content for Kafka topics.
        Overrides base method to handle Java-specific patterns.
        """
        if self.patterns.should_ignore(content):
            logger.debug(f"Ignoring {file_path} - matches ignore pattern")
            return {}

        # Clear topics for this analysis
        self.topics.clear()

        # Process producer patterns
        for pattern in self.patterns._compiled_producers:
            matches = re.finditer(pattern.pattern, content, re.MULTILINE)
            for match in matches:
                # Get matched topic name from last group if multiple groups
                topic_name = match.group(match.lastindex or 1).strip(' "\'"')
                if not topic_name:
                    continue
                if topic_name not in self.topics:
                    self.topics[topic_name] = KafkaTopic(topic_name)
                self.topics[topic_name].producers.add(service.name)
                self.topics[topic_name].add_producer_location(service.name, {
                    'file': str(file_path),
                    'line': content[:match.start()].count('\n') + 1
                })

        # Process consumer patterns
        for pattern in self.patterns._compiled_consumers:
            matches = re.finditer(pattern.pattern, content, re.MULTILINE)
            for match in matches:
                topics_str = match.group(match.lastindex or 1)
                topics = []
                if '"' in topics_str or "'" in topics_str:
                    topics.extend(t.strip(' "\'') for t in re.findall(r'["\']([^"\']+)["\']', topics_str))
                elif '${' in topics_str:
                    topics.extend(f"${{{t}}}" for t in re.findall(r'\$\{([^}]+)\}', topics_str))
                else:
                    topics.append(topics_str.strip())

                for topic_name in topics:
                    if topic_name not in self.topics:
                        self.topics[topic_name] = KafkaTopic(topic_name)
                    self.topics[topic_name].consumers.add(service.name)
                    self.topics[topic_name].add_consumer_location(service.name, {
                        'file': str(file_path),
                        'line': content[:match.start()].count('\n') + 1
                    })

        # Process constant/config patterns
        for pattern in self.patterns._compiled_configs:
            matches = re.finditer(pattern.pattern, content, re.MULTILINE)
            for match in matches:
                value = match.group(1)
                if ('kafka' in value.lower() and 'topic' in value.lower()):
                    topic_name = f"${{{value}}}" if value.startswith("${") or value.endswith("}") else value
                    if topic_name not in self.topics:
                        self.topics[topic_name] = KafkaTopic(topic_name)
                    # Look for nearby producer/consumer patterns
                    context = content[max(0, match.start()-200):min(len(content), match.end()+200)]
                    if any(word in context.lower() for word in ['producer', 'send', 'publish', '@sendto']):
                        self.topics[topic_name].producers.add(service.name)
                    if any(word in context.lower() for word in ['consumer', 'subscribe', 'listen', '@kafkalistener']):
                        self.topics[topic_name].consumers.add(service.name)

        # Handle variable references
        topic_refs = {}
        for match in re.finditer(r'private\s+(?:static\s+final\s+)?String\s+(\w+)\s*=\s*["\']([^"\']+)["\']', content):
            var_name, topic_name = match.groups()
            topic_refs[var_name] = topic_name

        for var_name, topic_name in topic_refs.items():
            # Look for variable usage with producers
            for match in re.finditer(rf'(?:producer|template)\.(?:send|publish)\s*\(\s*{var_name}\b', content):
                if topic_name not in self.topics:
                    self.topics[topic_name] = KafkaTopic(topic_name)
                self.topics[topic_name].producers.add(service.name)

            # Look for variable usage with consumers
            for match in re.finditer(rf'consumer\.subscribe\s*\([^)]*{var_name}\b', content):
                if topic_name not in self.topics:
                    self.topics[topic_name] = KafkaTopic(topic_name)
                self.topics[topic_name].consumers.add(service.name)

        # Fix config value formatting
        new_topics = {}
        for name, topic in self.topics.items():
            if name.startswith("kafka.") or "kafka" in name.lower():
                new_name = f"${{{name}}}"
                topic.name = new_name
                new_topics[new_name] = topic
            else:
                new_topics[name] = topic
        self.topics = new_topics

        # Sync with service topics
        for topic_name, topic in self.topics.items():
            if topic_name not in service.topics:
                service.topics[topic_name] = topic
            else:
                service.topics[topic_name].producers.update(topic.producers)
                service.topics[topic_name].consumers.update(topic.consumers)
                # Ensure locations are properly updated
                for producer in topic.producer_locations:
                    for location in topic.producer_locations[producer]:
                        service.topics[topic_name].add_producer_location(producer, location)
                for consumer in topic.consumer_locations:
                    for location in topic.consumer_locations[consumer]:
                        service.topics[topic_name].add_consumer_location(consumer, location)

        return self.topics

    def analyze_file(self, file_path: Path) -> List[KafkaTopic]:
        """Analyze a Java file for Kafka topics, keeping backward compatibility."""
        service = Service(name=file_path.parent.name, path=file_path.parent)
        topics_dict = self.analyze(file_path, service)
        return list(topics_dict.values())