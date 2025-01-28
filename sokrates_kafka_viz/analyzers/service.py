"""Service analyzer for detecting microservices in a codebase."""
from typing import Dict, Set, Optional, List, Any
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import re
import logging

from ..core.analyzer import BaseAnalyzer
from ..core.config import Config
from ..core.errors import AnalyzerError
from ..models.service import Service

logger = logging.getLogger(__name__)

class ServiceAnalyzer(BaseAnalyzer):
    """Analyzer for detecting and analyzing microservices."""
    
    def __init__(self):
        """Initialize service analyzer with language-specific patterns."""
        self.build_patterns = {
            'java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
            'javascript': ['package.json'],
            'python': ['pyproject.toml', 'setup.py', 'requirements.txt'],
            'csharp': ['.csproj']
        }
        self.test_dirs = {'test', 'tests', 'src/test', 'src/tests'}
        self.services: Dict[str, Service] = {}
        
    async def analyze(self, config: Config) -> Dict[str, Any]:
        """Find all microservices in the configured source directories.
        
        Args:
            config: Analysis configuration
            
        Returns:
            Dictionary containing discovered services and analysis results
        """
        try:
            analyzer_config = config.get_analyzer_config('service')
            if not analyzer_config:
                raise AnalyzerError('Service analyzer configuration not found')
            
            # Reset services for new analysis
            self.services = {}
            
            # Get paths from config
            paths = [Path(p) for p in analyzer_config.paths]
            
            for path in paths:
                if not path.exists():
                    logger.warning(f'Path does not exist: {path}')
                    continue
                
                logger.info(f'Analyzing directory: {path}')
                found_services = self.find_services(str(path))
                self.services.update(found_services)
                
            # Run additional analysis on found services
            for service in self.services.values():
                self._analyze_service_dependencies(service)
                
            return {
                'services': self.services,
                'total_count': len(self.services),
                'by_language': self.get_services_by_language(),
                'services_with_kafka': self._find_kafka_services()
            }
            
        except Exception as e:
            raise AnalyzerError(f'Service analysis failed: {str(e)}') from e
        
    def find_services(self, source_dir: str) -> Dict[str, Service]:
        """Find all microservices in the given source directory.
        
        Args:
            source_dir: Root directory containing microservices
            
        Returns:
            Dictionary mapping service names to Service objects
        """
        root_path = Path(source_dir)
        services = {}
        
        # Walk through all directories
        for path in root_path.rglob('*'):
            # Skip test directories unless explicitly included
            if any(test_dir in str(path) for test_dir in self.test_dirs):
                continue
                
            service = self._detect_service(path)
            if service:
                services[service.name] = service
                logger.info(f'Found service: {service.name} ({service.language})')
                
        return services
        
    def _detect_service(self, path: Path) -> Optional[Service]:
        """Detect if path contains a service by looking for build files."""
        if not path.is_dir():
            return None
            
        for language, patterns in self.build_patterns.items():
            for pattern in patterns:
                build_file = path / pattern
                if build_file.exists():
                    name = self._extract_service_name(build_file, language)
                    if name:
                        return Service(
                            name=name,
                            root_path=path,
                            language=language,
                            build_file=build_file
                        )
        return None
        
    def _extract_service_name(self, build_file: Path, language: str) -> Optional[str]:
        """Extract service name from build file based on language."""
        try:
            if language == 'java':
                if build_file.name == 'pom.xml':
                    tree = ET.parse(build_file)
                    root = tree.getroot()
                    # Handle XML namespaces in pom.xml
                    ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}
                    artifact_id = root.find('.//maven:artifactId', ns)
                    return artifact_id.text if artifact_id is not None else None
                else:
                    # For Gradle, use directory name as fallback
                    return build_file.parent.name
                    
            elif language == 'javascript':
                with open(build_file) as f:
                    package_data = json.load(f)
                    return package_data.get('name')
                    
            elif language == 'python':
                if build_file.name == 'pyproject.toml':
                    import tomli
                    with open(build_file, 'rb') as f:
                        data = tomli.load(f)
                        return data.get('tool', {}).get('poetry', {}).get('name') or \
                               data.get('project', {}).get('name')
                else:
                    # For requirements.txt or setup.py, use directory name
                    return build_file.parent.name
                    
            elif language == 'csharp':
                tree = ET.parse(build_file)
                root = tree.getroot()
                assembly_name = root.find('.//AssemblyName')
                return assembly_name.text if assembly_name is not None else build_file.stem
                
        except Exception as e:
            logger.error(f"Error extracting service name from {build_file}: {e}")
            # Fallback to directory name
            return build_file.parent.name
            
        return None

    def _analyze_service_dependencies(self, service: Service) -> None:
        """Analyze service for dependencies and characteristics."""
        try:
            if service.language == 'java':
                self._analyze_java_service(service)
            elif service.language == 'javascript':
                self._analyze_node_service(service)
            elif service.language == 'python':
                self._analyze_python_service(service)
        except Exception as e:
            logger.warning(f'Error analyzing dependencies for {service.name}: {e}')

    def _analyze_java_service(self, service: Service) -> None:
        """Analyze Java-based service for dependencies."""
        # Look for Spring Cloud Stream bindings
        for java_file in service.root_path.rglob('*.java'):
            try:
                with open(java_file) as f:
                    content = f.read()
                    # Check for Spring Cloud Stream annotations
                    if '@EnableBinding' in content:
                        # Extract topics from bindings
                        # TODO: Implement topic extraction
                        logger.debug(f'Found Spring Cloud Stream bindings in {service.name}')
                        service.uses_kafka = True
            except Exception as e:
                logger.warning(f'Error analyzing Java file {java_file}: {e}')
                    
    def _analyze_node_service(self, service: Service) -> None:
        """Analyze Node.js service for dependencies."""
        package_json = service.root_path / 'package.json'
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    # Check for Kafka-related dependencies
                    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                    kafka_deps = [d for d in deps if 'kafka' in d.lower()]
                    if kafka_deps:
                        logger.debug(f'Found Kafka dependencies in {service.name}: {kafka_deps}')
                        service.uses_kafka = True
            except Exception as e:
                logger.warning(f'Error analyzing package.json {package_json}: {e}')
                    
    def _analyze_python_service(self, service: Service) -> None:
        """Analyze Python service for dependencies."""
        requirements_file = service.root_path / 'requirements.txt'
        if requirements_file.exists():
            try:
                with open(requirements_file) as f:
                    content = f.read()
                    if 'kafka' in content.lower():
                        logger.debug(f'Found Kafka dependencies in {service.name}')
                        service.uses_kafka = True
            except Exception as e:
                logger.warning(f'Error analyzing requirements.txt {requirements_file}: {e}')
                    
    def get_service_by_name(self, service_name: str) -> Optional[Service]:
        """Get a service by its name."""
        return self.services.get(service_name)

    def get_services_by_language(self, language: Optional[str] = None) -> Dict[str, List[str]]:
        """Get services grouped by programming language."""
        by_language: Dict[str, List[str]] = {}
        for service in self.services.values():
            if language and service.language != language:
                continue
            if service.language not in by_language:
                by_language[service.language] = []
            by_language[service.language].append(service.name)
        return by_language

    def _find_kafka_services(self) -> List[str]:
        """Find services that use Kafka."""
        return [name for name, service in self.services.items() if service.uses_kafka]