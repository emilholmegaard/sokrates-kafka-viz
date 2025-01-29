"""Service model representing a microservice in the system."""
from dataclasses import dataclass, field
from typing import Dict, Set, Optional
from pathlib import Path
from .schema import Schema, KafkaTopic

@dataclass
class Service:
    """Represents a microservice in the system."""
    name: str
    root_path: Path
    language: str
    build_file: Optional[Path] = None
    topics: Dict[str, KafkaTopic] = field(default_factory=dict)
    schemas: Dict[str, Schema] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    source_files: Set[Path] = field(default_factory=set)

    @property
    def produced_topics(self) -> Set[str]:
        """Get all topics this service produces to."""
        return {name for name, topic in self.topics.items() 
                if self.name in topic.producers}

    @property
    def consumed_topics(self) -> Set[str]:
        """Get all topics this service consumes from."""
        return {name for name, topic in self.topics.items() 
                if self.name in topic.consumers}

@dataclass
class ServiceCollection:
    """Collection of services with their relationships."""
    services: Dict[str, Service] = field(default_factory=dict)
    
    def add_service(self, service: Service) -> None:
        """Add a service to the collection."""
        self.services[service.name] = service
    
    def get_service_dependencies(self, service_name: str) -> Set[str]:
        """Get all services that this service depends on through Kafka."""
        if service_name not in self.services:
            return set()
            
        service = self.services[service_name]
        dependencies = set()
        
        # Find services that produce to topics this service consumes from
        for topic_name in service.consumed_topics:
            for other_service in self.services.values():
                if topic_name in other_service.produced_topics:
                    dependencies.add(other_service.name)
        
        return dependencies
    
    def get_service_dependents(self, service_name: str) -> Set[str]:
        """Get all services that depend on this service through Kafka."""
        if service_name not in self.services:
            return set()
            
        service = self.services[service_name]
        dependents = set()
        
        # Find services that consume from topics this service produces to
        for topic_name in service.produced_topics:
            for other_service in self.services.values():
                if topic_name in other_service.consumed_topics:
                    dependents.add(other_service.name)
        
        return dependents