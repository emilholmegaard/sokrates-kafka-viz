import re
import logging
from typing import List, Set
from pathlib import Path
from ..models import KafkaTopic, TopicType

logger = logging.getLogger(__name__)

class JavaAnalyzer:
    def __init__(self):
        self.topics: Set[KafkaTopic] = set()
        
    def analyze_file(self, file_path: Path) -> List[KafkaTopic]:
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
        logger.info(f"Analyzing file: {file_path}")
        content = file_path.read_text()
        
        logger.debug("Starting pattern analysis...")
        self._find_record_based_producers(content)
        self._find_collection_based_consumers(content)
        self._find_container_configs(content)
        self._find_stream_patterns(content)
        self._find_value_annotations(content)
        
        logger.info(f"Found {len(self.topics)} topics in {file_path}")
        logger.debug(f"Topics found: {[t.name for t in self.topics]}")
        return list(self.topics)

    def _find_record_based_producers(self, content: str):
        logger.debug("Searching for record-based producers...")
        # Match ProducerRecord constructor patterns
        producer_records = re.finditer(
            r'new\s+ProducerRecord\s*<[^>]*>\s*\(\s*["\']([^"\'])+["\']',
            content
        )
        for match in producer_records:
            topic = match.group(1)
            logger.debug(f"Found ProducerRecord topic: {topic}")
            self.topics.add(KafkaTopic(topic, TopicType.PRODUCER))

        # Match messageProducer.publish patterns
        publish_calls = re.finditer(
            r'(?:messageProducer|producer)\.publish\s*\(\s*["\']([^"\'])+["\']',
            content
        )
        for match in publish_calls:
            topic = match.group(1)
            logger.debug(f"Found messageProducer.publish topic: {topic}")
            self.topics.add(KafkaTopic(topic, TopicType.PRODUCER))

        # Match kafkaTemplate.send patterns
        template_sends = re.finditer(
            r'(?:kafkaTemplate|template)\.send\s*\(\s*([^,\)]+)',
            content
        )
        for match in template_sends:
            topic = match.group(1).strip()
            if topic.startswith(('configuredTopic', '${', 'kafka.')):
                logger.debug(f"Found kafkaTemplate.send topic: {topic}")
                self.topics.add(KafkaTopic(topic, TopicType.PRODUCER))

    def _find_collection_based_consumers(self, content: str):
        logger.debug("Searching for collection-based consumers...")
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
                topics = re.findall(r'["\']([^"\'])+["\']', topics_str)
                for topic in topics:
                    logger.debug(f"Found collection-based topic: {topic}")
                    self.topics.add(KafkaTopic(topic, TopicType.CONSUMER))

        # Match @KafkaListener with multiple topics
        kafka_listeners = re.finditer(
            r'@KafkaListener\s*\(\s*(?:[^)]*?topics\s*=\s*)\{([^}]+)\}',
            content
        )
        for match in kafka_listeners:
            topics_str = match.group(1)
            # Match both string literals and ${} expressions
            topics = re.findall(r'["\']([^"\'])+["\']|\$\{([^}]+)\}', topics_str)
            for topic_groups in topics:
                topic = next(t for t in topic_groups if t)  # Get non-empty group
                logger.debug(f"Found @KafkaListener topic: {topic}")
                self.topics.add(KafkaTopic(topic, TopicType.CONSUMER))

    def _find_container_configs(self, content: str):
        logger.debug("Searching for container configurations...")
        # Match containerFactory patterns with @KafkaListener
        factory_configs = re.finditer(
            r'@KafkaListener\s*\(\s*(?:[^)]*?topics\s*=\s*["\']?\$\{([^}]+)\}["\']?)',
            content
        )
        for match in factory_configs:
            topic = f"${{{match.group(1)}}}"
            logger.debug(f"Found container factory topic: {topic}")
            self.topics.add(KafkaTopic(topic, TopicType.CONSUMER))

    def _find_stream_patterns(self, content: str):
        logger.debug("Searching for stream patterns...")
        # Match @Output channel definitions
        outputs = re.finditer(r'@Output\s*\(\s*["\']([^"\'])+["\']', content)
        for match in outputs:
            topic = match.group(1)
            logger.debug(f"Found @Output channel: {topic}")
            self.topics.add(KafkaTopic(topic, TopicType.PRODUCER))

        # Match @Input channel definitions
        inputs = re.finditer(r'@Input\s*\(\s*["\']([^"\'])+["\']', content)
        for match in inputs:
            topic = match.group(1)
            logger.debug(f"Found @Input channel: {topic}")
            self.topics.add(KafkaTopic(topic, TopicType.CONSUMER))

        # Match StreamListener patterns
        stream_listeners = re.finditer(
            r'@StreamListener\s*\(\s*(?:target\s*=\s*)?([^,\)]+)',
            content
        )
        for match in stream_listeners:
            target = match.group(1).strip()
            if target.startswith('Processor.'):
                channel = target.split('.')[-1].lower()
                logger.debug(f"Found @StreamListener channel: {channel}")
                self.topics.add(KafkaTopic(channel, TopicType.CONSUMER))

        # Match SendTo patterns
        send_to = re.finditer(r'@SendTo\s*\(\s*([^,\)]+)', content)
        for match in send_to:
            target = match.group(1).strip()
            if target.startswith('Processor.'):
                channel = target.split('.')[-1].lower()
                logger.debug(f"Found @SendTo channel: {channel}")
                self.topics.add(KafkaTopic(channel, TopicType.PRODUCER))

    def _find_value_annotations(self, content: str):
        logger.debug("Searching for @Value annotations...")
        # Match @Value annotations with kafka topic configurations
        value_annotations = re.finditer(
            r'@Value\s*\(\s*["\']?\$\{([^}]+)\}["\']?',
            content
        )
        for match in value_annotations:
            config = match.group(1)
            if 'kafka' in config.lower() and 'topic' in config.lower():
                topic = f"${{{config}}}"
                logger.debug(f"Found @Value kafka topic: {topic}")
                self.topics.add(KafkaTopic(topic, TopicType.PRODUCER))
