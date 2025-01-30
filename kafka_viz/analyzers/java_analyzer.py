import re
from typing import Dict, Set, Optional
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
                r'(?:messageProducer|producer|template|kafkaTemplate)\.(publish|send)\s*\(\s*["\']([^"\']+)["\']',
                r'@SendTo\s*\(\s*["\']([^"\']+)["\']',
                r'@Output\s*\(\s*["\']([^"\']+)["\']'
            },
            consumers={
                r'@KafkaListener\s*\(\s*topics\s*=\s*["\']([^"\']+)["\']',
                r'@KafkaListener\s*\(\s*topics\s*=\s*\{([^}]+)\}',
                r'@StreamListener\s*\(\s*["\']([^"\']+)["\']',
                r'@Input\s*\(\s*["\']([^"\']+)["\']',
                r'consumer\.subscribe\s*\(\s*Arrays\.asList\s*\((.*?)\)',
                r'consumer\.subscribe\s*\(\s*Set\.of\s*\((.*?)\)'
            },
            topic_configs={
                r'@Value\s*\(\s*["\']?\$\{([^}]+)\}["\']?',
                r'private\s+(?:static\s+final\s+)?String\s+\w+\s*=\s*["\']([^"\']+)["\']'
            }
        )

    def can_analyze(self, file_path: Path) -> bool:
        """Check if this analyzer can handle Java files."""
        return file_path.suffix.lower() == '.java'

    def analyze_file(self, file_path: Path) -> Dict[str, KafkaTopic]:
        """Analyze a Java file for Kafka topics, keeping backward compatibility."""
        dummy_service = Service(name=file_path.parent.name, path=file_path.parent)
        return self.analyze(file_path, dummy_service)

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
            for match in pattern.finditer(content):
                # Get matched topic name(s)
                if ',' in match.group(1):  # Handle comma-separated topics
                    topics = [t.strip(' "\'') for t in match.group(1).split(',')]
                else:
                    topics = [match.group(1).strip(' "\'')]
                
                for topic_name in topics:
                    if not topic_name:
                        continue
                    if topic_name not in self.topics:
                        self.topics[topic_name] = KafkaTopic(topic_name)
                    self.topics[topic_name].producers.add(service.name)
                    self.topics[topic_name].add_producer_location(service_name=service.name, location={
                        'file': str(file_path),
                        'line': content[:match.start()].count('\n') + 1
                    })

        # Process consumer patterns
        for pattern in self.patterns._compiled_consumers:
            for match in pattern.finditer(content):
                topics_str = match.group(1)
                # Handle different topic list formats
                topics = []
                if '"' in topics_str or "'" in topics_str:
                    topics.extend(re.findall(r'["\']([^"\']+)["\']', topics_str))
                elif '${' in topics_str:
                    topics.extend(re.findall(r'\$\{([^}]+)\}', topics_str))
                
                for topic_name in topics:
                    if topic_name not in self.topics:
                        self.topics[topic_name] = KafkaTopic(topic_name)
                    self.topics[topic_name].consumers.add(service.name)
                    self.topics[topic_name].add_consumer_location(service_name=service.name, location={
                        'file': str(file_path),
                        'line': content[:match.start()].count('\n') + 1
                    })

        # Process constant/config patterns
        for pattern in self.patterns._compiled_configs:
            for match in pattern.finditer(content):
                value = match.group(1)
                if ('kafka' in value.lower() and 'topic' in value.lower()) or \
                   ('topic' in match.string[max(0, match.start()-20):match.start()].lower()):
                    topic_name = value
                    if topic_name not in self.topics:
                        self.topics[topic_name] = KafkaTopic(topic_name)
                        
                    # Look for nearby producer/consumer patterns
                    context = match.string[max(0, match.start()-100):min(len(match.string), match.end()+100)]
                    if any(word in context.lower() for word in ['producer', 'send', 'publish']):
                        self.topics[topic_name].producers.add(service.name)
                    if any(word in context.lower() for word in ['consumer', 'subscribe', 'listen']):
                        self.topics[topic_name].consumers.add(service.name)

        # Sync with service topics
        for topic_name, topic in self.topics.items():
            if topic_name not in service.topics:
                service.topics[topic_name] = topic
            else:
                service.topics[topic_name].producers.update(topic.producers)
                service.topics[topic_name].consumers.update(topic.consumers)
                service.topics[topic_name].producer_locations.update(topic.producer_locations)
                service.topics[topic_name].consumer_locations.update(topic.consumer_locations)

        return self.topics