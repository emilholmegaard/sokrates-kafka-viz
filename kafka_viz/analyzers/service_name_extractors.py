"""Service name extractors for different build systems."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


class ServiceNameExtractor:
    """Base class for service name extractors."""

    def extract(self, build_file: Path) -> Optional[str]:
        """Extract service name from build file."""
        raise NotImplementedError()

    def _sanitize_name(self, name: str) -> str:
        """Sanitize service name."""
        if not name:
            return ""
        # Convert camelCase to kebab-case
        name = re.sub("([a-z0-9])([A-Z])", r"\1-\2", name).lower()
        # Replace spaces and underscores with hyphens
        name = re.sub(r"[\s_]+", "-", name)
        # Remove any invalid characters
        name = re.sub(r"[^a-z0-9-]", "", name)
        return name


class JavaServiceNameExtractor(ServiceNameExtractor):
    """Extract service name from Maven/Gradle build files."""

    def extract(self, build_file: Path) -> Optional[str]:
        """Extract service name from pom.xml or build.gradle."""
        if build_file.name == "pom.xml":
            return self._extract_from_pom(build_file)
        elif build_file.name in ["build.gradle", "build.gradle.kts"]:
            return self._extract_from_gradle(build_file)
        return None

    def _extract_from_pom(self, pom_file: Path) -> Optional[str]:
        """Extract service name from pom.xml."""
        try:
            tree = ET.parse(pom_file)
            root = tree.getroot()

            # Extract namespace if present
            match = re.match(r"\{.*\}", root.tag)
            ns = {"mvn": match.group(0)} if match else {}

            def ns_path(p):
                return p if not ns else f"mvn:{p}"

            # Try to extract artifactId
            artifact_id = root.find(ns_path("artifactId"), ns)
            if artifact_id is not None and artifact_id.text:
                return self._sanitize_name(artifact_id.text)

            # Try to extract name
            name = root.find(ns_path("name"), ns)
            if name is not None and name.text:
                return self._sanitize_name(name.text)

            # Use directory name as fallback
            dir_name = pom_file.parent.name
            if dir_name:
                return self._sanitize_name(dir_name)

        except ET.ParseError:
            # Handle specific XML parsing errors
            pass
        except Exception:
            # Log or handle other exceptions if necessary
            pass

        return None

    def _extract_from_gradle(self, gradle_file: Path) -> Optional[str]:
        """Extract service name from build.gradle."""
        try:
            content = gradle_file.read_text()

            # Try to find project name/artifactId
            match = re.search(r'rootProject\.name\s*=\s*[\'"]([^\'"]+)[\'"]', content)
            if match:
                name = match.group(1)
                if name not in self.parent_artifact_ids:
                    return self._sanitize_name(name)

            match = re.search(r'archivesBaseName\s*=\s*[\'"]([^\'"]+)[\'"]', content)
            if match:
                name = match.group(1)
                if name not in self.parent_artifact_ids:
                    return self._sanitize_name(name)

            # Try project name from settings.gradle if it exists
            settings_gradle = gradle_file.parent / "settings.gradle"
            if settings_gradle.exists():
                settings_content = settings_gradle.read_text()
                match = re.search(
                    r'rootProject\.name\s*=\s*[\'"]([^\'"]+)[\'"]', settings_content
                )
                if match:
                    name = match.group(1)
                    if name not in self.parent_artifact_ids:
                        return self._sanitize_name(name)

        except Exception:
            pass

        return None


class JavaScriptServiceNameExtractor(ServiceNameExtractor):
    """Extract service name from package.json."""

    def extract(self, build_file: Path) -> Optional[str]:
        """Extract service name from package.json."""
        try:
            with open(build_file) as f:
                package_json = json.load(f)
                name = package_json.get("name")
                if name:
                    # Remove scope from scoped packages
                    name = name.split("/")[-1]
                    return self._sanitize_name(name)
        except Exception:
            pass

        # Try directory name if package.json name is not available
        dir_name = build_file.parent.name
        if dir_name:
            return self._sanitize_name(dir_name)

        return None


class PythonServiceNameExtractor(ServiceNameExtractor):
    """Extract service name from Python build files."""

    def extract(self, build_file: Path) -> Optional[str]:
        """Extract service name from setup.py, pyproject.toml, or requirements.txt."""
        if build_file.name == "setup.py":
            return self._extract_from_setup_py(build_file)
        elif build_file.name == "pyproject.toml":
            return self._extract_from_pyproject_toml(build_file)

        # For requirements.txt, try directory name
        dir_name = build_file.parent.name
        if dir_name:
            return self._sanitize_name(dir_name)
        return None

    def _extract_from_setup_py(self, setup_file: Path) -> Optional[str]:
        """Extract service name from setup.py."""
        try:
            content = setup_file.read_text()
            # Look for name parameter in setup()
            match = re.search(
                r'setup\s*\([^)]*name\s*=\s*[\'"]([^\'"]+)[\'"]', content, re.DOTALL
            )
            if match:
                return self._sanitize_name(match.group(1))
        except Exception:
            pass
        return None

    def _extract_from_pyproject_toml(self, pyproject_file: Path) -> Optional[str]:
        """Extract service name from pyproject.toml."""
        try:
            content = pyproject_file.read_text()
            # Look for project name in [project] section
            match = re.search(
                r'\[project\][^\[]*name\s*=\s*[\'"]([^\'"]+)[\'"]', content, re.DOTALL
            )
            if match:
                return self._sanitize_name(match.group(1))
        except Exception:
            pass
        return None


class CSharpServiceNameExtractor(ServiceNameExtractor):
    """Extract service name from .csproj files."""

    def extract(self, build_file: Path) -> Optional[str]:
        """Extract service name from .csproj file."""
        try:
            tree = ET.parse(build_file)
            root = tree.getroot()

            # Try AssemblyName first
            assembly_name = root.find(".//AssemblyName")
            if assembly_name is not None and assembly_name.text:
                return self._sanitize_name(assembly_name.text)

            # Try RootNamespace
            root_namespace = root.find(".//RootNamespace")
            if root_namespace is not None and root_namespace.text:
                return self._sanitize_name(root_namespace.text)

            # Try PackageId
            package_id = root.find(".//PackageId")
            if package_id is not None and package_id.text:
                return self._sanitize_name(package_id.text)

        except Exception:
            pass

        # Fall back to file name without extension
        return self._sanitize_name(build_file.stem)
