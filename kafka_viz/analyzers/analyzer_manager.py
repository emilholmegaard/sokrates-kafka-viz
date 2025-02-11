"""Manager class to coordinate different analyzers."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.schema import KafkaTopic
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
        
        for service_name, service in discovered_services.items():
            self.logger.debug(f"Adding service: {service_name} at path {service.root_path}")
            services.add_service(service)
        
        self.logger.info(f"Completed service discovery. Found {len(services.services)} services")
        return services

    def analyze_schemas(self, service: Service) -> None:
        """Second pass: Analyze schemas for a service."""
        self.logger.debug(f"Analyzing schemas for service at {service.root_path}")
        schemas = self.schema_analyzer.analyze_directory(service.root_path)
        if schemas:
            self.logger.debug(f"Found {len(schemas)} schemas for service at {service.root_path}")
            for schema_name in schemas:
                self.logger.debug(f"Found schema: {schema_name}")
        service.schemas.update(schemas)

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
                        f"Analyzer {analyzer.__class__.__name__} found {len(topics)} topics in {file_path}"
                    )
                    for topic_name, topic in topics.items():
                        if topic_name not in all_topics:
                            self.logger.debug(f"New topic found: {topic_name}")
                            all_topics[topic_name] = topic
                        else:
                            self.logger.debug(f"Merging additional info for topic: {topic_name}")
                            # Merge producers and consumers
                            all_topics[topic_name].producers.update(topic.producers)
                            all_topics[topic_name].consumers.update(topic.consumers)
            except Exception as e:
                self.logger.warning(
                    f"Error in analyzer {analyzer.__class__.__name__} for file {file_path}: {e}"
                )

        return all_topics if all_topics else None

    def analyze_service_dependencies(self, services: ServiceCollection) -> None:
        """Run all service-level analyzers on the service collection."""
        self.logger.info("Starting service dependency analysis")
        for analyzer in self.service_level_analyzers:
            try:
                self.logger.debug(f"Running service-level analyzer: {analyzer.__class__.__name__}")
                analyzer.analyze_services(services)
            except Exception as e:
                self.logger.error(
                    f"Error in service-level analyzer {analyzer.__class__.__name__}: {e}"
                )

    def generate_output(
        self, services: ServiceCollection, include_debug: bool = False
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
                        topic.name: {
                            "producers": list(topic.producers),
                            "consumers": list(topic.consumers),
                        }
                        for topic in svc.topics.values()
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

        if include_debug:
            result["debug_info"] = self.get_debug_info()
            self.logger.debug("Added debug information to output")

        return result

    def save_output(
        self,
        services: ServiceCollection,
        output_path: Path,
        include_debug: bool = False,
    ) -> None:
        """Generate and save analysis results to a JSON file."""
        self.logger.info(f"Saving analysis results to {output_path}")
        result = self.generate_output(services, include_debug)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
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
