"""Manager class to coordinate different analyzers."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.schema import AvroSchema, KafkaTopic
from ..models.service import Service
from ..models.service_collection import ServiceCollection
from ..models.service_registry import ServiceRegistry
from .avro_analyzer import AvroAnalyzer
from .dependency_analyzer import DependencyAnalyzer
from .java_analyzer import JavaAnalyzer
from .kafka_analyzer import KafkaAnalyzer
from .service_analyzer import ServiceAnalyzer
from .spring_analyzer import SpringCloudStreamAnalyzer


class AnalyzerManager:
    """Manages and coordinates different analyzers."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        # Define analyzer order based on dependencies
        self.service_analyzer = ServiceAnalyzer()  # Must run first to discover services
        self.schema_analyzer = AvroAnalyzer()  # Should run before Kafka analysis

        # File-level analyzers
        self.file_analyzers = [
            JavaAnalyzer(),
            KafkaAnalyzer(),
            SpringCloudStreamAnalyzer(),
        ]

        # Service-level analyzers that work on the entire service collection
        self.service_level_analyzers = [
            DependencyAnalyzer(),
        ]

    def discover_services(self, source_dir: Path) -> ServiceCollection:
        """First pass: Discover all services in the source directory."""
        self.logger.info(f"Starting service discovery in {source_dir}")
        analysis_result = self.service_analyzer.find_services(source_dir)
        self.logger.debug(
            f"Initially discovered {len(analysis_result.discovered_services)} services"
        )

        # Process each discovered service
        for service_name, service in analysis_result.discovered_services.items():
            self.logger.debug(
                f"Adding service: {service_name} at path {service.root_path}"
            )
            self.service_registry.register_service(service)

        # Register relationships found during discovery
        for relationship in analysis_result.service_relationships:
            self.service_registry.add_relationship(
                relationship.source,
                relationship.target,
                relationship.type,
                relationship.details,
            )
            # Create a new service entry with proper metadata
            new_service = Service(service.root_path, service.name, service.language)
            new_service.pom_path = (
                service.pom_path if hasattr(service, "pom_path") else None
            )
            new_service.package_json_path = (
                service.package_json_path
                if hasattr(service, "package_json_path")
                else None
            )
            self.service_registry.add_service(new_service)

        self.logger.info(
            f"Completed service discovery. Found {len(services.services)} services"
        )

        # Convert registry to ServiceCollection for backward compatibility
        return self.service_registry.to_service_collection()

    def analyze_schemas(self, service: Service) -> None:
        """Second pass: Analyze schemas for a service."""
        self.logger.debug(f"Analyzing schemas for service at {service.root_path}")
        try:
            schemas = self.schema_analyzer.analyze_directory(service.root_path)
            if schemas:
                self.logger.debug(
                    f"Found {len(schemas)} schemas for service at {service.root_path}"
                )
                for schema_name in schemas:
                    self.logger.debug(f"Found schema: {schema_name}")
                service.schemas.update(schemas)
        except Exception as e:
            self.logger.warning(f"Error analyzing schemas for {service.name}: {e}")

    def analyze_file(
        self, file_path: Path, service: Service
    ) -> Optional[Dict[str, KafkaTopic]]:
        """Analyze a file using all available file-level analyzers."""
        self.logger.debug(f"Analyzing file: {file_path}")
        all_topics = {}

        for analyzer in self.file_analyzers:
            try:
                topics = analyzer.analyze(file_path, service)
                if topics:
                    self.logger.debug(
                        f"Analyzer {analyzer.__class__.__name__} found "
                        f"{len(topics)} topics in {file_path}"
                    )
                    for topic_name, topic in result.topics.items():
                        if topic_name not in all_topics:
                            self.logger.debug(f"New topic found: {topic_name}")
                            all_topics[topic_name] = topic
                        else:
                            existing_topic = all_topics[topic_name]
                            # Merge producers
                            for producer in topic.producers:
                                if producer not in existing_topic.producers:
                                    existing_topic.producers.add(producer)
                                    existing_topic.producer_locations.update(
                                        topic.producer_locations
                                    )
                            # Merge consumers
                            for consumer in topic.consumers:
                                if consumer not in existing_topic.consumers:
                                    existing_topic.consumers.add(consumer)
                                    existing_topic.consumer_locations.update(
                                        topic.consumer_locations
                                    )
            except Exception as e:
                self.logger.warning(
                    f"Error in analyzer {analyzer.__class__.__name__} for file {file_path}: {e}"
                )

        return all_topics if all_topics else None

    def analyze_service_dependencies(self) -> None:
        """Run all service-level analyzers on the service collection."""
        self.logger.info("Starting service dependency analysis")
        # Convert registry to collection for backward compatibility with existing analyzers
        services = self.service_registry.to_service_collection()

        for analyzer in self.service_level_analyzers:
            try:
                self.logger.debug(
                    f"Running service-level analyzer: {analyzer.__class__.__name__}"
                )
                analyzer.analyze_services(services)
                # After analysis, update the registry with any new relationships found
                for service_name, service in services.services.items():
                    if service.dependencies:
                        for dep in service.dependencies:
                            self.service_registry.add_relationship(
                                source=service_name, target=dep, type_="dependency"
                            )
            except Exception as e:
                self.logger.error(
                    f"Error in service-level analyzer {analyzer.__class__.__name__}: {e}"
                )

    def generate_output(self, include_debug: bool = False) -> Dict[str, Any]:
        """Generate JSON-compatible output dictionary."""
        self.logger.info("Generating output")
        self.logger.debug(f"Processing {len(services.services)} services for output")

        result: Dict[str, Any] = {
            "services": {
                name: {
                    "path": str(svc.root_path),
                    "language": svc.language,
                    "topics": {
                        topic_name: {
                            "producers": sorted(list(topic.producers)),
                            "consumers": sorted(list(topic.consumers)),
                            "producer_locations": {
                                producer: sorted(
                                    [
                                        {"file": str(loc["file"]), "line": loc["line"]}
                                        for loc in locs
                                    ]
                                )
                                for producer, locs in topic.producer_locations.items()
                            },
                            "consumer_locations": {
                                consumer: locations
                                for consumer, locations in topic.consumer_locations.items()
                            },
                        }
                        for topic_name, topic in svc.topics.items()
                    },
                    "schemas": {
                        schema.name: {
                            "type": (
                                "avro"
                                if schema.__class__.__name__ == "AvroSchema"
                                else "dto"
                            ),
                            "namespace": getattr(schema, "namespace", ""),
                            "fields": schema.fields,
                        }
                        for schema in svc.schemas.values()
                    },
                    "relationships": [
                        {"target": rel.target, "type": rel.type, "details": rel.details}
                        for rel in self.service_registry.get_relationships(name)
                    ],
                }
                for name, svc in services.services.items()
            }
        }

        self.logger.debug(f"Output contains {len(result['services'])} services")
        for service_name, service_data in result["services"].items():
            self.logger.debug(
                f"Service {service_name}: {len(service_data['topics'])} topics, "
                f"{len(service_data['schemas'])} schemas"
            )

        # Add debug info if requested
        if verbose:
            result["debug_info"] = self.get_debug_info()
            self.logger.debug("Added debug information to output")

        return result

    def save_output(
        self,
        services: ServiceCollection,
        output_path: Path,
        verbose: bool = False,
    ) -> None:
        """Generate and save analysis results to a JSON file."""
        self.logger.info(f"Saving analysis results to {output_path}")
        result = self.generate_output(self.service_registry.services, include_debug)

        # Handle encoding of Path objects and sets
        def json_encoder(obj):
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, set):
                return list(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, default=json_encoder)
        self.logger.info("Successfully saved analysis results")

    def get_debug_info(self) -> List[Dict[str, Any]]:
        """Get debug information from all analyzers."""
        self.logger.debug("Collecting debug information from all analyzers")
        all_analyzers = (
            [self.service_analyzer, self.schema_analyzer]
            + self.file_analyzers
            + self.service_level_analyzers
        )
        return [analyzer.get_debug_info() for analyzer in all_analyzers]
