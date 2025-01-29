import re
from pathlib import Path

from kafka_viz.models import Service, KafkaTopic

class KafkaAnalyzer:
    def __init__(self):
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
        
    def analyze_service(self, service: Service) -> None:
        """Analyze a service for Kafka usage.
        
        Args:
            service: Service to analyze
        """
        for file_path in service.root_path.rglob('*'):
            if self._is_source_file(file_path):
                self._analyze_file(service, file_path)
                
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
        with open(file_path) as f:
            content = f.read()
            
        patterns = self.topic_patterns.get(service.language, [])
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