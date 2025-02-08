"""Manager class to coordinate different analyzers."""
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from .service_analyzer import ServiceAnalyzer
from .java_analyzer import JavaAnalyzer
from .kafka_analyzer import KafkaAnalyzer
from .dependency_analyzer import DependencyAnalyzer
from .avro_analyzer import AvroAnalyzer
from .spring_analyzer import SpringCloudStreamAnalyzer
from ..models.service import Service
from ..models.schema import KafkaTopic
from ..models.service_collection import ServiceCollection

class AnalyzerManager:
    """Manages and coordinates different analyzers."""

    def __init__(self):
        # Define analyzer order based on dependencies
        self.service_analyzer = ServiceAnalyzer()  # Must run first to discover services
        self.schema_analyzer = AvroAnalyzer()      # Should run before Kafka analysis
        
        # Other analyzers can run in any order
        self.code_analyzers = [
            JavaAnalyzer(),
            KafkaAnalyzer(),
            DependencyAnalyzer(),
            SpringCloudStreamAnalyzer()
        ]

    def discover_services(self, source_dir: Path) -> ServiceCollection:
        """First pass: Discover all services in the source directory."""
        services = ServiceCollection()
        discovered_services = self.service_analyzer.find_services(source_dir)
        for service in discovered_services.values():
            services.add_service(service)
        return services

    def analyze_schemas(self, service: Service):
        """Second pass: Analyze schemas for a service."""
        schemas = self.schema_analyzer.analyze_directory(service.root_path)
        service.schemas.update(schemas)

    def analyze_file(self, file_path: Path, service: Service) -> Optional[Dict[str, KafkaTopic]]:
        """Analyze a file using all available code analyzers."""
        all_topics = {}

        for analyzer in self.code_analyzers:
            try:
                topics = analyzer.analyze(file_path, service)
                if topics:
                    for topic_name, topic in topics.items():
                        if topic_name not in all_topics:
                            all_topics[topic_name] = topic
                        else:
                            # Merge producers and consumers
                            all_topics[topic_name].producers.update(topic.producers)
                            all_topics[topic_name].consumers.update(topic.consumers)
            except Exception as e:
                # Log error but continue with other analyzers
                print(f"Error in analyzer {analyzer.__class__.__name__}: {e}")

        return all_topics if all_topics else None

    def generate_output(self, services: ServiceCollection, include_debug: bool = False) -> Dict[str, Any]:
        """Generate JSON-compatible output dictionary."""
        result: Dict[str, Any] = {
            "services": {
                name: {
                    "path": str(svc.root_path),
                    "language": svc.language,
                    "topics": {
                        topic.name: {
                            "producers": list(topic.producers),
                            "consumers": list(topic.consumers)
                        } for topic in svc.topics.values()
                    },
                    "schemas": {
                        schema.name: {
                            "type": "avro" if schema.__class__.__name__ == "AvroSchema" else "dto",
                            "namespace": getattr(schema, "namespace", ""),
                            "fields": schema.fields
                        } for schema in svc.schemas.values()
                    }
                } for name, svc in services.services.items()
            }
        }

        if include_debug:
            result["debug_info"] = self.get_debug_info()

        return result

    def save_output(self, services: ServiceCollection, output_path: Path, include_debug: bool = False):
        """Generate and save analysis results to a JSON file."""
        result = self.generate_output(services, include_debug)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

    def get_debug_info(self) -> List[Dict[str, Any]]:
        """Get debug information from all analyzers."""
        analyzers = [self.service_analyzer, self.schema_analyzer] + self.code_analyzers
        return [analyzer.get_debug_info() for analyzer in analyzers]