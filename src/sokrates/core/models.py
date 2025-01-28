"""Core domain models for the Sokrates Kafka Visualization tool."""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from pathlib import Path

@dataclass
class KafkaTopic:
    """Represents a Kafka topic and its configuration."""
    name: str
    partitions: Optional[int] = None
    replication_factor: Optional[int] = None
    config: Dict[str, str] = field(default_factory=dict)

@dataclass
class MessageSchema:
    """Represents a message schema (Avro, Protobuf, or DTO)."""
    name: str
    schema_type: str  # 'AVRO', 'PROTOBUF', 'DTO'
    fields: Dict[str, str]
    source_file: Path
    format: Optional[str] = None  # For DTOs: 'JSON', 'XML', etc.

@dataclass
class Service:
    """Represents a microservice in the system."""
    name: str
    path: Path
    language: str
    produced_topics: Set[str] = field(default_factory=set)
    consumed_topics: Set[str] = field(default_factory=set)
    schemas: Dict[str, MessageSchema] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)

@dataclass
class AnalysisResult:
    """Represents the complete analysis of the microservices system."""
    services: Dict[str, Service]
    topics: Dict[str, KafkaTopic]
    schemas: Dict[str, MessageSchema]
    stats: Dict[str, any]
    
    def to_dict(self) -> Dict:
        """Convert the analysis result to a dictionary for serialization."""
        return {
            'services': {
                name: {
                    'name': svc.name,
                    'path': str(svc.path),
                    'language': svc.language,
                    'produced_topics': list(svc.produced_topics),
                    'consumed_topics': list(svc.consumed_topics),
                    'schemas': {k: v.__dict__ for k, v in svc.schemas.items()},
                    'dependencies': list(svc.dependencies)
                } for name, svc in self.services.items()
            },
            'topics': {name: topic.__dict__ for name, topic in self.topics.items()},
            'schemas': {name: schema.__dict__ for name, schema in self.schemas.items()},
            'stats': self.stats
        }

@dataclass
class AnalysisOptions:
    """Configuration options for the analysis process."""
    include_test_code: bool = False
    analyze_dtos: bool = True
    analyze_schemas: bool = True
    excluded_paths: Set[str] = field(default_factory=lambda: {
        'node_modules', 'venv', '.git', 'test', 'tests', 
        '.idea', 'target', 'build', 'dist', '__pycache__'
    })
    included_languages: Set[str] = field(default_factory=lambda: {
        'Java', 'Kotlin', 'Python', 'C#', 'JavaScript', 'TypeScript'
    })