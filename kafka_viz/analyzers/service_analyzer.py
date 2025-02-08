"""Service analyzer for detecting microservices in a codebase."""

import json
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..models.service import Service

logger = logging.getLogger(__name__)


class ServiceAnalyzer:
    """Analyzer for detecting and analyzing microservices."""

    def __init__(self):
        """Initialize service analyzer with language-specific patterns."""
        self.build_patterns = {
            "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
            "javascript": ["package.json"],
            "python": ["pyproject.toml", "setup.py", "requirements.txt"],
            "csharp": [".csproj"],
        }
        self.test_dirs = {"test", "tests", "src/test", "src/tests"}

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
        for path in root_path.rglob("*"):
            # Skip test directories unless explicitly included
            if any(test_dir in str(path) for test_dir in self.test_dirs):
                continue

            service = self._detect_service(path)
            if service:
                services[service.name] = service

        logger.debug(f"Found {len(services)} services in {root_path}")

        return services

    def _detect_service(self, path: Path) -> Optional[Service]:
        """Detect if path contains a service by looking for build files."""
        if not path.is_dir():
            return None

        logger.debug(f"Found {len(self.build_patterns)} services in {path}")
        for language, patterns in self.build_patterns.items():

            for pattern in patterns:
                build_file = path / pattern
                if build_file.exists():
                    name = self._extract_service_name(build_file, language)

                    if name:
                        logger.debug(f"Found {name} as potential name in {pattern}")
                        # Create service
                        service = Service(
                            name=name,
                            root_path=path,
                            language=language,
                            build_file=build_file,
                        )

                        # Collect source files based on language
                        extensions = {
                            "java": [".java", ".kt", ".scala"],
                            "javascript": [".js", ".ts"],
                            "python": [".py"],
                            "csharp": [".cs"],
                        }

                        # Get all source files with matching extensions
                        for ext in extensions.get(language, []):
                            for source_file in path.rglob(f"*{ext}"):
                                # Skip test files
                                if not any(
                                    test_dir in str(source_file.relative_to(path))
                                    for test_dir in self.test_dirs
                                ):
                                    service.source_files.add(source_file)

                        return service
        return None

    def _extract_service_name(self, build_file: Path, language: str) -> Optional[str]:
        """Extract service name from build file based on language."""
        try:
            if language == "java":
                if build_file.name == "pom.xml":
                    tree = ET.parse(build_file)
                    root = tree.getroot()
                    # Handle XML namespaces in pom.xml
                    ns = {"maven": "http://maven.apache.org/POM/4.0.0"}
                    artifact_id = root.find(".//maven:artifactId", ns)
                    return artifact_id.text if artifact_id is not None else None
                else:
                    # For Gradle, use directory name as fallback
                    return build_file.parent.name

            elif language == "javascript":
                with open(build_file) as f:
                    package_data = json.load(f)
                    return package_data.get("name")

            elif language == "python":
                if build_file.name == "pyproject.toml":
                    import tomli

                    with open(build_file, "rb") as f:
                        data = tomli.load(f)
                        return data.get("tool", {}).get("poetry", {}).get(
                            "name"
                        ) or data.get("project", {}).get("name")
                else:
                    # For requirements.txt or setup.py, use directory name
                    return build_file.parent.name

            elif language == "csharp":
                tree = ET.parse(build_file)
                root = tree.getroot()
                assembly_name = root.find(".//AssemblyName")
                return (
                    assembly_name.text if assembly_name is not None else build_file.stem
                )

        except Exception as e:
            print(f"Error extracting service name from {build_file}: {e}")
            # Fallback to directory name
            return build_file.parent.name

        return None

    def _analyze_java_service(self, service: Service) -> None:
        """Analyze Java-based service for dependencies."""
        # Look for Spring Cloud Stream bindings
        for java_file in service.root_path.rglob("*.java"):
            with open(java_file) as f:
                content = f.read()
                # Check for Spring Cloud Stream annotations
                if "@EnableBinding" in content:
                    # Extract topics from bindings
                    pass

    def _analyze_node_service(self, service: Service) -> None:
        """Analyze Node.js service for dependencies."""
        package_json = service.root_path / "package.json"
        if package_json.exists():
            with open(package_json) as f:
                data = json.load(f)
                # Check for Kafka-related dependencies
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }
                kafka_deps = [d for d in deps if "kafka" in d.lower()]
                if kafka_deps:
                    # Service uses Kafka, analyze source files
                    pass

    def _analyze_python_service(self, service: Service) -> None:
        """Analyze Python service for dependencies."""
        requirements_file = service.root_path / "requirements.txt"
        if requirements_file.exists():
            with open(requirements_file) as f:
                content = f.read()
                if "kafka" in content.lower():
                    # Service uses Kafka, analyze source files
                    pass

    def _find_dependencies(self) -> None:
        """Find dependencies between services based on shared topics."""
        # This should be implemented as part of issue #13
        pass

    def get_service_by_name(self, service_name: str) -> Optional[Service]:
        """Get a service by its name."""
        # This requires services to be discovered first
        pass

    def get_services_by_language(self, language: str) -> Dict[str, Service]:
        """Get services filtered by programming language.

         Args:
            language: Programming language to filter by (e.g., 'java', 'python')

        Returns:
            Dict[str, Service]: Dictionary of services that use the specified language

        Note:
            This requires services to be discovered first using find_services()
        """
        if not hasattr(self, "_discovered_services"):
            logger.warning("No services discovered yet. Call find_services() first.")
            return {}

        return {
            name: service
            for name, service in self._discovered_services.items()
            if service.language.lower() == language.lower()
        }

    def get_services_with_schema(self, schema_name: str) -> Dict[str, Service]:
        """Get services that use a specific schema.

        Args:
            schema_name: Name of the schema to search for (e.g., 'UserEvent.avsc')

        Returns:
            Dict[str, Service]: Dictionary of services that use the specified schema

        Note:
            This requires services to be discovered first using find_services()
        """
        if not hasattr(self, "_discovered_services"):
            logger.warning("No services discovered yet. Call find_services() first.")
            return {}

        matching_services = {}

        for name, service in self._discovered_services.items():
            # Look for schema files in common schema locations
            schema_locations = [
                service.root_path / "src/main/avro",
                service.root_path / "src/main/resources/avro",
                service.root_path / "schemas",
                service.root_path / "avro",
            ]

            # Check source files for schema references
            schema_pattern = re.compile(
                rf'(?:Schema|@AvroGenerated|schemaReference)\s*[=:]\s*["\'].*{re.escape(schema_name)}["\']'
            )

            # Check if schema file exists in any location
            schema_exists = any(
                loc.exists() and any(f.name == schema_name for f in loc.glob("*.avsc"))
                for loc in schema_locations
            )

            # Check if schema is referenced in source files
            schema_referenced = any(
                schema_pattern.search(source_file.read_text())
                for source_file in service.source_files
                if source_file.exists()
            )

            if schema_exists or schema_referenced:
                matching_services[name] = service

        return matching_services
