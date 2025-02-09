"""Base class for service-level analyzers."""

from abc import abstractmethod
from typing import Any, Dict

from ..models.service_collection import ServiceCollection
from .base_analyzer import BaseAnalyzer


class ServiceLevelAnalyzer(BaseAnalyzer):
    """Base class for analyzers that work on the entire service collection."""

    @abstractmethod
    def analyze_services(self, services: ServiceCollection) -> None:
        """Analyze the entire service collection.

        Args:
            services: Collection of services to analyze
        """
        pass

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information from the analyzer.

        Returns:
            Dict containing debug information
        """
        return {
            "analyzer": self.__class__.__name__,
            "type": "service-level",
        }
