"""Manager class to coordinate different analyzers."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.schema import AvroSchema, KafkaTopic
from ..models.service import Service
from ..models.service_collection import ServiceCollection
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
        services = ServiceCollection()
        discovered_services = self.service_analyzer.find_services(source_dir)
        self.logger.debug(f"Initially discovered {len(discovered_services)} services")

        # Process each discovered service
        for service_name, service in discovered_services.items():
            self.logger.debug(
                f"Adding service: {service_name} at path {service.root_path}"
            )
            services.add_service(service)

        self.logger.info(
            f"Completed service discovery. Found {len(services.services)} services"
        )
        return services

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
                    for topic_name, topic in topics.items():
                        if topic_name not in all_topics:
                            self.logger.debug(f"New topic found: {topic_name}")
                            all_topics[topic_name] = topic
                        else:
                            existing_topic = all_topics[topic_name]
                            # Merge producers
                            for producer in topic.producers:
                                existing_topic.producers.add(producer)
                                if producer in topic.producer_locations:
                                    existing_topic.producer_locations.setdefault(
                                        producer, []
                                    ).extend(topic.producer_locations[producer])
                            # Merge consumers
                            for consumer in topic.consumers:
                                existing_topic.consumers.add(consumer)
                                if consumer in topic.consumer_locations:
                                    existing_topic.consumer_locations.setdefault(
                                        consumer, []
                                    ).extend(topic.consumer_locations[consumer])
            except Exception as e:
                self.logger.warning(
                    f"Error in analyzer {analyzer.__class__.__name__} for file {file_path}: {e}"
                )

        return all_topics if all_topics else None

    def generate_output(
        self, services: ServiceCollection, verbose: bool = False
    ) -> Dict[str, Any]:
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
                                consumer: sorted(
                                    [
                                        {"file": str(loc["file"]), "line": loc["line"]}
                                        for loc in locs
                                    ]
                                )
                                for consumer, locs in topic.consumer_locations.items()
                            },
                        }
                        for topic_name, topic in svc.topics.items()
                    },
                    "schemas": {
                        schema_name: {
                            "type": "avro" if isinstance(schema, AvroSchema) else "dto",
                            "namespace": getattr(schema, "namespace", ""),
                            "fields": (
                                [
                                    {
                                        "name": field["name"],
                                        "type": field["type"],
                                        "doc": field.get("doc", ""),
                                    }
                                    for field in schema.fields
                                ]
                                if hasattr(schema, "fields")
                                else []
                            ),
                        }
                        for schema_name, schema in svc.schemas.items()
                    },
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
        result = self.generate_output(services, verbose=verbose)

        # Handle encoding of Path objects and sets
        def json_encoder(obj):
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, set):
                return sorted(list(obj))
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
