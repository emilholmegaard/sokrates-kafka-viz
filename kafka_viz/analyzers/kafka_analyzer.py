import re
from pathlib import Path
from typing import Dict, Optional

from kafka_viz.models import Service, KafkaTopic
from .base import BaseAnalyzer, KafkaPatterns

class KafkaAnalyzer(BaseAnalyzer):
    """Analyzer for finding Kafka usage patterns in code."""

    def __init__(self):
        super().__init__()
        self.topic_patterns = {
            'java': [
                r'@KafkaListener\(\s*topics\s*=\s*["\']([^"\']+)["\']',
                r'@SendTo\(\s*["\']([^"\']+)["\']',
                r'new\s+KafkaTemplate<>\([^)]+\).send\(\s*["\']([^"\']+)["\']'
            ],
            'python': [
                r'KafkaConsumer\([^)]*["\']([^"\']+)["\']',
                r'KafkaProducer\(\).send\(\s*["\']([^"\']+)["\']'
            ],
            'javascript': [
                r'kafka\.consumer\([^)]*["\']([^"\']+)["\']',
                r'kafka\.producer\.send\([^)]*["\']([^"\']+)["\']'
            ]
        }

    def can_analyze(self, service: Service) -> bool:
        """Check if this analyzer can handle the given service.
        
        Args:
            service: Service to check
            
        Returns:
            bool: True if this analyzer can handle the service
        """
        return service.language.lower() in self.topic_patterns
        
    def get_patterns(self, service: Service) -> KafkaPatterns:
        """Get the Kafka patterns to look for in this service.
        
        Args:
            service: Service to analyze
            
        Returns:
            KafkaPatterns: Producer and consumer patterns
        """
        if not self.can_analyze(service):
            return KafkaPatterns([], [])
            
        patterns = self.topic_patterns.get(service.language.lower(), [])
        producer_patterns = [p for p in patterns if any(x in p for x in ['send', 'SendTo', 'producer'])]
        consumer_patterns = [p for p in patterns if not any(x in p for x in ['send', 'SendTo', 'producer'])]
        
        return KafkaPatterns(producer_patterns, consumer_patterns)
        
    def analyze_service(self, service: Service) -> Dict[str, KafkaTopic]:
        """Analyze a service for Kafka usage.
        
        Args:
            service: Service to analyze
            
        Returns:
            Dict[str, KafkaTopic]: Dictionary of topics found in the service
        """
        for file_path in service.root_path.rglob('*'):
            if self._is_source_file(file_path):
                self._analyze_file(service, file_path)
        return service.topics
                
    def _is_source_file(self, file_path: Path) -> bool:
        """Check if file is a source file we should analyze."""
        extensions = {
            'java': ['.java'],
            'python': ['.py'],
            'javascript': ['.js', '.ts']
        }
        
        if not file_path.is_file():
            return False
            
        ext = file_path.suffix.lower()
        for lang_exts in extensions.values():
            if ext in lang_exts:
                return True
        return False
                
    def _analyze_file(self, service: Service, file_path: Path) -> None:
        """Analyze a single file for Kafka patterns."""
        try:
            with open(file_path) as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            return  # Skip files we can't read
            
        patterns = self.topic_patterns.get(service.language.lower(), [])
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                topic_name = match.group(1)
                if topic_name not in service.topics:
                    service.topics[topic_name] = KafkaTopic(topic_name)
                    
                # Determine if producer or consumer based on pattern
                if any(p in pattern for p in ['send', 'SendTo', 'producer']):
                    service.topics[topic_name].producers.add(service.name)
                else:
                    service.topics[topic_name].consumers.add(service.name)