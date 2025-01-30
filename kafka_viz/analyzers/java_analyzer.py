import re
from typing import List, Set
from pathlib import Path
from ..models.schema import KafkaTopic
from .base import BaseAnalyzer

class JavaAnalyzer(BaseAnalyzer):
    def __init__(self):
        self.topics: Set[KafkaTopic] = set()
        
    def can_analyze(self, file_path: Path) -> bool:
        """Check if this analyzer can handle Java files."""
        return file_path.suffix.lower() == '.java'

    def analyze(self, file_path: Path, service) -> List[KafkaTopic]:
        """
        Analyze a Java file for Kafka topic patterns.
        Supports both basic patterns and advanced patterns including:
        - Record-based producers
        - Configuration-based topics
        - Collection-based subscriptions
        - Container factory configs
        - Spring Cloud Stream patterns
        """
        self.topics.clear()
        content = file_path.read_text()
        
        self._find_record_based_producers(content, service.name, file_path)
        self._find_collection_based_consumers(content, service.name, file_path)
        self._find_container_configs(content, service.name, file_path)
        self._find_stream_patterns(content, service.name, file_path)
        self._find_value_annotations(content, service.name, file_path)
        
        return list(self.topics)

    def _get_or_create_topic(self, name: str) -> KafkaTopic:
        """Get existing topic or create new one."""
        for topic in self.topics:
            if topic.name == name:
                return topic
        topic = KafkaTopic(name=name)
        self.topics.add(topic)
        return topic

    def _find_record_based_producers(self, content: str, service_name: str, file_path: Path):
        # Match ProducerRecord constructor patterns
        producer_records = re.finditer(
            r'new\s+ProducerRecord\s*<[^>]*>\s*\(\s*["\']([^"\']+)["\']',
            content
        )
        for match in producer_records:
            topic = self._get_or_create_topic(match.group(1))
            topic.producers.add(service_name)
            topic.add_producer_location(service_name, {
                'file': str(file_path),
                'line': content[:match.start()].count('\n') + 1
            })

        # Match messageProducer.publish patterns
        publish_calls = re.finditer(
            r'(?:messageProducer|producer)\.(publish|send)\s*\(\s*["\']([^"\']+)["\']',
            content
        )
        for match in publish_calls:
            topic = self._get_or_create_topic(match.group(2))
            topic.producers.add(service_name)
            topic.add_producer_location(service_name, {
                'file': str(file_path),
                'line': content[:match.start()].count('\n') + 1
            })

        # Match kafkaTemplate.send patterns
        template_sends = re.finditer(
            r'(?:kafkaTemplate|template)\.send\s*\(\s*([^,\)]+)',
            content
        )
        for match in template_sends:
            topic_name = match.group(1).strip()
            if topic_name.startswith(('configuredTopic', '${', 'kafka.')):
                topic = self._get_or_create_topic(topic_name)
                topic.producers.add(service_name)
                topic.add_producer_location(service_name, {
                    'file': str(file_path),
                    'line': content[:match.start()].count('\n') + 1
                })

    def _find_collection_based_consumers(self, content: str, service_name: str, file_path: Path):
        # Match Arrays.asList and Set.of patterns
        collection_patterns = [
            r'Arrays\.asList\s*\((.*?)\)',
            r'Set\.of\s*\((.*?)\)',
            r'List\.of\s*\((.*?)\)'
        ]
        
        for pattern in collection_patterns:
            collections = re.finditer(pattern, content)
            for match in collections:
                topics_str = match.group(1)
                topics = re.findall(r'["\']([^"\']+)["\']', topics_str)
                for topic_name in topics:
                    topic = self._get_or_create_topic(topic_name)
                    topic.consumers.add(service_name)
                    topic.add_consumer_location(service_name, {
                        'file': str(file_path),
                        'line': content[:match.start()].count('\n') + 1
                    })

        # Match @KafkaListener with multiple topics
        kafka_listeners = re.finditer(
            r'@KafkaListener\s*\(\s*(?:[^)]*?topics\s*=\s*)\{([^}]+)\}',
            content
        )
        for match in kafka_listeners:
            topics_str = match.group(1)
            # Match both string literals and ${} expressions
            topics = re.findall(r'["\']([^"\']+)["\']|\$\{([^}]+)\}', topics_str)
            for topic_groups in topics:
                topic_name = next(t for t in topic_groups if t)  # Get non-empty group
                topic = self._get_or_create_topic(topic_name)
                topic.consumers.add(service_name)
                topic.add_consumer_location(service_name, {
                    'file': str(file_path),
                    'line': content[:match.start()].count('\n') + 1
                })

    def _find_container_configs(self, content: str, service_name: str, file_path: Path):
        # Match containerFactory patterns with @KafkaListener
        factory_configs = re.finditer(
            r'@KafkaListener\s*\(\s*(?:[^)]*?topics\s*=\s*["\']?\$\{([^}]+)\}["\']?)',
            content
        )
        for match in factory_configs:
            topic_name = f"${{{match.group(1)}}}"
            topic = self._get_or_create_topic(topic_name)
            topic.consumers.add(service_name)
            topic.add_consumer_location(service_name, {
                'file': str(file_path),
                'line': content[:match.start()].count('\n') + 1
            })

    def _find_stream_patterns(self, content: str, service_name: str, file_path: Path):
        # Match @Output channel definitions
        outputs = re.finditer(r'@Output\s*\(\s*["\']([^"\']+)["\']', content)
        for match in outputs:
            topic = self._get_or_create_topic(match.group(1))
            topic.producers.add(service_name)
            topic.add_producer_location(service_name, {
                'file': str(file_path),
                'line': content[:match.start()].count('\n') + 1
            })

        # Match @Input channel definitions
        inputs = re.finditer(r'@Input\s*\(\s*["\']([^"\']+)["\']', content)
        for match in inputs:
            topic = self._get_or_create_topic(match.group(1))
            topic.consumers.add(service_name)
            topic.add_consumer_location(service_name, {
                'file': str(file_path),
                'line': content[:match.start()].count('\n') + 1
            })

        # Match StreamListener patterns
        stream_listeners = re.finditer(
            r'@StreamListener\s*\(\s*(?:target\s*=\s*)?([^,\)]+)',
            content
        )
        for match in stream_listeners:
            target = match.group(1).strip()
            if target.startswith('Processor.'):
                channel = target.split('.')[-1].lower()
                topic = self._get_or_create_topic(channel)
                topic.consumers.add(service_name)
                topic.add_consumer_location(service_name, {
                    'file': str(file_path),
                    'line': content[:match.start()].count('\n') + 1
                })

        # Match SendTo patterns
        send_to = re.finditer(r'@SendTo\s*\(\s*([^,\)]+)', content)
        for match in send_to:
            target = match.group(1).strip()
            if target.startswith('Processor.'):
                channel = target.split('.')[-1].lower()
                topic = self._get_or_create_topic(channel)
                topic.producers.add(service_name)
                topic.add_producer_location(service_name, {
                    'file': str(file_path),
                    'line': content[:match.start()].count('\n') + 1
                })