"""Kafka pattern analyzer for different programming languages."""
import re
from pathlib import Path
from typing import Dict, Set, Optional, Tuple
from dataclasses import dataclass, field

from ..models.service import Service
from ..models.schema import KafkaTopic

@dataclass
class KafkaPatterns:
    """Language-specific Kafka patterns."""
    producers: Set[str] = field(default_factory=set)
    consumers: Set[str] = field(default_factory=set)

class LanguagePatterns:
    """Kafka patterns for different programming languages."""
    
    JAVA = KafkaPatterns(
        producers={
            # Kafka Producer annotation with both single and double quotes
            r'@KafkaProducer\s*\(\s*topics\s*=\s*["\']([^"\']+)["\']',
            # Spring SendTo annotation
            r'@SendTo\s*\(\s*["\']([^"\']+)["\']',
            # Direct producer send method
            r'\.send\s*\(\s*["\']([^"\']+)["\']',
            # Kafka ProducerRecord constructor
            r'ProducerRecord\s*<[^>]*>\s*\(\s*["\']([^"\']+)["\']'
        },
        consumers={
            # Kafka Listener annotation
            r'@KafkaListener\s*\(\s*topics\s*=\s*["\']([^"\']+)["\']',
            # Kafka Handler annotation
            r'@KafkaHandler\s*\([^)]*["\']([^"\']+)["\']',
            # ConsumerRecord pattern with capture group for topic
            r'ConsumerRecord\s*<[^>]*>\s*\(\s*["\']([^"\']+)["\']'
        }
    )
    
    PYTHON = KafkaPatterns(
        producers={
            r'KafkaProducer\s*\([^)]*\)\.send\s*\(\s*[\"\']([^\"\']+)',
            r'producer\.send\s*\(\s*[\"\']([^\"\']+)'
        },
        consumers={
            r'KafkaConsumer\s*\([^)]*[\"\']([^\"\']+)',
            r'consumer\.subscribe\s*\(\s*\[[\"\']([^\"\']+)'
        }
    )
    
    CSHARP = KafkaPatterns(
        producers={
            r'\.Produce\s*\(\s*[\"\']([^\"\']+)',
            r'ProducerBuilder\s*<[^>]*>\s*\.\s*SetTopic\s*\(\s*[\"\']([^\"\']+)',
            r'\.ProduceAsync\s*\(\s*[\"\']([^\"\']+)'
        },
        consumers={
            r'\.Subscribe\s*\(\s*[\"\']([^\"\']+)',
            r'ConsumerBuilder\s*<[^>]*>\s*\.\s*Subscribe\s*\(\s*[\"\']([^\"\']+)'
        }
    )

class KafkaAnalyzer:
    """Analyzes source code for Kafka patterns."""

    def __init__(self):
        self.language_patterns = {
            'java': LanguagePatterns.JAVA,
            'kt': LanguagePatterns.JAVA,  # Kotlin uses same patterns
            'scala': LanguagePatterns.JAVA,  # Scala uses similar patterns
            'py': LanguagePatterns.PYTHON,
            'cs': LanguagePatterns.CSHARP
        }

    def analyze_service(self, service: Service) -> Dict[str, KafkaTopic]:
        """Analyze all files in a service for Kafka patterns."""
        all_topics = {}
    
        for file_path in service.source_files:
            topics = self.analyze_file(file_path, service)
            if topics:
                for topic_name, topic in topics.items():
                    if topic_name not in all_topics:
                        all_topics[topic_name] = topic
                    else:
                        # Merge producers and consumers
                        all_topics[topic_name].producers.update(topic.producers)
                        all_topics[topic_name].consumers.update(topic.consumers)
    
        return all_topics

    def analyze_file(
        self, 
        file_path: Path, 
        service: Service
    ) -> Optional[Dict[str, KafkaTopic]]:
        """Analyze a single file for Kafka patterns."""
        if not self._should_analyze_file(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            return None

        language = file_path.suffix.lstrip('.')
        patterns = self.language_patterns.get(language)
        
        if not patterns:
            return None

        topics = {}
        
        # Find producers
        for pattern in patterns.producers:
            for match in re.finditer(pattern, content):
                topic_name = match.group(1)
                if topic_name not in topics:
                    topics[topic_name] = KafkaTopic(name=topic_name)
                topics[topic_name].producers.add(service.name)

        # Find consumers
        for pattern in patterns.consumers:
            for match in re.finditer(pattern, content):
                topic_name = match.group(1)
                if topic_name not in topics:
                    topics[topic_name] = KafkaTopic(name=topic_name)
                topics[topic_name].consumers.add(service.name)

        return topics if topics else None

    def _should_analyze_file(self, file_path: Path) -> bool:
        """Determine if a file should be analyzed."""
        # Only analyze source code files
        return file_path.suffix.lstrip('.') in self.language_patterns

class KafkaConfigAnalyzer:
    """Analyzes Kafka configuration files."""

    CONFIG_PATTERNS = {
        'application.properties': r'kafka\.topic\.([^=]+)\s*=\s*([^\n]+)',
        'application.yaml': r'kafka:\s+topics:\s+([^:]+):\s+([^\n]+)',
        'application.yml': r'kafka:\s+topics:\s+([^:]+):\s+([^\n]+)'
    }

    def analyze_config(
        self, 
        config_file: Path,
        service: Service
    ) -> Optional[Dict[str, KafkaTopic]]:
        """Analyze a configuration file for Kafka topic definitions."""
        if config_file.name not in self.CONFIG_PATTERNS:
            return None

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return None

        pattern = self.CONFIG_PATTERNS[config_file.name]
        topics = {}

        for match in re.finditer(pattern, content):
            topic_name = match.group(2).strip('" \'')
            if topic_name not in topics:
                topics[topic_name] = KafkaTopic(name=topic_name)

        return topics if topics else None