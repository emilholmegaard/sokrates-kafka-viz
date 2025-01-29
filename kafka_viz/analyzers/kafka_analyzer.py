import re
from pathlib import Path
from typing import Dict, Optional, Set
import logging

from kafka_viz.models import Service, KafkaTopic
from .base import BaseAnalyzer, KafkaPatterns

logger = logging.getLogger(__name__)

class KafkaAnalyzer(BaseAnalyzer):
    """Analyzer for finding Kafka usage patterns in code."""

    def __init__(self):
        super().__init__()
        # Define regex patterns for Kafka usage
        self.patterns = KafkaPatterns(
            producers={
                # Plain Kafka patterns
                r'new\s+ProducerRecord\s*<[^>]*>\s*\(\s*"([^"]+)"',  # ProducerRecord constructor
                r'\.send\s*\(\s*"([^"]+)"',  # Direct send
                r'kafkaTemplate\.send\s*\(\s*"([^"]+)"',  # KafkaTemplate send
                
                # Spring Cloud Stream patterns
                r'@SendTo\s*\(\s*"([^"]+)"\s*\)',  # SendTo annotation
                r'@Output\s*\(\s*"([^"]+)"\s*\)',  # Output channel
            },
            consumers={
                # Plain Kafka patterns
                r'\.subscribe\s*\(\s*(?:Arrays\.asList|List\.of)\s*\(\s*"([^"]+)"\s*\)',  # Subscribe
                r'@KafkaListener\s*\(\s*topics\s*=\s*"([^"]+)"\s*\)',  # Single topic
                r'@KafkaListener\s*\(\s*topics\s*=\s*\{\s*"([^"]+)"\s*\}\s*\)',  # Array topics
                
                # Spring Cloud Stream patterns
                r'@StreamListener\s*\(\s*"([^"]+)"\s*\)',  # StreamListener
                r'@Input\s*\(\s*"([^"]+)"\s*\)',  # Input channel
            },
            topic_configs={
                # Configuration patterns
                r'(?:private|public|static)\s+(?:final\s+)?String\s+([A-Z_]+)\s*=\s*"([^"]+)"',  # Constants
                r'@Value\s*\(\s*"\$\{([^}]+\.topic)\}"\s*\)\s*private\s+String\s+([^;\s]+)',  # Spring config
                r'spring\.cloud\.stream\.bindings\.([^.]+)\.destination\s*=',  # Stream binding
                r'@TopicConfig\s*\(\s*name\s*=\s*"([^"]+)"'  # Topic config
            }
        )
        
    def can_analyze(self, file_path: Path) -> bool:
        """Check if file is a Java source file."""
        return file_path.suffix.lower() == '.java'
        
    def _extract_topic_vars(self, content: str) -> Dict[str, str]:
        """Extract topic variables and constants from file content."""
        topic_vars = {}
        for pattern in self.patterns.topic_configs:
            matches = re.finditer(pattern, content)
            for match in matches:
                if len(match.groups()) == 2:
                    var_name, topic_name = match.groups()
                    topic_vars[var_name] = topic_name
        return topic_vars
        
    def analyze_service(self, service: Service) -> Dict[str, KafkaTopic]:
        """Analyze a service for Kafka usage.
        
        Args:
            service: Service to analyze
            
        Returns:
            Dict[str, KafkaTopic]: Dictionary of topics found
        """
        # Make sure we're working with an absolute path
        base_path = service.root_path.resolve()
        
        # Find all Java files
        java_files = list(base_path.rglob('*.java'))
        logger.debug(f"Found {len(java_files)} Java files in {base_path}")
        
        for file_path in java_files:
            # Skip actual test files but not test data files
            if ('src/test' not in str(file_path) and 
                'tests/test_data' in str(file_path) or
                'src/test' not in str(file_path) and
                'tests/test' not in str(file_path)):
                try:
                    self.analyze(file_path, service)
                except Exception as e:
                    logger.error(f"Error analyzing {file_path}: {str(e)}")
                    
        return service.topics

    def analyze(self, file_path: Path, service: Service) -> Optional[Dict[str, KafkaTopic]]:
        """Analyze Java file for Kafka patterns.
        
        Args:
            file_path: Path to Java file
            service: Service to analyze
            
        Returns:
            Dict[str, KafkaTopic]: Dictionary of topics found
        """
        content = file_path.read_text()
        
        # First pass: collect topic variables/constants
        topic_vars = self._extract_topic_vars(content)
        
        # Track found topics
        topics: Dict[str, KafkaTopic] = {}

        # Analyze producers
        for pattern in self.patterns.producers:
            for match in re.finditer(pattern, content):
                topic_name = match.group(1)
                # Check if it's a variable reference
                if topic_name in topic_vars:
                    topic_name = topic_vars[topic_name]
                    
                if topic_name not in topics:
                    topics[topic_name] = KafkaTopic(topic_name, set(), set())
                
                location = {
                    'file': str(file_path.relative_to(service.root_path)),
                    'line': len(content[:match.start()].splitlines()) + 1,
                    'column': match.start(1) - len(content[:match.start()].splitlines()[-1])
                }
                topics[topic_name].producers.add(service.name)
                topics[topic_name].add_producer_location(service.name, location)

        # Analyze consumers
        for pattern in self.patterns.consumers:
            for match in re.finditer(pattern, content):
                topic_name = match.group(1)
                if topic_name in topic_vars:
                    topic_name = topic_vars[topic_name]
                    
                if topic_name not in topics:
                    topics[topic_name] = KafkaTopic(topic_name, set(), set())
                
                location = {
                    'file': str(file_path.relative_to(service.root_path)),
                    'line': len(content[:match.start()].splitlines()) + 1,
                    'column': match.start(1) - len(content[:match.start()].splitlines()[-1])
                }
                topics[topic_name].consumers.add(service.name)
                topics[topic_name].add_consumer_location(service.name, location)

        return topics if topics else None