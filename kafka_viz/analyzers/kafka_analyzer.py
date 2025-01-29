import re
from pathlib import Path
from typing import Dict

from kafka_viz.models import Service, KafkaTopic
from .base import BaseAnalyzer, KafkaPatterns

class KafkaAnalyzer(BaseAnalyzer):
    """Analyzer for finding Kafka usage patterns in code."""

    def __init__(self):
        super().__init__()
        self.patterns = KafkaPatterns(
            producers={
                # Template based patterns
                r'kafkaTemplate\.send\s*\(\s*["\']([^"\']+)["\']',
                # Annotation based patterns
                r'@SendTo\s*\(\s*["\']([^"\']+)["\']'
            },
            consumers={
                r'@KafkaListener\s*\(\s*topics\s*=\s*["\']([^"\']+)["\']'
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
        for file_path in service.root_path.rglob('*.java'):
            if file_path.is_file():
                result = self.analyze(file_path, service)
                
        return service.topics