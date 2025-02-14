"""Service analyzer for detecting microservices in a codebase."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Set

from ..models.service import Service
from ..models.service_registry import AnalysisResult, ServiceRelationship
from .base_analyzer import BaseAnalyzer
from .service_name_extractors import (
    CSharpServiceNameExtractor,
    JavaScriptServiceNameExtractor,
    JavaServiceNameExtractor,
    PythonServiceNameExtractor,
)

logger = logging.getLogger(__name__)


class ServiceAnalyzer(BaseAnalyzer):
    """Analyzer for detecting and analyzing microservices."""

    def __init__(self) -> None:
        """Initialize service analyzer with language-specific patterns."""
        self.build_patterns = {
            "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
            "javascript": ["package.json"],
            "python": ["pyproject.toml", "setup.py", "requirements.txt"],
            "csharp": [".csproj"],
        }
        self.name_extractors = {
            "java": JavaServiceNameExtractor(),
            "javascript": JavaScriptServiceNameExtractor(),
            "python": PythonServiceNameExtractor(),
            "csharp": CSharpServiceNameExtractor(),
        }
        self.test_dirs = {"test", "tests", "src/test", "src/tests"}

    def find_services(self, source_dir: Path) -> AnalysisResult:
        """Find all microservices in the given source directory.

        Args:
            source_dir: Root directory containing microservices

        Returns:
            AnalysisResult containing discovered services and their relationships
        """
        result = AnalysisResult(
            affected_service="root"
        )  # Special case for service discovery
        root_path = Path(source_dir)

        # Track processed directories to avoid duplicate services
        processed_dirs: Set[Path] = set()

        # Walk through all directories
        for path in root_path.rglob("*"):
            if not path.is_dir() or path in processed_dirs:
                continue

            # Skip test directories only if they are at the root level
            parent_is_root = path.parent == root_path
            if parent_is_root and path.name in self.test_dirs:
                continue

            service = self._detect_service(path)
            if service:
                result.discovered_services[service.name] = service
                processed_dirs.add(path)
                # Add all parent directories to processed to avoid duplicate detection
                processed_dirs.update(path.parents)

                # Analyze service for dependencies and add relationships
                self._analyze_service_dependencies(service, result)

        logger.debug(f"Found {len(result.discovered_services)} services in {root_path}")
        return result

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
                        logger.debug(
                            f"Found service '{name}' ({language}) in {build_file}"
                        )
                        return self._create_service(path, name, language, build_file)
        return None

    def _create_service(
        self, path: Path, name: str, language: str, build_file: Path
    ) -> Service:
        """Create a Service object with proper initialization."""
        service = Service(
            name=name,
            root_path=path,
            language=language,
        )
        # Add source files
        for ext in {
            "java": [".java"],
            "python": [".py"],
            "javascript": [".js", ".ts"],
            "csharp": [".cs"],
        }.get(language, []):
            for source_file in path.rglob(f"*{ext}"):
                if not any(
                    str(source_file).startswith(str(path / test_dir))
                    for test_dir in self.test_dirs
                ):
                    service.source_files.add(source_file)

        return service

    def _extract_service_name(self, build_file: Path, language: str) -> Optional[str]:
        """Extract service name from build file based on language."""
        try:
            extractor = self.name_extractors.get(language)
            if extractor:
                return extractor.extract(build_file)
        except Exception as e:
            logger.warning(f"Error extracting service name from {build_file}: {e}")
            return build_file.parent.name
        return None

    def _analyze_service_dependencies(
        self, service: Service, result: AnalysisResult
    ) -> None:
        """Analyze service for dependencies and add to results."""
        if service.language == "java":
            self._analyze_java_service(service, result)
        elif service.language == "javascript":
            self._analyze_node_service(service, result)
        elif service.language == "python":
            self._analyze_python_service(service, result)

    def _analyze_java_service(self, service: Service, result: AnalysisResult) -> None:
        """Analyze Java-based service for dependencies."""
        # Check for Spring Cloud dependencies in pom.xml
        pom_file = service.root_path / "pom.xml"
        if pom_file.exists():
            try:
                content = pom_file.read_text()
                if "spring-cloud" in content:
                    # Look for Spring Cloud Stream bindings
                    self._analyze_spring_cloud_bindings(service, result)
            except Exception as e:
                logger.warning(f"Error analyzing pom.xml for {service.name}: {e}")

    def _analyze_spring_cloud_bindings(
        self, service: Service, result: AnalysisResult
    ) -> None:
        """Analyze Spring Cloud Stream bindings in configuration."""
        config_files = [
            service.root_path / "src/main/resources/application.yml",
            service.root_path / "src/main/resources/application.yaml",
            service.root_path / "src/main/resources/application.properties",
        ]

        for config_file in config_files:
            if config_file.exists():
                try:
                    content = config_file.read_text()
                    # Look for service dependencies in configuration
                    service_pattern = re.compile(r"([\w-]+)\.url\s*=\s*([^\s]+)")

                    for match in service_pattern.finditer(content):
                        dep_service_name = match.group(1)
                        service_url = match.group(2)

                        # Add as discovered service if not already known
                        if dep_service_name not in result.discovered_services:
                            dep_service = Service(
                                name=dep_service_name, root_path=service.root_path
                            )
                            result.discovered_services[dep_service_name] = dep_service

                        # Add relationship
                        relationship = ServiceRelationship(
                            source=service.name,
                            target=dep_service_name,
                            type_="spring-cloud",
                            details={"url": service_url},
                        )
                        result.service_relationships.append(relationship)

                except Exception as e:
                    logger.warning(f"Error analyzing config file {config_file}: {e}")

    def _analyze_node_service(self, service: Service, result: AnalysisResult) -> None:
        """Analyze Node.js service for dependencies."""
        package_json = service.root_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }

                # Look for microservice-related dependencies
                service_deps = [
                    d
                    for d in deps
                    if any(
                        keyword in d.lower() for keyword in ["service", "client", "api"]
                    )
                ]

                for dep in service_deps:
                    # Convert npm package names to service names
                    service_name = dep.replace("@", "").replace("/", "-")

                    # Add as discovered service
                    if service_name not in result.discovered_services:
                        dep_service = Service(
                            name=service_name, root_path=service.root_path
                        )
                        result.discovered_services[service_name] = dep_service

                    # Add relationship
                    relationship = ServiceRelationship(
                        source=service.name,
                        target=service_name,
                        type_="npm-dependency",
                        details={"version": deps[dep]},
                    )
                    result.service_relationships.append(relationship)

            except Exception as e:
                logger.warning(f"Error analyzing package.json for {service.name}: {e}")

    def _analyze_python_service(self, service: Service, result: AnalysisResult) -> None:
        """Analyze Python service for dependencies."""
        requirements_file = service.root_path / "requirements.txt"
        if requirements_file.exists():
            try:
                content = requirements_file.read_text()
                # Look for service-related dependencies
                service_pattern = re.compile(
                    r"^([a-zA-Z0-9-]+(?:-client|-service|-api))[>=<~]"
                )

                for match in service_pattern.finditer(content):
                    service_name = match.group(1)

                    # Add as discovered service
                    if service_name not in result.discovered_services:
                        dep_service = Service(
                            name=service_name, root_path=service.root_path
                        )
                        result.discovered_services[service_name] = dep_service

                    # Add relationship
                    relationship = ServiceRelationship(
                        source=service.name,
                        target=service_name,
                        type_="python-dependency",
                    )
                    result.service_relationships.append(relationship)

            except Exception as e:
                logger.warning(
                    f"Error analyzing requirements.txt for {service.name}: {e}"
                )

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the service analyzer."""
        return {
            "supported_languages": list(self.build_patterns.keys()),
            "test_directories": list(self.test_dirs),
            "analyzer_type": self.__class__.__name__,
            "status": "active",
        }
