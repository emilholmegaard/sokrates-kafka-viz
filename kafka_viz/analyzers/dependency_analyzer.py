"""Analyzer for service dependencies based on Kafka topics and schemas."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from ..models.service_collection import ServiceCollection
from .service_level_base import ServiceLevelAnalyzer


@dataclass
class DependencyEdge:
    """Represents a dependency between services."""

    source: str
    target: str
    topics: Set[str]
    schemas: Set[str]
    message_types: Set[str]


class DependencyAnalyzer(ServiceLevelAnalyzer):
    """Analyzer for finding dependencies between services."""

    def __init__(self) -> None:
        """Initialize dependency analyzer."""
        self.graph = nx.DiGraph()
        self.edge_data: Dict[Tuple[str, str], DependencyEdge] = {}
        self._cycles: List[List[str]] = []

    def analyze_services(self, services: ServiceCollection) -> None:
        """Analyze dependencies between services.

        Args:
            services: Collection of services to analyze
        """
        # First ensure all services are nodes in the graph
        for service_name in services.services:
            self.graph.add_node(service_name)

        self._analyze_topic_dependencies(services)
        self._analyze_schema_dependencies(services)
        self._cycles = self._detect_cycles()

    def _analyze_topic_dependencies(self, services: ServiceCollection) -> None:
        """Find dependencies based on shared Kafka topics.
        
        For each topic:
        - If service A produces to topic T and service B consumes from topic T
        - Then service A depends on service B (edge A -> B)
        """
        # Build a map of topic names to their consumer services
        topic_to_consumers: Dict[str, Set[str]] = {}
        
        # First pass: collect all topics and their consumers
        for service_name, service in services.services.items():
            for topic in service.topics.values():
                if topic.name not in topic_to_consumers:
                    topic_to_consumers[topic.name] = set()
                if service_name in topic.consumers:
                    topic_to_consumers[topic.name].add(service_name)
        
        # Second pass: for each producer, create dependencies to consumers
        for service_name, service in services.services.items():
            for topic in service.topics.values():
                if service_name in topic.producers:  # If this service produces the topic
                    # Find all consumers of this topic
                    for consumer in topic_to_consumers[topic.name]:
                        if consumer != service_name:  # Don't create self-dependencies
                            # Producer depends on consumer: producer -> consumer edge
                            self._add_dependency(service_name, consumer, topic.name, None)

    def _analyze_schema_dependencies(self, services: ServiceCollection) -> None:
        """Find dependencies based on shared schemas."""
        # Build schema to service mapping
        schema_producers: Dict[str, Set[str]] = {}
        schema_consumers: Dict[str, Set[str]] = {}

        for service_name, service in services.services.items():
            for schema in service.schemas.values():
                schema_key = (
                    f"{schema.namespace}.{schema.name}"
                    if hasattr(schema, "namespace")
                    else schema.name
                )

                # Check if service produces or consumes this schema
                for topic in service.topics.values():
                    if service_name in topic.producers:
                        if schema_key not in schema_producers:
                            schema_producers[schema_key] = set()
                        schema_producers[schema_key].add(service_name)

                    if service_name in topic.consumers:
                        if schema_key not in schema_consumers:
                            schema_consumers[schema_key] = set()
                        schema_consumers[schema_key].add(service_name)

        # Create dependencies based on schema usage
        for schema_key in schema_producers:
            if schema_key in schema_consumers:
                for producer in schema_producers[schema_key]:
                    for consumer in schema_consumers[schema_key]:
                        if producer != consumer:
                            # Producer depends on consumer: producer -> consumer edge
                            self._add_dependency(producer, consumer, None, schema_key)

    def _add_dependency(
        self,
        source: str,
        target: str,
        topic: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> None:
        """Add or update a dependency between services.
        
        Args:
            source: Name of the source (producer) service
            target: Name of the target (consumer) service
            topic: Optional topic name that creates this dependency
            schema: Optional schema name that creates this dependency
        """
        edge_key = (source, target)

        # Add both nodes to ensure they exist in the graph
        self.graph.add_node(source)
        self.graph.add_node(target)

        if edge_key not in self.edge_data:
            self.edge_data[edge_key] = DependencyEdge(
                source=source,
                target=target,
                topics=set(),
                schemas=set(),
                message_types=set(),
            )
            self.graph.add_edge(source, target)

        edge = self.edge_data[edge_key]
        if topic:
            edge.topics.add(topic)
        if schema:
            edge.schemas.add(schema)

    def _detect_cycles(self) -> List[List[str]]:
        """Detect cycles in the dependency graph.

        Returns:
            List of cycles found in the graph
        """
        cycles = list(nx.simple_cycles(self.graph))
        for cycle in cycles:
            print(f"Warning: Dependency cycle detected: {' -> '.join(cycle)}")
        return cycles

    def get_dependencies(self, service_name: str) -> Set[str]:
        """Get all services that this service depends on.
        
        For a service that produces messages, its dependencies are the services
        that consume those messages.

        Args:
            service_name: Name of the service

        Returns:
            Set of service names that this service depends on
        """
        if service_name not in self.graph:
            return set()
        return set(self.graph.successors(service_name))

    def get_dependents(self, service_name: str) -> Set[str]:
        """Get all services that depend on this service.
        
        For a service that consumes messages, its dependents are the services
        that produce those messages.

        Args:
            service_name: Name of the service

        Returns:
            Set of service names that depend on this service
        """
        if service_name not in self.graph:
            return set()
        return set(self.graph.predecessors(service_name))

    def get_dependency_details(
        self, source: str, target: str
    ) -> Optional[DependencyEdge]:
        """Get detailed information about a dependency.

        Args:
            source: Name of the source service
            target: Name of the target service

        Returns:
            DependencyEdge object if dependency exists, None otherwise
        """
        return self.edge_data.get((source, target))

    def get_critical_services(self) -> Set[str]:
        """Get services that are critical based on dependency analysis.

        A service is considered critical if it:
        1. Has 2 or more dependents (in_degree >= 2)
        2. Has 2 or more dependencies (out_degree >= 2)
        3. Is part of a dependency cycle

        Returns:
            Set of service names that are considered critical
        """
        critical = set()
        
        # Check for high in/out degree (threshold is 2)
        for service in self.graph.nodes():
            if (self.graph.in_degree(service) >= 2 or 
                self.graph.out_degree(service) >= 2):
                critical.add(service)
        
        # Add services in cycles
        for cycle in self._cycles:
            critical.update(cycle)
        
        return critical

    def get_debug_info(self) -> Dict[str, any]:
        """Get debug information about the dependency analysis.

        Returns:
            Dict containing debug information
        """
        base_info = super().get_debug_info()
        base_info.update({
            "nodes": list(self.graph.nodes()),
            "edges": list(self.graph.edges()),
            "cycles": self._cycles,
            "critical_services": list(self.get_critical_services()),
        })
        return base_info
