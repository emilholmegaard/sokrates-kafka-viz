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

    def analyze_service(self, service: Service) -> Dict[str, KafkaTopic]:
        """Analyze all files in a service for Kafka patterns."""
        all_topics = {}
    
        for file_path in service.source_files:
            topics = self.analyze(file_path, service)
            if topics:
                for topic_name, topic in topics.items():
                    if topic_name not in all_topics:
                        all_topics[topic_name] = topic
                    else:
                        # Merge producers and consumers
                        all_topics[topic_name].producers.update(topic.producers)
                        all_topics[topic_name].consumers.update(topic.consumers)
    
        return all_topics

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
            # Generic producer annotations (Spring, custom frameworks)
            r'@\w*Producer\s*\(\s*topics?\s*=\s*["\']([\w.-]+)["\']',
            r'@\w*Producer\s*\(\s*value\s*=\s*["\']([\w.-]+)["\']',
            r'@\w*To\s*\(\s*["\']([\w.-]+)["\']',
            r'@\w*Topic\s*\(\s*["\']([\w.-]+)["\']',
            r'@\w*Output\s*\(\s*["\']([\w.-]+)["\']',
            
            # Generic producer method/API calls
            r'\.send\s*\(\s*["\']([\w.-]+)["\']',
            r'\.produce\s*\(\s*["\']([\w.-]+)["\']',
            r'\.publish\s*\(\s*["\']([\w.-]+)["\']',
            
            # Generic message record patterns
            r'[Pp]roducer[Rr]ecord\s*[^(]*\(\s*["\']([\w.-]+)["\']',
            r'[Mm]essage[Rr]ecord\s*[^(]*\(\s*["\']([\w.-]+)["\']',
            r'[Kk]afka[Mm]essage\s*[^(]*\(\s*["\']([\w.-]+)["\']',
            
            # Configuration and template patterns
            r'\w*[Tt]emplate\s*[^.]*\.send\(\s*["\']([\w.-]+)["\']',
            r'\w*[Tt]emplate\s*[^.]*\.produce\(\s*["\']([\w.-]+)["\']',
            r'@Bean\s*\(\s*name\s*=\s*["\']([\w.-]+)[\w-]*producer["\']',
            r'\.setTopic(?:Name)?\(\s*["\']([\w.-]+)["\']',
            r'\.forTopic\(\s*["\']([\w.-]+)["\']',
            
            # Property/configuration patterns (supports various naming conventions)
            r'(?:kafka|messaging|producer|topic)\.[\w.-]*topic\s*=\s*["\']([\w.-]+)["\']',
            r'spring\.kafka\.template\.default-topic\s*=\s*["\']([\w.-]+)["\']',
            r'spring\.cloud\.stream\.bindings\.[^.]+\.destination\s*=\s*["\']([\w.-]+)["\']',
            r'spring\.cloud\.stream\.function\.bindings\.[^.]+\.destination\s*=\s*["\']([\w.-]+)["\']',
            
            # Programmatic configuration
            r'\.topics?\(\s*["\']([\w.-]+)["\']',
            r'\.setTopics?\(\s*["\']([\w.-]+)["\']'
        },
        consumers={
            # Generic consumer annotations
            r'@\w*Consumer\s*\(\s*topics?\s*=\s*["\']([\w.-]+)["\']',
            r'@\w*Consumer\s*\(\s*value\s*=\s*["\']([\w.-]+)["\']',
            r'@\w*Listener\s*\([^)]*["\']([\w.-]+)["\']',
            r'@\w*Handler\s*\([^)]*["\']([\w.-]+)["\']',
            r'@\w*Input\s*\(\s*["\']([\w.-]+)["\']',
            r'@\w*From\s*\(\s*["\']([\w.-]+)["\']',
            
            # Generic consumer API patterns
            r'\.subscribe\s*\(\s*[^)]*["\']([\w.-]+)["\']',
            r'\.consume\s*\(\s*["\']([\w.-]+)["\']',
            r'\.receive\s*\(\s*["\']([\w.-]+)["\']',
            
            # Generic message record patterns
            r'[Cc]onsumer[Rr]ecord\s*[^(]*\(\s*["\']([\w.-]+)["\']',
            r'[Mm]essage[Rr]ecord\s*[^(]*\(\s*["\']([\w.-]+)["\']',
            r'[Kk]afka[Mm]essage\s*[^(]*\(\s*["\']([\w.-]+)["\']',
            
            # Configuration patterns
            r'@Bean\s*\(\s*name\s*=\s*["\']([\w.-]+)[\w-]*consumer["\']',
            r'\w*[Cc]ontainer[Ff]actory\s*=\s*["\']([\w.-]+)["\']',
            
            # Property/configuration patterns
            r'(?:kafka|messaging|consumer|topic)\.[\w.-]*topic[s]?\s*=\s*["\']([\w.-]+)["\']',
            r'spring\.kafka\.consumer\.topics?\s*=\s*["\']([\w.-]+)["\']',
            r'spring\.kafka\.consumer\.topic-pattern\s*=\s*["\']([\w.-]+)["\']',
            r'spring\.cloud\.stream\.bindings\.[^.]+\.destination\s*=\s*["\']([\w.-]+)["\']',
            r'spring\.cloud\.stream\.function\.bindings\.[^.]+\.destination\s*=\s*["\']([\w.-]+)["\']',
            
            # Topic pattern subscriptions
            r'topic[Pp]attern\s*=\s*["\']([\w.-]+)["\']',
            r'group[Pp]attern\s*=\s*["\']([\w.-]+)["\']',
            
            # Collection subscriptions (supporting various formats)
            r'\.subscribe\(\s*Collections\.singleton(?:List|Map)?\(\s*["\']([\w.-]+)["\']',
            r'\.subscribe\(\s*Arrays\.asList\([^)]*["\']([\w.-]+)["\']',
            r'\.subscribe\(\s*Set\.of\([^)]*["\']([\w.-]+)["\']',
            r'\.subscribe\(\s*List\.of\([^)]*["\']([\w.-]+)["\']'
        }
    )
    
    PYTHON = KafkaPatterns(
        producers={
            # Generic producer patterns
            r'[Pp]roducer\s*\([^)]*\)\s*\.\s*(?:send|produce)\s*\(\s*[\"\']([\w.-]+)',
            r'\.(?:send|produce)\s*\(\s*[\"\']([\w.-]+)',
            r'topic\s*=\s*[\"\']([\w.-]+)',
            r'TOPIC\s*=\s*[\"\']([\w.-]+)',
            r'[Pp]roducer(?:Config|Settings)?\.topic\s*=\s*[\"\']([\w.-]+)'
        },
        consumers={
            # Generic consumer patterns
            r'[Cc]onsumer\s*\([^)]*[\"\']([\w.-]+)',
            r'\.subscribe\s*\(\s*(?:\[[\"\']([\w.-]+)|\{[\"\']([\w.-]+))',
            r'topic\s*=\s*[\"\']([\w.-]+)',
            r'TOPIC\s*=\s*[\"\']([\w.-]+)',
            r'[Cc]onsumer(?:Config|Settings)?\.topic\s*=\s*[\"\']([\w.-]+)',
            r'@kafka_listener\s*\(\s*topics?\s*=\s*[\"\']([\w.-]+)',
            r'@consumer\s*\(\s*[\"\']([\w.-]+)'
        }
    )
    
    CSHARP = KafkaPatterns(
        producers={
            # Generic producer patterns
            r'\.[Pp]roduce(?:Async)?\s*\(\s*[\"\']([\w.-]+)',
            r'\.[Ss]end(?:Async)?\s*\(\s*[\"\']([\w.-]+)',
            r'\.[Ss]et[Tt]opic\s*\(\s*[\"\']([\w.-]+)',
            r'[Tt]opic\s*=\s*[\"\']([\w.-]+)',
            r'\.[Ww]ithTopic\s*\(\s*[\"\']([\w.-]+)',
            r'[Pp]roducer(?:Config|Settings)?\.Topic\s*=\s*[\"\']([\w.-]+)',
            r'\[Topic\(\s*[\"\']([\w.-]+)\s*\)\]'
        },
        consumers={
            # Generic consumer patterns
            r'\.[Ss]ubscribe\s*\(\s*[\"\']([\w.-]+)',
            r'\.[Cc]onsume(?:Async)?\s*\(\s*[\"\']([\w.-]+)',
            r'\.[Ss]et[Tt]opic\s*\(\s*[\"\']([\w.-]+)',
            r'[Tt]opic\s*=\s*[\"\']([\w.-]+)',
            r'\.[Ww]ithTopic\s*\(\s*[\"\']([\w.-]+)',
            r'[Cc]onsumer(?:Config|Settings)?\.Topic\s*=\s*[\"\']([\w.-]+)',
            r'\[Topic\(\s*[\"\']([\w.-]+)\s*\)\]',
            r'@KafkaListener\s*\(\s*[\"\']([\w.-]+)'
        }
    )