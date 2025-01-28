"""Analyzer for Spring Cloud Stream applications."""
from pathlib import Path
from typing import Dict, Optional

from ..base import BaseAnalyzer, KafkaPatterns
from ...models.service import Service
from ...models.schema import KafkaTopic

class SpringCloudStreamAnalyzer(BaseAnalyzer):
    """Analyzer for Spring Cloud Stream applications using various binding types."""

    PATTERNS = KafkaPatterns(
        producers={
            # Functional style bindings
            r'@Bean\s+public\s+Function\s*<[^>]+>\s+\w+\s*\([^)]*\)',
            r'@Bean\s+public\s+Supplier\s*<[^>]+>\s+\w+\s*\([^)]*\)',
            # Annotation-based bindings
            r'@Output\s*\(\s*[\"\']([^\"\']+)',
            r'@StreamEmitter\s*\(\s*[\"\']([^\"\']+)',
            # Interface-based bindings
            r'interface\s+\w+Source\s*{[^}]*@Output\s*\(\s*[\"\']([^\"\']+)',
            # Direct binder usage
            r'StreamsBuilder\s*\(\s*\)\s*\.stream\s*\(\s*[\"\']([^\"\']+)',
        },
        consumers={
            # Functional style bindings
            r'@Bean\s+public\s+Consumer\s*<[^>]+>\s+\w+\s*\([^)]*\)',
            # Annotation-based bindings
            r'@Input\s*\(\s*[\"\']([^\"\']+)',
            r'@StreamListener\s*\(\s*[\"\']([^\"\']+)',
            # Interface-based bindings
            r'interface\s+\w+Sink\s*{[^}]*@Input\s*\(\s*[\"\']([^\"\']+)',
            # Direct binder usage
            r'\.to\s*\(\s*[\"\']([^\"\']+)\s*\)',
        },
        topic_configs={
            # Application properties
            r'spring\.cloud\.stream\.bindings\.([^.]+)\.destination\s*=\s*([^\n]+)',
            # YAML configurations
            r'destination:\s*[\"\']([^\"\']+)',
            # Function bindings
            r'--spring\.cloud\.function\.definition=([^\s]+)',
        },
        # Patterns to ignore (e.g., test files)
        ignore_patterns={
            r'@SpringBootTest',
            r'@TestConfiguration',
        },
        # Custom patterns for specific cases
        custom_patterns={
            'dead_letter': {
                r'\.deadLetterChannel\s*\(\s*[\"\']([^\"\']+)',
                r'spring\.cloud\.stream\.kafka\.bindings\.[^.]+\.consumer\.enableDlq\s*=\s*true'
            },
            'retry_topic': {
                r'spring\.cloud\.stream\.kafka\.bindings\.[^.]+\.consumer\.retry-topic\s*=\s*[\"\']([^\"\']+)'
            }
        }
    )

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

    def get_patterns(self) -> KafkaPatterns:
        """Get Spring Cloud Stream specific patterns."""
        return self.PATTERNS

    def _analyze_content(
        self, 
        content: str, 
        file_path: Path,
        service: Service
    ) -> Optional[Dict[str, KafkaTopic]]:
        """Enhanced analysis for Spring Cloud Stream applications."""
        topics = super()._analyze_content(content, file_path, service)
        if not topics:
            topics = {}

        # Look for function definitions that might indicate Kafka usage
        function_pattern = r'@Bean\s+public\s+Function\s*<([^>]+)>\s+(\w+)'
        for match in re.finditer(function_pattern, content):
            type_info = match.group(1)
            function_name = match.group(2)
            
            # Check if the function processes messages
            if 'Message<' in type_info or 'KStream<' in type_info:
                # Use function name as topic name with lower confidence
                if function_name not in topics:
                    topics[function_name] = KafkaTopic(name=function_name)
                    self.matches.append(KafkaPatternMatch(
                        topic_name=function_name,
                        file_path=file_path,
                        line_number=content.count('\n', 0, match.start()) + 1,
                        context=match.group(0),
                        pattern_type='function',
                        confidence=0.7  # Lower confidence for inferred topics
                    ))

        return topics if topics else None