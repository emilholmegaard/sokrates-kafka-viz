"""Kafka pattern analyzer for different programming languages."""
import re
from pathlib import Path
from typing import Dict, Set, Optional, Tuple
from dataclasses import dataclass, field

from .base import BaseAnalyzer, KafkaPatterns
from ..models.service import Service
from ..models.schema import KafkaTopic

class KafkaAnalyzer(BaseAnalyzer):
    """Analyzes source code for Kafka patterns."""

    def __init__(self):
        """Initialize with language-specific patterns."""
        super().__init__()
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
            topics = self.analyze(file_path, service)
            if topics:
                for topic_name, topic in topics.items():
                    if topic_name not in all_topics:
                        all_topics[topic_name] = topic
                    else:
                        # Merge producers and consumers
                        all_topics[topic_name].producers.update(topic.producers)
                        all_topics[topic_name].consumers.update(topic.consumers)
    
        return all_topics

    def can_analyze(self, file_path: Path) -> bool:
        """Determine if a file should be analyzed."""
        # Only analyze source code files
        return file_path.suffix.lstrip('.') in self.language_patterns

    def get_patterns(self) -> KafkaPatterns:
        """Get patterns for the current file language."""
        # Get language from file extension if available
        if hasattr(self, 'current_file') and self.current_file:
            lang = self.current_file.suffix.lstrip('.')
            if lang in self.language_patterns:
                return self.language_patterns[lang]
        # Return Java patterns as default
        return LanguagePatterns.JAVA

    def _analyze_content(
        self, 
        content: str, 
        file_path: Path,
        service: Service
    ) -> Optional[Dict[str, KafkaTopic]]:
        """Analyze file content for Kafka patterns."""
        # Store current file for pattern selection
        self.current_file = file_path
        return super()._analyze_content(content, file_path, service)

class LanguagePatterns:
    """Kafka patterns for different programming languages."""
    
    JAVA = KafkaPatterns(
        producers={
            # Spring Kafka Producer patterns
            r'@KafkaProducer\s*\(\s*topics\s*=\s*["\']([\w.-]+)["\']',
            r'@KafkaProducer\s*\(\s*topic\s*=\s*["\']([\w.-]+)["\']',
            r'@SendTo\s*\(\s*["\']([\w.-]+)["\']',
            r'@Topic\s*\(\s*["\']([\w.-]+)["\']',
            
            # Producer method/API calls
            r'\.send\s*\(\s*["\']([\w.-]+)["\']',
            r'\.send\(new\s+ProducerRecord\s*<[^>]*>\s*\(\s*["\']([\w.-]+)["\']',
            r'ProducerRecord\s*<[^>]*>\s*\(\s*["\']([\w.-]+)["\']',
            r'\.send\(\s*["\']([\w.-]+)["\']',
            
            # Spring Kafka Template
            r'kafkaTemplate\.send\(\s*["\']([\w.-]+)["\']',
            r'KafkaTemplate<[^>]*>\.send\(\s*["\']([\w.-]+)["\']',
            
            # Configuration patterns
            r'@Bean\s*\(\s*name\s*=\s*["\']([\w.-]+)-producer["\']',
            r'\.setTopicName\(\s*["\']([\w.-]+)["\']',
            r'\.forTopic\(\s*["\']([\w.-]+)["\']',
            
            # Property based patterns
            r'kafka\.topic\s*=\s*["\']([\w.-]+)["\']',
            r'kafka\.producer\.topic\s*=\s*["\']([\w.-]+)["\']',
            r'spring\.kafka\.template\.default-topic\s*=\s*["\']([\w.-]+)["\']'
        },
        consumers={
            # Spring Kafka Consumer patterns
            r'@KafkaListener\s*\(\s*topics\s*=\s*["\']([\w.-]+)["\']',
            r'@KafkaListener\s*\(\s*topicPattern\s*=\s*["\']([\w.-]+)["\']',
            r'@KafkaHandler\s*\([^)]*["\']([\w.-]+)["\']',
            
            # Consumer API patterns
            r'ConsumerRecord\s*<[^>]*>\s*\(\s*["\']([\w.-]+)["\']',
            r'\.subscribe\(\s*Collections\.singletonList\(\s*["\']([\w.-]+)["\']',
            r'\.subscribe\(\s*Arrays\.asList\([^)]*["\']([\w.-]+)["\']',
            r'\.subscribe\(\s*["\']([\w.-]+)["\']',
            
            # Configuration patterns
            r'@Bean\s*\(\s*name\s*=\s*["\']([\w.-]+)-consumer["\']',
            r'containerFactory\s*=\s*["\']([\w.-]+)KafkaListenerContainerFactory["\']',
            
            # Property based patterns
            r'kafka\.consumer\.topic\s*=\s*["\']([\w.-]+)["\']',
            r'spring\.kafka\.consumer\.topics\s*=\s*["\']([\w.-]+)["\']',
            r'spring\.kafka\.consumer\.topic-pattern\s*=\s*["\']([\w.-]+)["\']',
            
            # Method level patterns
            r'@StreamListener\s*\(\s*["\']([\w.-]+)["\']',
            r'@Input\s*\(\s*["\']([\w.-]+)["\']'
        }
    )
    
    PYTHON = KafkaPatterns(
        producers={
            r'KafkaProducer\s*\([^)]*\)\.send\s*\(\s*[\"\']([\w.-]+)',
            r'producer\.send\s*\(\s*[\"\']([\w.-]+)'
        },
        consumers={
            r'KafkaConsumer\s*\([^)]*[\"\']([\w.-]+)',
            r'consumer\.subscribe\s*\(\s*\[[\"\']([\w.-]+)'
        }
    )
    
    CSHARP = KafkaPatterns(
        producers={
            r'\.Produce\s*\(\s*[\"\']([\w.-]+)',
            r'ProducerBuilder\s*<[^>]*>\s*\.\s*SetTopic\s*\(\s*[\"\']([\w.-]+)',
            r'\.ProduceAsync\s*\(\s*[\"\']([\w.-]+)'
        },
        consumers={
            r'\.Subscribe\s*\(\s*[\"\']([\w.-]+)',
            r'ConsumerBuilder\s*<[^>]*>\s*\.\s*Subscribe\s*\(\s*[\"\']([\w.-]+)'
        }
    )