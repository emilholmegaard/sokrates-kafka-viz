import re
from pathlib import Path
from typing import Dict, Set
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
                # KafkaTemplate send patterns
                r'kafkaTemplate\.send\s*\(\s*["\']([^"\']+)["\']',  # Basic send
                r'@SendTo\s*\(\s*["\']([^"\']+)["\']',             # Spring Cloud Stream
                r'@Output\s*\(\s*["\']([^"\']+)["\']',             # Spring Cloud Stream
            },
            consumers={
                # Kafka Listener patterns
                r'@KafkaListener\s*\(\s*topics\s*=\s*["\']([^"\']+)["\']',  # Single topic
                r'@KafkaListener\s*\(\s*topics\s*=\s*{\s*["\']([^"\']+)["\']',  # Array of topics
                r'@Input\s*\(\s*["\']([^"\']+)["\']',  # Spring Cloud Stream
            },
            topic_configs={
                # Configuration patterns
                r'@TopicConfig\s*\(\s*name\s*=\s*["\']([^"\']+)["\']',
                r'spring\.cloud\.stream\.bindings\.([^.]+)\.destination\s*='
            }
        )
        
    def can_analyze(self, file_path: Path) -> bool:
        """Check if file is a Java source file."""
        return file_path.suffix.lower() == '.java'
        
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