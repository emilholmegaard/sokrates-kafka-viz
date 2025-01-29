import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class KafkaTopic:
    name: str
    type: str  # 'producer' or 'consumer'
    location: Dict[str, Any]  # file, line, column info
    pattern_type: str  # The pattern used to detect this topic

class JavaKafkaAnalyzer:
    def __init__(self):
        self.plain_patterns = {
            'producer': [
                r'new\s+ProducerRecord\s*<[^>]*>\s*\(\s*"([^"]+)"',  # Plain Kafka producer
                r'\.send\s*\(\s*"([^"]+)"',  # KafkaTemplate send
            ],
            'consumer': [
                r'\.subscribe\s*\(\s*(?:Arrays\.asList|List\.of)\s*\(\s*"([^"]+)"\s*\)',  # Plain consumer
                r'@KafkaListener\s*\(\s*topics\s*=\s*"([^"]+)"\s*\)',  # Spring Kafka listener
                r'@KafkaListener\s*\(\s*topics\s*=\s*\{\s*"([^"]+)"\s*\}\s*\)'  # Array style topics
            ]
        }
        
        self.spring_patterns = {
            'producer': [
                r'@SendTo\s*\(\s*"([^"]+)"\s*\)',  # Spring Cloud Stream SendTo
                r'@Output\s*\(\s*"([^"]+)"\s*\)',  # Spring Cloud Stream output
            ],
            'consumer': [
                r'@StreamListener\s*\(\s*"([^"]+)"\s*\)',  # Spring Cloud Stream listener
                r'@Input\s*\(\s*"([^"]+)"\s*\)'  # Spring Cloud Stream input
            ]
        }
        
        # Combined patterns for easier iteration
        self.all_patterns = {
            'producer': self.plain_patterns['producer'] + self.spring_patterns['producer'],
            'consumer': self.plain_patterns['consumer'] + self.spring_patterns['consumer']
        }
        
        # Patterns for detecting topic variables/constants
        self.topic_var_patterns = [
            r'(?:private|public|static)\s+(?:final\s+)?String\s+([A-Z_]+)\s*=\s*"([^"]+)"',  # Constants
            r'@Value\s*\(\s*"\$\{([^}]+\.topic)\}"\s*\)\s*private\s+String\s+([^;\s]+)'  # Spring configuration
        ]
    
    def analyze_file(self, file_path: str, content: str) -> List[KafkaTopic]:
        topics = []
        lines = content.split('\n')
        
        # First pass: collect topic variables/constants
        topic_vars = {}
        for i, line in enumerate(lines):
            for pattern in self.topic_var_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    if len(match.groups()) == 2:
                        var_name, topic_name = match.groups()
                        topic_vars[var_name] = topic_name
        
        # Second pass: find all Kafka topic usages
        for pattern_type, patterns in self.all_patterns.items():
            for i, line in enumerate(lines):
                for pattern in patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        topic_name = match.group(1)
                        
                        # Check if it's a variable reference
                        if topic_name in topic_vars:
                            topic_name = topic_vars[topic_name]
                        
                        topic = KafkaTopic(
                            name=topic_name,
                            type=pattern_type,
                            location={
                                'file': file_path,
                                'line': i + 1,
                                'column': match.start(1)
                            },
                            pattern_type='spring' if pattern in self.spring_patterns[pattern_type] else 'plain'
                        )
                        topics.append(topic)
        
        return topics
    
    def analyze_multi_topic_declaration(self, content: str) -> List[str]:
        """Analyzes multi-topic declarations like @KafkaListener(topics = {"topic1", "topic2"})"""
        topics = []
        pattern = r'\{\s*"([^"]+)"(?:\s*,\s*"([^"]+)")*\s*\}'
        
        matches = re.finditer(pattern, content)
        for match in matches:
            topics.extend([g for g in match.groups() if g])
        
        return topics
    
    def get_topic_dependencies(self, topics: List[KafkaTopic]) -> Dict[str, List[str]]:
        """Analyzes topic dependencies based on producer/consumer relationships"""
        dependencies = {}
        
        # Group topics by file
        topics_by_file = {}
        for topic in topics:
            file_path = topic.location['file']
            if file_path not in topics_by_file:
                topics_by_file[file_path] = []
            topics_by_file[file_path].append(topic)
        
        # Analyze dependencies
        for file_path, file_topics in topics_by_file.items():
            producers = [t.name for t in file_topics if t.type == 'producer']
            consumers = [t.name for t in file_topics if t.type == 'consumer']
            
            # A service consuming from topic A and producing to topic B creates a dependency A -> B
            if producers and consumers:
                for consumer in consumers:
                    if consumer not in dependencies:
                        dependencies[consumer] = []
                    dependencies[consumer].extend(producers)
        
        return dependencies