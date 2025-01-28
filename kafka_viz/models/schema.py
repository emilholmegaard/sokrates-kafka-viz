"""Schema models for data contracts."""
from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path

@dataclass
class Schema:
    """Base class for all schemas (Avro, DTO, etc.)."""
    name: str
    file_path: Path
    fields: Dict[str, str] = field(default_factory=dict)

@dataclass
class AvroSchema(Schema):
    """Represents an Avro schema."""
    namespace: str = ""
    type_name: str = "record"

@dataclass
class DTOSchema(Schema):
    """Represents a DTO class."""
    language: str
    serialization_format: Optional[str] = None  # 'JSON', 'XML', etc.
    service_name: Optional[str] = None

@dataclass
class KafkaTopic:
    """Represents a Kafka topic."""
    name: str
    producers: set[str] = field(default_factory=set)
    consumers: set[str] = field(default_factory=set)
    schema: Optional[Schema] = None