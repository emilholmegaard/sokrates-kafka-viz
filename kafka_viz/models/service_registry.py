"""Service Registry for centralized service management."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .schema import KafkaTopic
from .service import Service
from .service_collection import ServiceCollection

logger = logging.getLogger(__name__)


@dataclass
class ServiceRelationship:
    """Represents a relationship between two services."""

    source: str
    target: str
    type: str  # e.g., "kafka", "rest", "dependency"
    details: Optional[Dict] = None


@dataclass
class AnalysisResult:
    """Container for analysis results from analyzers."""

    affected_service: str
    topics: Dict[str, KafkaTopic] = field(default_factory=dict)
    discovered_services: Dict[str, Service] = field(default_factory=dict)
    service_relationships: List[ServiceRelationship] = field(default_factory=list)

    def add_relationship(
        self,
        source: str,
        target: str,
        type_: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Helper method to add a relationship."""
        relationship = ServiceRelationship(source, target, type_, details)
        self.service_relationships.append(relationship)


class ServiceRegistry:
    """Centralized registry for managing services and their relationships."""

    def __init__(self) -> None:
        self.services: Dict[str, Service] = {}
        self.relationships: List[ServiceRelationship] = []
        self.topics: Dict[str, KafkaTopic] = {}
        self.logger: logging.Logger = logging.getLogger(__name__)

    def register_service(self, service: Service) -> None:
        """Register a new service or update existing one."""
        self.services[service.name] = service

    def get_or_create_service(
        self, name: str, root_path: Optional[Path] = None
    ) -> Service:
        """Get an existing service or create a new one."""
        if name not in self.services:
            self.logger.debug(f"Creating new service: {name}")
            service = Service(name=name, root_path=root_path or Path())
            self.services[name] = service
        return self.services[name]

    def add_relationship(
        self,
        source: str,
        target: str,
        type_: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a relationship between services."""
        relationship = ServiceRelationship(source, target, type_, details)
        self.relationships.append(relationship)
        self.logger.debug(f"Added {type_} relationship: {source} -> {target}")

    def get_relationships(
        self, service_name: Optional[str] = None
    ) -> List[ServiceRelationship]:
        """Get all relationships or filter by service name."""
        if service_name is None:
            return self.relationships
        return [
            r
            for r in self.relationships
            if r.source == service_name or r.target == service_name
        ]

    def apply_analysis_result(self, result: AnalysisResult) -> None:
        """Apply analysis results to the registry."""
        # Register discovered services
        for service in result.discovered_services.values():
            self.register_service(service)

        # Add relationships
        for relationship in result.service_relationships:
            self.add_relationship(
                relationship.source, relationship.target, relationship.type
            )

        # Merge topics
        for topic_name, topic in result.topics.items():
            if topic_name not in self.topics:
                self.topics[topic_name] = topic
            else:
                self.topics[topic_name].producers.update(topic.producers)
                self.topics[topic_name].consumers.update(topic.consumers)

    def to_service_collection(self) -> ServiceCollection:
        """Convert registry to ServiceCollection for backwards compatibility."""
        collection = ServiceCollection()
        for service in self.services.values():
            collection.add_service(service)
        return collection

    def get_service_dependencies(self, service_name: str) -> Set[str]:
        """Get all services that the given service depends on."""
        return {r.target for r in self.relationships if r.source == service_name}

    def get_service_dependents(self, service_name: str) -> Set[str]:
        """Get all services that depend on the given service."""
        return {r.source for r in self.relationships if r.target == service_name}

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the registry."""
        return {
            "num_services": len(self.services),
            "num_relationships": len(self.relationships),
            "relationship_types": list(set(r.type for r in self.relationships)),
        }
