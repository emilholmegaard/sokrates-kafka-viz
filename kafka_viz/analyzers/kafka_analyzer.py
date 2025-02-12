"""Kafka-specific patterns and topic analysis."""

import logging
import re
import yaml
from pathlib import Path
from typing import Dict, Optional, Set

from ..models.schema import KafkaTopic
from ..models.service import Service
from ..models.service_registry import AnalysisResult
from .analyzer import Analyzer, KafkaPatterns

logger = logging.getLogger(__name__)


class KafkaAnalyzer(Analyzer):
    """Analyzer for Kafka-specific patterns."""

    def __init__(self):
        super().__init__()
        self.patterns = KafkaPatterns(
            producers={
                # Basic Kafka patterns
                r'producer\.send\(\s*["\']([^"\']+)["\']\s*\)',
                r'producer\.beginTransaction\(\s*["\']([^"\']+)["\']\s*\)',
                r'@SendTo\(\s*["\']([^"\']+)["\']\s*\)',
                r'ProducerRecord\(\s*["\']([^"\']+)["\']\s*\)',
                # Configuration patterns
                r'kafka\.topic\s*=\s*["\']([^"\']+)["\']\s*',
                r'spring\.cloud\.stream\.bindings\.output\.destination\s*=\s*["\']([^"\']+)["\']\s*',
            },
            consumers={
                # Basic Kafka patterns
                r'consumer\.subscribe\(\s*["\']([^"\']+)["\']\s*\)',
                r'@KafkaListener\(\s*topics\s*=\s*["\']([^"\']+)["\']\s*\)',
                r'ConsumerRecord\<[^>]+\>\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[^;]+;',
                # Configuration patterns
                r'spring\.cloud\.stream\.bindings\.input\.destination\s*=\s*["\']([^"\']+)["\']\s*',
            },
            topic_configs={
                # Topic configuration patterns - both literal and property references
                r'admin\.createTopics\(\s*["\']([^"\']+)["\']\s*\)',
                r'@Topic\(\s*["\']([^"\']+)["\']\s*\)',
                r'@StreamListener\(\s*["\']([^"\']+)["\']\s*\)',
                r'\$\{([^}]+\.topic[^}]*)\}',  # Match property references
                r'\$\{([^}]+\.destination[^}]*)\}',  # Match destination properties
                r'\#\{([^}]+)\}',  # Match SpEL expressions
            },
            ignore_patterns={
                r'@TestConfiguration',
                r'@SpringBootTest',
                r'@Test',
            },
        )
        self._properties_cache: Dict[Path, Dict] = {}  # Cache for resolved properties

    def can_analyze(self, file_path: Path) -> bool:
        """Check if file can be analyzed for Kafka patterns."""
        return any(
            file_path.suffix.lower() == ext
            for ext in [".java", ".kt", ".py", ".js", ".ts", ".properties", ".yml", ".yaml"]
        )

    def analyze(self, file_path: Path, service: Service) -> AnalysisResult:
        """Analyze a file for Kafka topic usage.

        Args:
            file_path: Path to file to analyze
            service: Service the file belongs to

        Returns:
            AnalysisResult containing found topics and relationships
        """
        result = AnalysisResult(affected_service=service.name)
        
        if not self.can_analyze(file_path):
            logger.debug(f"Skipping {file_path} - not supported by analyzer")
            return result

        try:
            # Load properties first
            properties = self._load_properties(service.root_path)
            content = file_path.read_text()
            
            # Handle property references in the content
            content = self._resolve_properties(content, properties)
            
            # Get topics from base analyzer with resolved content
            topics = super()._analyze_content(content, file_path, service)
            
            if topics:
                # Filter out invalid topic names
                valid_topics = {
                    name: topic for name, topic in topics.items()
                    if self._is_valid_topic_name(name)
                }
                
                if valid_topics:
                    result.topics.update(valid_topics)
                    logger.debug(f"Found topics in {file_path}: {list(valid_topics.keys())}")

                    # Add relationships for topics
                    for topic_name, topic in valid_topics.items():
                        self._add_topic_relationships(topic, result)

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {str(e)}")

        return result

    def _is_valid_topic_name(self, name: str) -> bool:
        """Check if a topic name is valid."""
        # Filter out unresolved properties and invalid characters
        if '${' in name or '#{' in name or not name.strip():
            return False
        # Basic topic name validation (alphanumeric, dots, hyphens, underscores)
        return bool(re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$', name))

    def _load_properties(self, root_path: Path) -> Dict:
        """Load properties from application.yml/properties files."""
        if root_path in self._properties_cache:
            return self._properties_cache[root_path]

        properties = {}
        config_files = [
            root_path / 'src/main/resources/application.yml',
            root_path / 'src/main/resources/application.yaml',
            root_path / 'src/main/resources/application.properties',
            root_path / 'src/main/resources/application-local.yml',
            root_path / 'src/main/resources/application-local.yaml',
            root_path / 'src/main/resources/application-local.properties',
        ]

        for config_file in config_files:
            if not config_file.exists():
                continue

            try:
                if config_file.suffix in ['.yml', '.yaml']:
                    with open(config_file) as f:
                        yaml_props = yaml.safe_load(f) or {}
                        self._flatten_dict(yaml_props, properties)
                else:
                    with open(config_file) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                key, _, value = line.partition('=')
                                properties[key.strip()] = value.strip()
            except Exception as e:
                logger.warning(f"Error loading properties from {config_file}: {e}")

        self._properties_cache[root_path] = properties
        return properties

    def _flatten_dict(self, yaml_dict: Dict, output: Dict, prefix: str = '') -> None:
        """Flatten nested YAML dictionary into dot notation."""
        for key, value in yaml_dict.items():
            new_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, dict):
                self._flatten_dict(value, output, f"{new_key}.")
            else:
                output[new_key] = str(value)

    def _resolve_properties(self, content: str, properties: Dict) -> str:
        """Resolve property references in content."""
        # Resolve ${property} references
        def property_replacer(match):
            prop_name = match.group(1).strip()
            return properties.get(prop_name, match.group(0))

        content = re.sub(r'\$\{([^}]+)\}', property_replacer, content)

        # Resolve #{SpEL} expressions - currently just remove them
        content = re.sub(r'#\{[^}]+\}', '', content)

        return content

    def _add_topic_relationships(self, topic: KafkaTopic, result: AnalysisResult) -> None:
        """Add relationships based on topic producers and consumers."""
        # Add relationships between producers and consumers
        for producer in topic.producers:
            for consumer in topic.consumers:
                if producer != consumer:
                    result.add_relationship(
                        source=producer,
                        target=consumer,
                        type_="kafka",
                        details={"topic": topic.name}
                    )
