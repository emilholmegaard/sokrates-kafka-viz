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
        # Try pom.xml first
        if build_file.name == "pom.xml":
            try:
                tree = ET.parse(build_file)
                root = tree.getroot()
                artifact_id = root.find(".//artifactId")
                if artifact_id is not None and artifact_id.text:
                    return artifact_id.text
            except ET.ParseError:
                pass

        # Try gradle file
        if build_file.name == "build.gradle" and build_file.exists():
            try:
                content = build_file.read_text()
                if "rootProject.name" in content:
                    match = re.search(
                        r"rootProject\.name\s*=\s*['\"](.+?)['\"]", content
                    )
                    if match:
                        return match.group(1)
            except Exception:
                pass

        # Fallback to directory name
        return build_file.parent.name


class JavaScriptServiceNameExtractor(ServiceNameExtractor):
    def extract(self, build_file: Path) -> Optional[str]:
        """Extract service name from package.json."""
        if build_file.name != "package.json":
            return build_file.parent.name

        try:
            content = build_file.read_text()
            package_data = json.loads(content)
            name = package_data.get("name", "")
            if not name:
                return build_file.parent.name

            # Remove scope from name if present
            return name.split("/")[-1] if "/" in name else name
        except (json.JSONDecodeError, FileNotFoundError):
            return build_file.parent.name


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
