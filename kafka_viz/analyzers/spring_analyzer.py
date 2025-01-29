"""Analyzer for Spring Cloud Stream applications."""
from pathlib import Path
from typing import Dict, Optional
import re

from .base import BaseAnalyzer
from ..models.service import Service
from ..models.schema import KafkaTopic

class SpringCloudStreamAnalyzer(BaseAnalyzer):
    """Analyzer for Spring Cloud Stream applications using various binding types."""

    def can_analyze(self, file_path: Path) -> bool:
        """Check if file is a Spring Cloud Stream source file or config."""
        suffix = file_path.suffix.lower()
        
        # Source files
        if suffix in {'.java', '.kt', '.groovy'}:
            return True
            
        # Configuration files
        if file_path.name.lower() in {
            'application.properties',
            'application.yml',
            'application.yaml',
            'bootstrap.properties',
            'bootstrap.yml',
            'bootstrap.yaml'
        }:
            return True
            
        return False

    def _analyze_content(
        self, 
        content: str, 
        file_path: Path,
        service: Service
    ) -> Optional[Dict[str, KafkaTopic]]:
        """Enhanced analysis for Spring Cloud Stream applications."""
        topics = {}

        # Skip test files
        if '@SpringBootTest' in content or '@TestConfiguration' in content:
            return None

        # Producer patterns
        producer_patterns = [
            # Functional style bindings
            (r'@Bean\s+public\s+Function\s*<[^>]+>\s+(\w+)\s*\([^)]*\)', 1),
            (r'@Bean\s+public\s+Supplier\s*<[^>]+>\s+(\w+)\s*\([^)]*\)', 1),
            # Annotation-based bindings
            (r'@Output\s*\(\s*[\"\']([^\"\']+)', 1),
            (r'@StreamEmitter\s*\(\s*[\"\']([^\"\']+)', 1),
            # Interface-based bindings
            (r'interface\s+\w+Source\s*{[^}]*@Output\s*\(\s*[\"\']([^\"\']+)', 1),
            # Direct binder usage
            (r'StreamsBuilder\s*\(\s*\)\s*\.stream\s*\(\s*[\"\']([^\"\']+)', 1)
        ]

        # Consumer patterns
        consumer_patterns = [
            # Functional style bindings
            (r'@Bean\s+public\s+Consumer\s*<[^>]+>\s+(\w+)\s*\([^)]*\)', 1),
            # Annotation-based bindings
            (r'@Input\s*\(\s*[\"\']([^\"\']+)', 1),
            (r'@StreamListener\s*\(\s*[\"\']([^\"\']+)', 1),
            # Interface-based bindings
            (r'interface\s+\w+Sink\s*{[^}]*@Input\s*\(\s*[\"\']([^\"\']+)', 1),
            # Direct binder usage
            (r'\.to\s*\(\s*[\"\']([^\"\']+)\s*\)', 1)
        ]

        # Configuration patterns
        config_patterns = [
            # Application properties
            (r'spring\.cloud\.stream\.bindings\.([^.]+)\.destination\s*=\s*([^\n]+)', 2),
            # YAML configurations
            (r'destination:\s*[\"\']([^\"\']+)', 1),
            # Function bindings
            (r'--spring\.cloud\.function\.definition=([^\s]+)', 1)
        ]

        # Process producer patterns
        for pattern, group in producer_patterns:
            for match in re.finditer(pattern, content):
                topic_name = match.group(group)
                if topic_name not in topics:
                    topics[topic_name] = KafkaTopic(name=topic_name)
                topics[topic_name].producers.add(service.name)

        # Process consumer patterns
        for pattern, group in consumer_patterns:
            for match in re.finditer(pattern, content):
                topic_name = match.group(group)
                if topic_name not in topics:
                    topics[topic_name] = KafkaTopic(name=topic_name)
                topics[topic_name].consumers.add(service.name)

        # Process configuration patterns
        for pattern, group in config_patterns:
            for match in re.finditer(pattern, content):
                topic_name = match.group(group).strip('" \'')
                if topic_name not in topics:
                    topics[topic_name] = KafkaTopic(name=topic_name)

        return topics if topics else None