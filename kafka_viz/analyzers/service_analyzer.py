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
    # ... [previous code remains the same until _analyze_python_service] ...

    def _analyze_python_service(self, service: Service, result: AnalysisResult) -> None:
        """Analyze Python service for dependencies."""
        requirements_file = service.root_path / "requirements.txt"
        if requirements_file.exists():
            try:
                content = requirements_file.read_text()
                # Look for service-related dependencies
                service_pattern = re.compile(
                    r"^([\w-]+(?:-client|-service|-api))(?:[>=<~]|$)",
                    re.MULTILINE
                )

                logger.debug(f"Analyzing requirements content:\n{content}")
                
                for match in service_pattern.finditer(content):
                    service_name = match.group(1)
                    logger.debug(f"Found service dependency: {service_name}")

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
                        type="python-dependency",
                    )
                    result.service_relationships.append(relationship)

            except Exception as e:
                logger.warning(
                    f"Error analyzing requirements.txt for {service.name}: {e}"
                )

    # ... [rest of the code remains the same] ...