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
        self, source: str, target: str, type_: str, details: Optional[Dict] = None
    ) -> None:
        """Helper method to add a relationship."""
        relationship = ServiceRelationship(source, target, type_, details)
        self.service_relationships.append(relationship)


class ServiceRegistry:
    """Centralized registry for managing services and their relationships."""

    def __init__(self):
        self._services: Dict[str, Service] = {}
        self._relationships: List[ServiceRelationship] = []
        self.logger = logging.getLogger(__name__)

    @property
    def services(self) -> Dict[str, Service]:
        """Get all registered services."""
        return self._services

    def register_service(self, service: Service) -> None:
        """Register a new service or update existing one."""
        if service.name in self._services:
            self.logger.debug(f"Updating existing service: {service.name}")
            # Merge the service data rather than overwriting
            existing = self._services[service.name]
            existing.topics.update(service.topics)
            existing.schemas.update(service.schemas)
            existing.root_path = service.root_path
            existing.language = service.language
        else:
            self.logger.debug(f"Registering new service: {service.name}")
            self._services[service.name] = service

    def get_or_create_service(
        self, name: str, root_path: Optional[Path] = None
    ) -> Service:
        """Get an existing service or create a new one."""
        if name not in self._services:
            self.logger.debug(f"Creating new service: {name}")
            service = Service(name=name, root_path=root_path or Path())
            self._services[name] = service
        return self._services[name]

    def add_relationship(
        self, source: str, target: str, type_: str, details: Optional[Dict] = None
    ) -> None:
        """Add a relationship between services."""
        relationship = ServiceRelationship(source, target, type_, details)
        if not any(
            r.source == source and r.target == target and r.type == type_
            for r in self._relationships
        ):
            self._relationships.append(relationship)
            self.logger.debug(f"Added {type_} relationship: {source} -> {target}")

    def get_relationships(self, service_name: str = None) -> List[ServiceRelationship]:
        """Get all relationships or filter by service name."""
        if service_name is None:
            return self._relationships
        return [
            r
            for r in self._relationships
            if r.source == service_name or r.target == service_name
        ]

    def apply_analysis_result(self, result: "AnalysisResult") -> None:
        """Apply analysis results to the registry."""
        # Update or create the affected service
        service = self.get_or_create_service(result.affected_service)

        # Update topics
        for topic_name, topic in result.topics.items():
            if topic_name in service.topics:
                # Merge producers and consumers
                service.topics[topic_name].producers.update(topic.producers)
                service.topics[topic_name].consumers.update(topic.consumers)
            else:
                service.topics[topic_name] = topic

        # Register discovered services
        for svc_name, svc in result.discovered_services.items():
            if svc_name != result.affected_service:  # Don't register self as discovered
                self.register_service(svc)

        # Add relationships
        for rel in result.service_relationships:
            self.add_relationship(rel.source, rel.target, rel.type, rel.details)

    def to_service_collection(self) -> ServiceCollection:
        """Convert registry to ServiceCollection for backwards compatibility."""
        collection = ServiceCollection()
        for service in self._services.values():
            collection.add_service(service)
        return collection

    def get_service_dependencies(self, service_name: str) -> Set[str]:
        """Get all services that the given service depends on."""
        return {r.target for r in self._relationships if r.source == service_name}

    def get_service_dependents(self, service_name: str) -> Set[str]:
        """Get all services that depend on the given service."""
        return {r.source for r in self._relationships if r.target == service_name}

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the registry."""
        return {
            "num_services": len(self._services),
            "num_relationships": len(self._relationships),
            "relationship_types": list(set(r.type for r in self._relationships)),
        }
