"""Base classes for Kafka pattern analysis."""
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Set, List, Any
from dataclasses import dataclass, field

from ..models.service import Service
from ..models.schema import KafkaTopic

@dataclass
class KafkaPatternMatch:
    """Represents a matched Kafka pattern in code."""
    topic_name: str
    file_path: Path
    line_number: int
    context: str
    pattern_type: str  # 'producer', 'consumer', or 'config'
    framework: Optional[str] = None
    confidence: float = 1.0  # How confident we are in this match (0.0-1.0)

@dataclass
class KafkaPatterns:
    """Patterns for detecting Kafka usage in code."""
    producers: Set[str] = field(default_factory=set)
    consumers: Set[str] = field(default_factory=set)
    topic_configs: Set[str] = field(default_factory=set)
    ignore_patterns: Set[str] = field(default_factory=set)
    custom_patterns: Dict[str, Set[str]] = field(default_factory=dict)

class BaseAnalyzer(ABC):
    """Base class for all Kafka pattern analyzers."""

    def __init__(self):
        self.debug_mode = False
        self.matches: List[KafkaPatternMatch] = []

    @abstractmethod
    def can_analyze(self, file_path: Path) -> bool:
        """Determine if this analyzer can handle the given file."""
        pass

    @abstractmethod
    def get_patterns(self) -> KafkaPatterns:
        """Get the Kafka patterns for this analyzer."""
        pass

    def analyze(self, file_path: Path, service: Service) -> Optional[Dict[str, KafkaTopic]]:
        """Analyze a file and return discovered Kafka topics."""
        if not self.can_analyze(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return self._analyze_content(content, file_path, service)
        except Exception as e:
            if self.debug_mode:
                print(f"Error analyzing {file_path}: {str(e)}")
            return None

    def _analyze_content(
        self, 
        content: str, 
        file_path: Path, 
        service: Service
    ) -> Optional[Dict[str, KafkaTopic]]:
        """Analyze file content for Kafka patterns."""
        patterns = self.get_patterns()
        topics: Dict[str, KafkaTopic] = {}

        # Check if file should be ignored
        for ignore_pattern in patterns.ignore_patterns:
            if re.search(ignore_pattern, content):
                return None

        # Helper function to process matches
        def process_matches(pattern_set: Set[str], pattern_type: str):
            for pattern in pattern_set:
                for match in re.finditer(pattern, content):
                    # Get line number and context
                    line_number = content.count('\n', 0, match.start()) + 1
                    lines = content.splitlines()
                    context_start = max(0, line_number - 2)
                    context_end = min(len(lines), line_number + 1)
                    context = '\n'.join(lines[context_start:context_end])

                    topic_name = match.group(1)
                    
                    # Store the match for debugging/analysis
                    kafka_match = KafkaPatternMatch(
                        topic_name=topic_name,
                        file_path=file_path,
                        line_number=line_number,
                        context=context,
                        pattern_type=pattern_type,
                        framework=self.__class__.__name__,
                    )
                    self.matches.append(kafka_match)

                    # Add to topics
                    if topic_name not in topics:
                        topics[topic_name] = KafkaTopic(name=topic_name)
                    
                    topic = topics[topic_name]
                    if pattern_type == 'producer':
                        topic.producers.add(service.name)
                    elif pattern_type == 'consumer':
                        topic.consumers.add(service.name)

        # Process standard patterns
        process_matches(patterns.producers, 'producer')
        process_matches(patterns.consumers, 'consumer')
        process_matches(patterns.topic_configs, 'config')

        # Process custom patterns
        for pattern_type, pattern_set in patterns.custom_patterns.items():
            process_matches(pattern_set, pattern_type)

        return topics if topics else None

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the analysis."""
        return {
            'analyzer': self.__class__.__name__,
            'matches': [
                {
                    'topic': m.topic_name,
                    'file': str(m.file_path),
                    'line': m.line_number,
                    'type': m.pattern_type,
                    'context': m.context,
                    'confidence': m.confidence
                }
                for m in self.matches
            ]
        }