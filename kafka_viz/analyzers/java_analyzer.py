"""Java-specific Kafka pattern analyzer."""
import re
from pathlib import Path
from typing import Dict, Optional, Set
import logging

from kafka_viz.models import Service, KafkaTopic
from .base import BaseAnalyzer, KafkaPatterns

logger = logging.getLogger(__name__)

class JavaKafkaAnalyzer(BaseAnalyzer):
    """Analyzer for Java-specific Kafka patterns."""

    def __init__(self):
        super().__init__()
        # Define regex patterns for Java Kafka usage
        self.patterns = KafkaPatterns(
            producers={
                # Plain Kafka patterns
                r'new\s+ProducerRecord\s*<[^>]*>\s*\(\s*"([^"]+)"',  # ProducerRecord with literal
                r'new\s+ProducerRecord\s*<[^>]*>\s*\(\s*([A-Z_]+)',  # ProducerRecord with constant
                r'\.send\s*\(\s*"([^"]+)"',  # Direct send with literal
                r'\.send\s*\(\s*([A-Z_]+)',  # Direct send with constant
                r'producer\.send\s*\(\s*([A-Z_]+)',  # Producer send with constant
                
                # Spring patterns
                r'@SendTo\s*\(\s*"([^"]+)"\s*\)',  # Spring Cloud Stream SendTo
                r'@Output\s*\(\s*"([^"]+)"\s*\)',  # Spring Cloud Stream output
            },
            consumers={
                # Plain Kafka patterns
                r'\.subscribe\s*\(\s*(?:Arrays\.asList|List\.of)\s*\(\s*"([^"]+)"\s*\)',  # Subscribe with literal
                r'\.subscribe\s*\(\s*(?:Arrays\.asList|List\.of)\s*\(\s*([A-Z_]+)\s*\)',  # Subscribe with constant
                r'@KafkaListener\s*\(\s*topics\s*=\s*"([^"]+)"\s*\)',  # Single topic literal
                r'@KafkaListener\s*\(\s*topics\s*=\s*([A-Z_]+)\s*\)',  # Single topic constant
                r'@KafkaListener\s*\(\s*topics\s*=\s*\{\s*"([^"]+)"(?:\s*,\s*"[^"]+")*\s*\}\s*\)',  # Array topics literals
                r'@KafkaListener\s*\(\s*topics\s*=\s*\{\s*([A-Z_]+)(?:\s*,\s*[A-Z_]+)*\s*\}\s*\)',  # Array topics constants
                
                # Spring patterns
                r'@StreamListener\s*\(\s*"([^"]+)"\s*\)',  # StreamListener
                r'@Input\s*\(\s*"([^"]+)"\s*\)'  # Spring Cloud Stream input
            },
            topic_configs={
                # Topic configuration patterns
                r'(?:private|public|static)\s+(?:final\s+)?String\s+([A-Z_]+)\s*=\s*"([^"]+)"',  # Constants
                r'@Value\s*\(\s*"\$\{([^}]+\.topic)\}"\s*\)\s*private\s+String\s+([^;\s]+)',  # Spring config
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
                groups = match.groups()
                if len(groups) == 2:  # For constant declarations
                    var_name, topic_name = groups
                    topic_vars[var_name] = topic_name
                elif len(groups) == 1:  # For Spring config
                    # Extract the last part as the variable name
                    parts = groups[0].split('.')
                    if len(parts) > 1:
                        topic_vars[parts[-2]] = parts[-2]  # For bindings.<name>.topic
                    else:
                        topic_vars[groups[0]] = groups[0]  # For direct topic names
        return topic_vars
        
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
        logger.debug(f"Found topic variables: {topic_vars}")
        
        # Track found topics
        topics: Dict[str, KafkaTopic] = {}

        # Helper function to process matches
        def process_match(match, is_producer: bool):
            topic_name = match.group(1)
            # Check if it's a variable reference
            if topic_name in topic_vars:
                topic_name = topic_vars[topic_name]
                
            if topic_name not in topics:
                topics[topic_name] = KafkaTopic(topic_name)
            
            location = {
                'file': str(file_path.relative_to(service.root_path)),
                'line': len(content[:match.start()].splitlines()) + 1,
                'column': match.start(1) - len(content[:match.start()].splitlines()[-1])
            }

            if is_producer:
                topics[topic_name].producers.add(service.name)
                topics[topic_name].add_producer_location(service.name, location)
            else:
                topics[topic_name].consumers.add(service.name)
                topics[topic_name].add_consumer_location(service.name, location)

        # Analyze producers
        for pattern in self.patterns.producers:
            for match in re.finditer(pattern, content):
                process_match(match, True)

        # Analyze consumers
        for pattern in self.patterns.consumers:
            for match in re.finditer(pattern, content):
                process_match(match, False)

        # Process multi-topic KafkaListener arrays
        multi_topic_pattern = r'@KafkaListener\s*\(\s*topics\s*=\s*\{\s*"([^"]+)"(?:\s*,\s*"([^"]+)")?\s*\}\s*\)'
        for match in re.finditer(multi_topic_pattern, content):
            for group in match.groups():
                if group:  # Skip None groups
                    if group not in topics:
                        topics[group] = KafkaTopic(group)
                    topics[group].consumers.add(service.name)
                    location = {
                        'file': str(file_path.relative_to(service.root_path)),
                        'line': len(content[:match.start()].splitlines()) + 1,
                        'column': match.start(1) - len(content[:match.start()].splitlines()[-1])
                    }
                    topics[group].add_consumer_location(service.name, location)

        logger.debug(f"Found topics: {topics}")
        return topics if topics else None