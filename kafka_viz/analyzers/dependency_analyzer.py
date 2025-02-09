"""Analyzer for service dependencies based on Kafka topics and schemas."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from ..models.schema import KafkaTopic
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
        """Analyze dependencies between services."""
        print("\nStarting service analysis...")

        # First ensure all services are nodes in the graph
        for service_name in services.services:
            self.graph.add_node(service_name)
            print(f"Added node: {service_name}")

        self._analyze_topic_dependencies(services)
        self._analyze_schema_dependencies(services)
        self._cycles = self._detect_cycles()

        print("\nFinal graph state:")
        print(f"Nodes: {list(self.graph.nodes())}")
        print(f"Edges: {list(self.graph.edges())}")
        print(f"Cycles: {self._cycles}")

    def _analyze_topic_dependencies(self, services: ServiceCollection) -> None:
        """Find dependencies based on shared Kafka topics."""
        print("\nAnalyzing topic dependencies...")

        # First consolidate topic information across services
        topic_info: Dict[str, KafkaTopic] = {}

        # First pass: collect all topic information
        for service in services.services.values():
            for topic in service.topics.values():
                if topic.name not in topic_info:
                    topic_info[topic.name] = KafkaTopic(topic.name)
                # Merge producers and consumers
                topic_info[topic.name].producers.update(topic.producers)
                topic_info[topic.name].consumers.update(topic.consumers)

        print("\nConsolidated topic information:")
        for topic_name, topic in topic_info.items():
            print(f"Topic {topic_name}:")
            print(f"  Producers: {topic.producers}")
            print(f"  Consumers: {topic.consumers}")

        # Second pass: create dependencies based on consolidated topic information
        for topic in topic_info.values():
            for producer in topic.producers:
                for consumer in topic.consumers:
                    if producer != consumer:  # Don't create self-dependencies
                        print(
                            f"Adding dependency: {producer} -> {consumer} via topic {topic.name}"
                        )
                        self._add_dependency(producer, consumer, topic.name, None)

    def _analyze_schema_dependencies(self, services: ServiceCollection) -> None:
        """Find dependencies based on shared schemas."""
        # Skip schema analysis for now as we're focusing on topic dependencies
        pass

    def _add_dependency(
        self,
        source: str,
        target: str,
        topic: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> None:
        """Add or update a dependency between services."""
        print(f"\nAdding dependency: {source} -> {target}")
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
            print(f"Added new edge: {source} -> {target}")
        else:
            print(f"Updated existing edge: {source} -> {target}")

        edge = self.edge_data[edge_key]
        if topic:
            edge.topics.add(topic)
        if schema:
            edge.schemas.add(schema)

    def _detect_cycles(self) -> List[List[str]]:
        """Detect cycles in the dependency graph."""
        print("\nDetecting cycles...")
        cycles = list(nx.simple_cycles(self.graph))
        for cycle in cycles:
            print(f"Warning: Dependency cycle detected: {' -> '.join(cycle)}")
        return cycles

    def get_dependencies(self, service_name: str) -> Set[str]:
        """Get all services that this service depends on."""
        print(f"\nGetting dependencies for {service_name}")
        if service_name not in self.graph:
            print(f"Service {service_name} not in graph")
            return set()
        deps = set(self.graph.successors(service_name))
        print(f"Dependencies found: {deps}")
        return deps

    def get_dependents(self, service_name: str) -> Set[str]:
        """Get all services that depend on this service."""
        if service_name not in self.graph:
            return set()
        return set(self.graph.predecessors(service_name))

    def get_dependency_details(
        self, source: str, target: str
    ) -> Optional[DependencyEdge]:
        """Get detailed information about a dependency."""
        return self.edge_data.get((source, target))

    def get_critical_services(self) -> Set[str]:
        """Get services that are critical based on dependency analysis."""
        critical = set()

        # Check for high in/out degree (threshold is 2)
        for service in self.graph.nodes():
            if (
                self.graph.in_degree(service) >= 2
                or self.graph.out_degree(service) >= 2
            ):
                critical.add(service)

        # Add services in cycles
        for cycle in self._cycles:
            critical.update(cycle)

        return critical

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the dependency analysis."""
        base_info = super().get_debug_info()
        base_info.update(
            {
                "nodes": list(self.graph.nodes()),
                "edges": list(self.graph.edges()),
                "cycles": self._cycles,
                "critical_services": list(self.get_critical_services()),
            }
        )
        return base_info
