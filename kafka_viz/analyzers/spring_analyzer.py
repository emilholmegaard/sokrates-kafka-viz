"""Spring Cloud Stream and Web specific analyzer."""

import re
from pathlib import Path
from typing import Any, Dict

from ..models.schema import KafkaTopic
from ..models.service import Service
from ..models.service_registry import AnalysisResult, ServiceRelationship
from .analyzer import Analyzer, KafkaPatterns


class SpringCloudStreamAnalyzer(Analyzer):
    """Spring Cloud Stream and Web analyzer that works alongside the main Kafka analyzer."""

    def __init__(self):
        super().__init__()
        self.patterns = KafkaPatterns(
            consumers={
                # Spring Cloud Stream patterns
                r'@StreamListener\s*\(\s*["\']([^"\']+)["\']\)',
                r'@Input\s*\(\s*["\']([^"\']+)["\']\)',
                r'@ServiceActivator\s*\(\s*inputChannel\s*=\s*["\']([^"\']+)["\']\)',
                # Event bus patterns
                r'@EventListener\s*\(\s*["\']([^"\']+)["\']\)',
                r'@KafkaListener\s*\(\s*topics\s*=\s*["\']([^"\']+)["\']\)',
                r'@RabbitListener\s*\(\s*queues\s*=\s*["\']([^"\']+)["\']\)',
                # Spring Integration patterns
                r'@InboundChannelAdapter\s*\(\s*channel\s*=\s*["\']([^"\']+)["\']\)',
                # Spring Cloud Function patterns
                r"Consumer<[^>]+>\s+\w+\s*\(\s*\)\s*{",
                r"Function<[^>]+>\s+\w+\s*\(\s*\)\s*{",
            },
            producers={
                # Spring Cloud Stream patterns
                r'@Output\s*\(\s*["\']([^"\']+)["\']\)',
                r'@SendTo\s*\(\s*["\']([^"\']+)["\']\)',
                r'@ServiceActivator\s*\(\s*outputChannel\s*=\s*["\']([^"\']+)["\']\)',
                # Event bus patterns
                r'eventBus\.publish\s*\(\s*["\']([^"\']+)["\']\)',
                r'template\.convertAndSend\s*\(\s*["\']([^"\']+)["\']\)',
                # Spring Integration patterns
                r'@OutboundChannelAdapter\s*\(\s*channel\s*=\s*["\']([^"\']+)["\']\)',
                # Spring Cloud Function patterns
                r"Supplier<[^>]+>\s+\w+\s*\(\s*\)\s*{",
            },
            ignore_patterns={
                r"@SpringBootTest",
                r"@TestConfiguration",
                r"@MockBean",
                r"@TestComponent",
            },
        )

        # Add REST endpoint detection
        self.rest_patterns = {
            r"@RestController",
            r"@Controller",
            r'@RequestMapping\s*\(\s*["\']([^"\']+)["\']\)',
            r'@GetMapping\s*\(\s*["\']([^"\']+)["\']\)',
            r'@PostMapping\s*\(\s*["\']([^"\']+)["\']\)',
            r'@PutMapping\s*\(\s*["\']([^"\']+)["\']\)',
            r'@DeleteMapping\s*\(\s*["\']([^"\']+)["\']\)',
            r'@PatchMapping\s*\(\s*["\']([^"\']+)["\']\)',
        }

        # Add dependency injection patterns for service discovery
        self.service_patterns = {
            r'@Autowired\s+(?:private\s+)?(\w+)\s+\w+',
            r'@Qualifier\s*\(\s*["\']([^"\']+)["\']\)',
            r'@DependsOn\s*\(\s*["\']([^"\']+)["\']\)',
        }

    def can_analyze(self, file_path: Path) -> bool:
        """Check if file is a Spring Cloud Stream source file, config, or REST controller."""
        if not file_path.suffix.lower() == ".java":
            return False

        try:
            content = file_path.read_text()

            # Check for Spring Boot application class
            if "@SpringBootApplication" in content:
                return True

            # Check for Spring Cloud Stream or messaging annotations
            for pattern in self.patterns.consumers.union(self.patterns.producers):
                if re.search(pattern, content):
                    return True

            # Check for REST endpoints
            for pattern in self.rest_patterns:
                if re.search(pattern, content):
                    return True

            return False

        except Exception:
            return False

    def analyze(self, file_path: Path, service: Service) -> AnalysisResult:
        """Analyze a file for Spring Cloud Stream and REST endpoints.

        Args:
            file_path: Path to the file to analyze
            service: Service the file belongs to

        Returns:
            AnalysisResult: Analysis results including topics, discovered services and relationships
        """
        result = AnalysisResult(affected_service=service.name)
        
        if not self.can_analyze(file_path):
            return result

        try:
            content = file_path.read_text()
        except Exception:
            return result

        # Find topics for each pattern type using base class implementation
        topics = self._analyze_content(content, file_path, service)
        result.topics.update(topics)

        # Look for service dependencies through DI patterns
        for pattern in self.service_patterns:
            for match in re.finditer(pattern, content):
                service_name = match.group(1)
                # Convert CamelCase to kebab-case for service names
                service_name = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', service_name).lower()
                if service_name != service.name:  # Don't add self-references
                    # Add as discovered service
                    discovered_service = Service(name=service_name)
                    result.discovered_services[service_name] = discovered_service
                    # Add relationship
                    relationship = ServiceRelationship(
                        source=service.name,
                        target=service_name,
                        type_="spring-dependency",
                        details={"injection_type": "autowired"}
                    )
                    result.service_relationships.append(relationship)

        # Additional Spring-specific analysis
        config_files = [
            file_path.parent / "application.properties",
            file_path.parent / "application.yml",
            file_path.parent / "application.yaml",
        ]

        for config_file in config_files:
            if config_file.exists():
                try:
                    config_content = config_file.read_text()
                    # Look for Spring Cloud Stream bindings
                    binding_pattern = re.compile(
                        r"spring\.cloud\.stream\.bindings\.([^.]+)\."
                        r"(destination|topic)\s*=\s*([^\s]+)"
                    )
                    
                    # Look for external service configurations
                    service_pattern = re.compile(
                        r"([\w-]+)\.url\s*=\s*([^\s]+)"
                    )
                    
                    # Process stream bindings
                    for match in binding_pattern.finditer(config_content):
                        binding_name = match.group(1)
                        topic_name = match.group(3).strip('"\'')

                        topic = KafkaTopic(topic_name)
                        
                        # Check if it's an input or output binding
                        if ".input." in binding_name.lower():
                            topic.consumers.add(service.name)
                        elif ".output." in binding_name.lower():
                            topic.producers.add(service.name)
                            
                        result.topics[topic_name] = topic

                    # Process external service configurations
                    for match in service_pattern.finditer(config_content):
                        ext_service_name = match.group(1)
                        service_url = match.group(2)
                        
                        # Add external service as discovered service
                        if ext_service_name != service.name:
                            ext_service = Service(name=ext_service_name)
                            result.discovered_services[ext_service_name] = ext_service
                            
                            # Add relationship
                            relationship = ServiceRelationship(
                                source=service.name,
                                target=ext_service_name,
                                type_="rest-client",
                                details={"url": service_url}
                            )
                            result.service_relationships.append(relationship)
                            
                except Exception:
                    continue

        return result

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information specific to Spring Cloud Stream analysis."""
        base_info = super().get_debug_info()
        base_info.update(
            {
                "patterns": {
                    "consumers": list(self.patterns.consumers),
                    "producers": list(self.patterns.producers),
                    "ignore_patterns": list(self.patterns.ignore_patterns),
                    "rest_patterns": list(self.rest_patterns),
                    "service_patterns": list(self.service_patterns)
                }
            }
        )
        return base_info
