import json
import logging
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ServiceNameExtractor(ABC):
    """Base class for service name extraction strategies."""

    @abstractmethod
    def extract(self, build_file: Path) -> Optional[str]:
        """Extract service name from build file."""
        pass

    def _get_fallback_name(self, build_file: Path) -> str:
        """Get fallback name from directory."""
        return build_file.parent.name


class JavaServiceNameExtractor(ServiceNameExtractor):
    def extract(self, build_file: Path) -> Optional[str]:
        if build_file.name == "pom.xml":
            return self._extract_from_pom(build_file)
        return self._get_fallback_name(build_file)

    def _extract_from_pom(self, pom_file: Path) -> str:
        tree = ET.parse(pom_file)
        root = tree.getroot()
        ns = {"maven": "http://maven.apache.org/POM/4.0.0"}

        for element in ["artifactId", "name"]:
            node = root.find(f".//maven:{element}", ns)
            if node is not None and node.text:
                return node.text.strip()

        return self._get_fallback_name(pom_file)


class JavaScriptServiceNameExtractor(ServiceNameExtractor):
    def extract(self, build_file: Path) -> Optional[str]:
        try:
            with open(build_file) as f:
                package_data = json.load(f)
                if name := package_data.get("name"):
                    return name.strip()
        except Exception as e:
            logger.warning(f"Error parsing package.json: {e}")
        return self._get_fallback_name(build_file)


class PythonServiceNameExtractor(ServiceNameExtractor):
    def extract(self, build_file: Path) -> Optional[str]:
        if build_file.name == "pyproject.toml":
            return self._extract_from_pyproject(build_file)
        elif build_file.name == "setup.py":
            return self._extract_from_setup(build_file)
        return self._get_fallback_name(build_file)

    def _extract_from_pyproject(self, build_file: Path) -> str:
        try:
            import tomli

            with open(build_file, "rb") as f:
                data = tomli.load(f)
                poetry_name = data.get("tool", {}).get("poetry", {}).get("name")
                project_name = data.get("project", {}).get("name")
                return (
                    poetry_name or project_name or self._get_fallback_name(build_file)
                )
        except Exception as e:
            logger.warning(f"Error parsing pyproject.toml: {e}")
            return self._get_fallback_name(build_file)

    def _extract_from_setup(self, build_file: Path) -> str:
        try:
            with open(build_file) as f:
                content = f.read()
                if match := re.search(r'name=["\']([^"\']+)["\']', content):
                    return match.group(1).strip()
        except Exception as e:
            logger.warning(f"Error parsing setup.py: {e}")
        return self._get_fallback_name(build_file)


class CSharpServiceNameExtractor(ServiceNameExtractor):
    def extract(self, build_file: Path) -> Optional[str]:
        try:
            tree = ET.parse(build_file)
            root = tree.getroot()
            if assembly_name := root.find(".//AssemblyName"):
                if assembly_name.text:
                    return assembly_name.text.strip()
        except Exception as e:
            logger.warning(f"Error parsing .csproj: {e}")
        return build_file.stem
