"""Spring Cloud Stream and Web specific analyzer."""

import re
from pathlib import Path
from typing import Any, Dict

from ..models.schema import KafkaTopic
from ..models.service import Service
from .analyzer import Analyzer, KafkaPatterns


class SpringCloudStreamAnalyzer(Analyzer):
    """Spring Cloud Stream and Web specific analyzer that works alongside the main Kafka analyzer."""

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
                r'Consumer<[^>]+>\s+\w+\s*\(\s*\)\s*{',
                r'Function<[^>]+>\s+\w+\s*\(\s*\)\s*{'
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
                r'Supplier<[^>]+>\s+\w+\s*\(\s*\)\s*{'
            },
            ignore_patterns={
                r'@SpringBootTest',
                r'@TestConfiguration',
                r'@MockBean',
                r'@TestComponent'
            }
        )
        
        # Add REST endpoint detection
        self.rest_patterns = {
            r'@RestController',
            r'@Controller',
            r'@RequestMapping\s*\(\s*["\']([^"\']+)["\']\)',
            r'@GetMapping\s*\(\s*["\']([^"\']+)["\']\)',
            r'@PostMapping\s*\(\s*["\']([^"\']+)["\']\)',
            r'@PutMapping\s*\(\s*["\']([^"\']+)["\']\)',
            r'@DeleteMapping\s*\(\s*["\']([^"\']+)["\']\)',
            r'@PatchMapping\s*\(\s*["\']([^"\']+)["\']\)'
        }

    def can_analyze(self, file_path: Path) -> bool:
        """Check if file is a Spring Cloud Stream source file, config, or REST controller."""
        if not file_path.suffix.lower() == '.java':
            return False
            
        try:
            content = file_path.read_text()
            
            # Check for Spring Boot application class
            if '@SpringBootApplication' in content:
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

    def analyze(self, file_path: Path, service: Service) -> Dict[str, KafkaTopic]:
        """Analyze a file for Spring Cloud Stream and REST endpoints.
        
        Args:
            file_path: Path to the file to analyze
            service: Service the file belongs to
            
        Returns:
            Dict[str, KafkaTopic]: Dictionary of topics found
        """
        if not self.can_analyze(file_path):
            return {}

        try:
            content = file_path.read_text()
        except Exception:
            return {}

        topics: Dict[str, KafkaTopic] = {}

        # Find topics for each pattern type using base class implementation
        base_topics = super()._analyze_content(content, file_path, service)
        topics.update(base_topics)

        # Additional Spring-specific analysis can be added here
        # For example, analyzing application.properties/yaml for stream bindings
        config_files = [
            file_path.parent / "application.properties",
            file_path.parent / "application.yml",
            file_path.parent / "application.yaml"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    config_content = config_file.read_text()
                    # Look for Spring Cloud Stream bindings
                    binding_pattern = re.compile(
                        r'spring\.cloud\.stream\.bindings\.([^.]+)\.(destination|topic)\s*=\s*([^\s]+)'
                    )
                    for match in binding_pattern.finditer(config_content):
                        binding_name = match.group(1)
                        topic_name = match.group(3).strip('"\'')
                        
                        if topic_name not in topics:
                            topics[topic_name] = KafkaTopic(topic_name)
                            
                        # Check if it's an input or output binding
                        if '.input.' in binding_name.lower():
                            topics[topic_name].consumers.add(service.name)
                        elif '.output.' in binding_name.lower():
                            topics[topic_name].producers.add(service.name)
                except Exception:
                    continue

        return topics

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information specific to Spring Cloud Stream analysis."""
        base_info = super().get_debug_info()
        base_info.update(
            {
                "patterns": {
                    "consumers": list(self.patterns.consumers),
                    "producers": list(self.patterns.producers),
                    "ignore_patterns": list(self.patterns.ignore_patterns),
                    "rest_patterns": list(self.rest_patterns)
                }
            }
        )
        return base_info
