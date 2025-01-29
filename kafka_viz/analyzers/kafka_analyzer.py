"""Kafka pattern analyzer for different programming languages."""
import re
from pathlib import Path
from typing import Dict, Set, Optional, Tuple
from dataclasses import dataclass, field

from .base import BaseAnalyzer, KafkaPatterns
from ..models.service import Service
from ..models.schema import KafkaTopic

class KafkaAnalyzer(BaseAnalyzer):
    """Analyzes source code for Kafka patterns."""

    def __init__(self):
        """Initialize with language-specific patterns."""
        super().__init__()
        self.language_patterns = {
            'java': LanguagePatterns.JAVA,
            'kt': LanguagePatterns.JAVA,  # Kotlin uses same patterns
            'scala': LanguagePatterns.JAVA,  # Scala uses similar patterns
            'py': LanguagePatterns.PYTHON,
            'cs': LanguagePatterns.CSHARP
        }

    def can_analyze(self, file_path: Path) -> bool:
        """Determine if a file should be analyzed."""
        # Only analyze source code files
        return file_path.suffix.lstrip('.') in self.language_patterns

    def get_patterns(self) -> KafkaPatterns:
        """Get patterns for the current file language."""
        # Get language from file extension if available
        if hasattr(self, 'current_file') and self.current_file:
            lang = self.current_file.suffix.lstrip('.')
            if lang in self.language_patterns:
                return self.language_patterns[lang]
        # Return Java patterns as default
        return LanguagePatterns.JAVA

    def _analyze_content(
        self, 
        content: str, 
        file_path: Path,
        service: Service
    ) -> Optional[Dict[str, KafkaTopic]]:
        """Analyze file content for Kafka patterns."""
        # Store current file for pattern selection
        self.current_file = file_path
        return super()._analyze_content(content, file_path, service)

class LanguagePatterns:
    """Kafka patterns for different programming languages."""
    
    JAVA = KafkaPatterns(
        producers={
            # Kafka Producer annotation with both single and double quotes
            r'@KafkaProducer\s*\(\s*topics\s*=\s*["\']([^"\']+)["\']',
            # Spring SendTo annotation
            r'@SendTo\s*\(\s*["\']([^"\']+)["\']',
            # Direct producer send method
            r'\.send\s*\(\s*["\']([^"\']+)["\']',
            # Kafka ProducerRecord constructor
            r'ProducerRecord\s*<[^>]*>\s*\(\s*["\']([^"\']+)["\']'
        },
        consumers={
            # Kafka Listener annotation
            r'@KafkaListener\s*\(\s*topics\s*=\s*["\']([^"\']+)["\']',
            # Kafka Handler annotation
            r'@KafkaHandler\s*\([^)]*["\']([^"\']+)["\']',
            # ConsumerRecord pattern with capture group for topic
            r'ConsumerRecord\s*<[^>]*>\s*\(\s*["\']([^"\']+)["\']'
        }
    )
    
    PYTHON = KafkaPatterns(
        producers={
            r'KafkaProducer\s*\([^)]*\)\.send\s*\(\s*[\"\']([^\"\']+)',
            r'producer\.send\s*\(\s*[\"\']([^\"\']+)'
        },
        consumers={
            r'KafkaConsumer\s*\([^)]*[\"\']([^\"\']+)',
            r'consumer\.subscribe\s*\(\s*\[[\"\']([^\"\']+)'
        }
    )
    
    CSHARP = KafkaPatterns(
        producers={
            r'\.Produce\s*\(\s*[\"\']([^\"\']+)',
            r'ProducerBuilder\s*<[^>]*>\s*\.\s*SetTopic\s*\(\s*[\"\']([^\"\']+)',
            r'\.ProduceAsync\s*\(\s*[\"\']([^\"\']+)'
        },
        consumers={
            r'\.Subscribe\s*\(\s*[\"\']([^\"\']+)',
            r'ConsumerBuilder\s*<[^>]*>\s*\.\s*Subscribe\s*\(\s*[\"\']([^\"\']+)'
        }
    )