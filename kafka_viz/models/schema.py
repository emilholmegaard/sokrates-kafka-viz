"""Schema models for data contracts."""
from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from pathlib import Path

@dataclass
class KafkaTopic:
    """Represents a Kafka topic."""
    name: str
    producers: Set[str] = field(default_factory=set)
    consumers: Set[str] = field(default_factory=set)

@dataclass
class SchemaBase:
    """Base class for schema properties."""
    name: str
    file_path: Path

@dataclass
class Schema(SchemaBase):
    """Schema with fields."""
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