"""Kafka pattern analyzer for different programming languages."""
import re
from pathlib import Path
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass, field
import logging

from ..core.analyzer import BaseAnalyzer
from ..core.config import Config
from ..core.errors import AnalyzerError
from ..models.service import Service
from ..models.schema import KafkaTopic

logger = logging.getLogger(__name__)

@dataclass
class KafkaPatterns:
    """Language-specific Kafka patterns."""
    producers: Set[str] = field(default_factory=set)
    consumers: Set[str] = field(default_factory=set)

class LanguagePatterns:
    """Kafka patterns for different programming languages."""
    
    JAVA = KafkaPatterns(
        producers={
            r'@KafkaProducer\s*\(\s*topics\s*=\s*[\"\']([^\"\']+)',
            r'@SendTo\s*\(\s*[\"\']([^\"\']+)',
            r'\.send\s*\(\s*[\"\']([^\"\']+)',
            r'ProducerRecord\s*<[^>]*>\s*\(\s*[\"\']([^\"\']+)'
        },
        consumers={
            r'@KafkaListener\s*\(\s*topics\s*=\s*[\"\']([^\"\']+)',
            r'@KafkaHandler\s*\([^)]*[\"\']([^\"\']+)',
            r'ConsumerRecord\s*<[^>]*>\s*\w+\s*[,\)]'
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

class KafkaAnalyzer(BaseAnalyzer):
    """Analyzes source code and configuration for Kafka patterns."""

    def __init__(self):
        """Initialize Kafka analyzer with language patterns."""
        self.language_patterns = {
            'java': LanguagePatterns.JAVA,
            'kt': LanguagePatterns.JAVA,  # Kotlin uses same patterns
            'scala': LanguagePatterns.JAVA,  # Scala uses similar patterns
            'py': LanguagePatterns.PYTHON,
            'cs': LanguagePatterns.CSHARP
        }
        
        self.config_patterns = {
            'application.properties': r'kafka\.topic\.([^=]+)\s*=\s*([^\n]+)',
            'application.yaml': r'kafka:\s+topics:\s+([^:]+):\s+([^\n]+)',
            'application.yml': r'kafka:\s+topics:\s+([^:]+):\s+([^\n]+)'
        }
        
        self.topics: Dict[str, KafkaTopic] = {}

    async def analyze(self, config: Config) -> Dict[str, Any]:
        """Analyze services for Kafka patterns.
        
        Args:
            config: Analysis configuration
            
        Returns:
            Dictionary containing discovered topics and analysis results
        """
        try:
            analyzer_config = config.get_analyzer_config('kafka')
            if not analyzer_config:
                raise AnalyzerError('Kafka analyzer configuration not found')
            
            # Reset topics for new analysis
            self.topics = {}
            
            # Get services from configuration
            services = self._get_services_from_config(config)
            
            # Analyze each service
            for service_name, service in services.items():
                logger.info(f'Analyzing service {service_name} for Kafka patterns')
                
                # Analyze source files
                for source_file in service.root_path.rglob('*'):
                    if source_file.is_file():
                        # Analyze source code
                        file_topics = self.analyze_file(source_file, service)
                        if file_topics:
                            self._merge_topics(file_topics)
                            
                        # Analyze config files
                        config_topics = self.analyze_config(source_file, service)
                        if config_topics:
                            self._merge_topics(config_topics)
            
            # Filter topics based on patterns if configured
            if hasattr(analyzer_config, 'topics_patterns'):
                filtered_topics = self._filter_topics(
                    self.topics,
                    analyzer_config.topics_patterns,
                    getattr(analyzer_config, 'exclude_patterns', [])
                )
            else:
                filtered_topics = self.topics
            
            return {
                'topics': filtered_topics,
                'total_count': len(filtered_topics),
                'by_service': self._group_by_service(filtered_topics),
                'orphaned_topics': self._find_orphaned_topics(filtered_topics)
            }
            
        except Exception as e:
            raise AnalyzerError(f'Kafka analysis failed: {str(e)}') from e

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
        except Exception as e:
            logger.warning(f'Error reading file {file_path}: {e}')
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

    def analyze_config(
        self, 
        config_file: Path,
        service: Service
    ) -> Optional[Dict[str, KafkaTopic]]:
        """Analyze a configuration file for Kafka topic definitions."""
        if config_file.name not in self.config_patterns:
            return None

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f'Error reading config file {config_file}: {e}')
            return None

        pattern = self.config_patterns[config_file.name]
        topics = {}

        for match in re.finditer(pattern, content):
            topic_name = match.group(2).strip('" \'')
            if topic_name not in topics:
                topics[topic_name] = KafkaTopic(name=topic_name)
                # Service defining a topic is likely a producer
                topics[topic_name].producers.add(service.name)

        return topics if topics else None

    def _should_analyze_file(self, file_path: Path) -> bool:
        """Determine if a file should be analyzed."""
        # Only analyze source code files
        return file_path.suffix.lstrip('.') in self.language_patterns
    
    def _merge_topics(self, new_topics: Dict[str, KafkaTopic]) -> None:
        """Merge new topics into existing topics."""
        for topic_name, topic in new_topics.items():
            if topic_name not in self.topics:
                self.topics[topic_name] = topic
            else:
                self.topics[topic_name].producers.update(topic.producers)
                self.topics[topic_name].consumers.update(topic.consumers)
    
    def _filter_topics(self
        self,
        topics: Dict[str, KafkaTopic],
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> Dict[str, KafkaTopic]:
        """Filter topics based on include and exclude patterns."""
        filtered = {}
        
        for topic_name, topic in topics.items():
            # Check if topic matches any include pattern
            included = any(re.match(pattern, topic_name) 
                         for pattern in include_patterns)
            
            # Check if topic matches any exclude pattern
            excluded = any(re.match(pattern, topic_name) 
                          for pattern in exclude_patterns)
            
            if included and not excluded:
                filtered[topic_name] = topic
                
        return filtered
    
    def _group_by_service(self, topics: Dict[str, KafkaTopic]) -> Dict[str, Dict[str, Set[str]]]:
        """Group topics by service showing produce/consume relationships."""
        by_service = {}
        
        for topic_name, topic in topics.items():
            # Add producers
            for producer in topic.producers:
                if producer not in by_service:
                    by_service[producer] = {'produces': set(), 'consumes': set()}
                by_service[producer]['produces'].add(topic_name)
            
            # Add consumers
            for consumer in topic.consumers:
                if consumer not in by_service:
                    by_service[consumer] = {'produces': set(), 'consumes': set()}
                by_service[consumer]['consumes'].add(topic_name)
                
        return by_service
    
    def _find_orphaned_topics(self, topics: Dict[str, KafkaTopic]) -> List[str]:
        """Find topics with no producers or consumers."""
        return [name for name, topic in topics.items() 
                if not topic.producers and not topic.consumers]