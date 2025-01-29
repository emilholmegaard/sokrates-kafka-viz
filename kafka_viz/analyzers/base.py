from pathlib import Path
from typing import Dict, Optional, Pattern, Set
import re

from ..models.service import Service
from ..models.schema import KafkaTopic

class KafkaPatterns:
    """Container for Kafka-related regex patterns."""
    def __init__(
        self,
        producers: Set[str] = None,
        consumers: Set[str] = None,
        topic_configs: Set[str] = None,
        ignore_patterns: Set[str] = None,
        custom_patterns: Dict[str, Set[str]] = None
    ):
        self.producers = producers or set()
        self.consumers = consumers or set()
        self.topic_configs = topic_configs or set()
        self.ignore_patterns = ignore_patterns or set()
        self.custom_patterns = custom_patterns or {}
        
        # Compile patterns for efficiency
        self._compiled_producers = {re.compile(p) for p in self.producers}
        self._compiled_consumers = {re.compile(p) for p in self.consumers}
        self._compiled_configs = {re.compile(p) for p in self.topic_configs}
        self._compiled_ignore = {re.compile(p) for p in self.ignore_patterns}
        
    def should_ignore(self, content: str) -> bool:
        """Check if content matches any ignore patterns."""
        return any(p.search(content) for p in self._compiled_ignore)

class BaseAnalyzer:
    """Base class for Kafka topic analyzers."""
    
    def get_patterns(self) -> KafkaPatterns:
        """Get the patterns to use for analysis.
        
        Returns:
            KafkaPatterns: The patterns to use
        """
        raise NotImplementedError()
        
    def can_analyze(self, file_path: Path) -> bool:
        """Check if this analyzer can handle the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if this analyzer can handle the file
        """
        raise NotImplementedError()
        
    def analyze(self, file_path: Path, service: Service) -> Dict[str, KafkaTopic]:
        """Analyze a file for Kafka topic usage.
        
        Args:
            file_path: Path to file to analyze
            service: Service the file belongs to
            
        Returns:
            Dict[str, KafkaTopic]: Dictionary of topics found
        """
        if not self.can_analyze(file_path):
            return {}
            
        try:
            with open(file_path) as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            return {}
            
        return self._analyze_content(content, file_path, service)
        
    def _analyze_content(
        self,
        content: str,
        file_path: Path,
        service: Service
    ) -> Dict[str, KafkaTopic]:
        """Analyze file content for Kafka topics.
        
        Args:
            content: File content to analyze
            file_path: Path to the file (for error reporting)
            service: Service the file belongs to
            
        Returns:
            Dict[str, KafkaTopic]: Dictionary of topics found
        """
        patterns = self.get_patterns()
        if patterns.should_ignore(content):
            return {}
            
        topics: Dict[str, KafkaTopic] = {}
        
        # Find producer patterns
        for pattern in patterns._compiled_producers:
            for match in pattern.finditer(content):
                topic_name = match.group(1)
                if topic_name not in topics:
                    topics[topic_name] = KafkaTopic(topic_name)
                topics[topic_name].producers.add(service.name)
                
        # Find consumer patterns
        for pattern in patterns._compiled_consumers:
            for match in pattern.finditer(content):
                topic_name = match.group(1)
                if topic_name not in topics:
                    topics[topic_name] = KafkaTopic(topic_name)
                topics[topic_name].consumers.add(service.name)
                
        # Find topic configurations
        for pattern in patterns._compiled_configs:
            for match in pattern.finditer(content):
                topic_name = match.group(1)
                if topic_name not in topics:
                    topics[topic_name] = KafkaTopic(topic_name)
                    
        return topics