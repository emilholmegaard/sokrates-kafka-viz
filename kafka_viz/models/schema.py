"""Schema models for data contracts."""
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, List
from pathlib import Path

@dataclass
class KafkaTopic:
    """Represents a Kafka topic."""
    name: str
    producers: Set[str] = field(default_factory=set)
    consumers: Set[str] = field(default_factory=set)
    producer_locations: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)
    consumer_locations: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)

    def add_producer_location(self, service_name: str, location: Dict[str, object]):
        """Add a producer location for a service."""
        if service_name not in self.producer_locations:
            self.producer_locations[service_name] = []
        self.producer_locations[service_name].append(location)

    def add_consumer_location(self, service_name: str, location: Dict[str, object]):
        """Add a consumer location for a service."""
        if service_name not in self.consumer_locations:
            self.consumer_locations[service_name] = []
        self.consumer_locations[service_name].append(location)

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
    serialization_format: Optional[str] = None  # 'JSON', 'XML', etc.
    service_name: Optional[str] = None
    language: str = ""