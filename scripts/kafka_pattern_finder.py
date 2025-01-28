import re
from typing import Set

class KafkaPatternFinder:
    def __init__(self):
        # Common Kafka producer patterns across languages
        self.producer_patterns = [
            # Java patterns
            r'@KafkaProducer\s*\(\s*topics\s*=\s*[\"\']([^\"\']+)',
            r'\.send\s*\(\s*[\"\']([^\"\']+)',
            # Python patterns
            r'KafkaProducer\s*\([^)]*\)\.send\s*\(\s*[\"\']([^\"\']+)',
            # Node.js patterns
            r'kafka\.producer\s*\([^)]*\)\.send\s*\(\s*[\"\']([^\"\']+)',
            # Spring patterns
            r'@SendTo\s*\(\s*[\"\']([^\"\']+)'
        ]

        # Common Kafka consumer patterns
        self.consumer_patterns = [
            # Java patterns
            r'@KafkaListener\s*\(\s*topics\s*=\s*[\"\']([^\"\']+)',
            # Python patterns
            r'KafkaConsumer\s*\([^)]*[\"\']([^\"\']+)[\"\']',
            # Node.js patterns
            r'kafka\.consumer\s*\([^)]*[\"\']([^\"\']+)[\"\']',
            # Spring patterns
            r'@KafkaHandler\s*\([^)]*[\"\']([^\"\']+)[\"\']'
        ]

    def find_producers(self, content: str) -> Set[str]:
        """Find all Kafka producer topics in the given content."""
        topics = set()
        for pattern in self.producer_patterns:
            matches = re.finditer(pattern, content)
            topics.update(match.group(1) for match in matches)
        return topics

    def find_consumers(self, content: str) -> Set[str]:
        """Find all Kafka consumer topics in the given content."""
        topics = set()
        for pattern in self.consumer_patterns:
            matches = re.finditer(pattern, content)
            topics.update(match.group(1) for match in matches)
        return topics