"""Analyzer for service dependencies based on Kafka topics and schemas."""
from typing import Dict, Set, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import networkx as nx

from ..models.service import Service, ServiceCollection
from ..models.schema import Schema, AvroSchema

@dataclass
class DependencyEdge:
    """Represents a dependency between services."""
    source: str
    target: str
    topics: Set[str]
    schemas: Set[str]
    message_types: Set[str]

class DependencyAnalyzer:
    """Analyzer for finding dependencies between services."""
    
    def __init__(self):
        """Initialize dependency analyzer."""
        self.graph = nx.DiGraph()
        self.edge_data: Dict[Tuple[str, str], DependencyEdge] = {}
        
    def analyze_services(self, services: ServiceCollection) -> None:
        """Analyze dependencies between services.
        
        Args:
            services: Collection of services to analyze
        """
        self._analyze_topic_dependencies(services)
        self._analyze_schema_dependencies(services)
        self._detect_cycles()
        
    def _analyze_topic_dependencies(self, services: ServiceCollection) -> None:
        """Find dependencies based on shared Kafka topics."""
        for producer_name, producer in services.services.items():
            for topic in producer.topics.values():
                if producer_name in topic.producers:
                    # Find consumers of this topic
                    for consumer_name, consumer in services.services.items():
                        if consumer_name in topic.consumers:
                            self._add_dependency(
                                producer_name,
                                consumer_name,
                                topic.name,
                                None
                            )
                            
    def _analyze_schema_dependencies(self, services: ServiceCollection) -> None:
        """Find dependencies based on shared schemas."""
        # Build schema to service mapping
        schema_producers: Dict[str, Set[str]] = {}
        schema_consumers: Dict[str, Set[str]] = {}
        
        for service_name, service in services.services.items():
            for schema in service.schemas.values():
                schema_key = f"{schema.namespace}.{schema.name}" if hasattr(schema, 'namespace') else schema.name
                
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
                            self._add_dependency(
                                producer,
                                consumer,
                                None,
                                schema_key
                            )
                            
    def _add_dependency(
        self,
        source: str,
        target: str,
        topic: Optional[str] = None,
        schema: Optional[str] = None
    ) -> None:
        """Add or update a dependency between services."""
        edge_key = (source, target)
        
        if edge_key not in self.edge_data:
            self.edge_data[edge_key] = DependencyEdge(
                source=source,
                target=target,
                topics=set(),
                schemas=set(),
                message_types=set()
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
        
        Args:
            service_name: Name of the service
            
        Returns:
            Set of service names that depend on this service
        """
        if service_name not in self.graph:
            return set()
        return set(self.graph.predecessors(service_name))
        
    def get_dependency_details(
        self,
        source: str,
        target: str
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
        
        Returns:
            Set of service names that are considered critical
        """
        in_degree = dict(self.graph.in_degree())
        out_degree = dict(self.graph.out_degree())
        
        critical = set()
        for service in self.graph.nodes():
            # Consider a service critical if it has many dependents
            # or is part of a dependency cycle
            if in_degree.get(service, 0) >= 3 or out_degree.get(service, 0) >= 3:
                critical.add(service)
        
        return critical