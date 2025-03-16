"""
Visualization factory for creating and managing visualization generators.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .architecture_viz import ArchitectureVisualizer
from .base import BaseGenerator
from .index_generator import IndexGenerator
from .kafka_viz import KafkaViz
from .mermaid import MermaidGenerator
from .simple_viz import SimpleViz

logger = logging.getLogger(__name__)


class VisualizationFactory:
    """Factory for creating visualization generators.

    This class is responsible for managing and creating visualization generators
    based on configuration and user preferences.
    """

    def __init__(self):
        self._generators: Dict[str, Type[BaseGenerator]] = {
            "react": KafkaViz,
            "mermaid": MermaidGenerator,
            "simple": SimpleViz,
            "architecture": ArchitectureVisualizer,
            "index": IndexGenerator,
        }
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load visualization configuration from the config file."""
        try:
            # Try to load from primary location
            config_path = Path(__file__).parent / "resources" / "config.json"
            if config_path.exists():
                with open(config_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading visualization config: {e}")

        # Return default config if loading fails
        return {
            "visualizations": {
                "react": {
                    "name": "React Interactive",
                    "description": "Interactive D3.js visualization with React UI",
                    "enabled": True,
                },
                "mermaid": {
                    "name": "Mermaid Diagram",
                    "description": "Simple Mermaid.js flowchart diagram",
                    "enabled": True,
                },
                "simple": {
                    "name": "Simple HTML",
                    "description": "Basic HTML visualization",
                    "enabled": True,
                },
                "architecture": {
                    "name": "Architecture Visualization",
                    "description": "Visualization of system architecture",
                    "enabled": True,
                },
                "index": {
                    "name": "Visualization Index",
                    "description": "Entry point linking to all visualizations",
                    "enabled": True,
                },
            }
        }

    def register_generator(
        self, name: str, generator_class: Type[BaseGenerator]
    ) -> None:
        """Register a new visualization generator.

        Args:
            name: Unique identifier for the generator
            generator_class: Class implementing BaseGenerator interface
        """
        self._generators[name] = generator_class

        # Update config if needed
        if name not in self._config["visualizations"]:
            # Create a generator instance to get name and description
            instance = generator_class()
            self._config["visualizations"][name] = {
                "name": getattr(instance, "name", name),
                "description": getattr(instance, "description", ""),
                "enabled": True,
            }

    def get_available_generators(self) -> Dict[str, Dict[str, Any]]:
        """Get all available visualization generators.

        Returns:
            dict: Mapping of generator IDs to metadata
        """
        available = {}
        for id, metadata in self._config["visualizations"].items():
            if (
                metadata.get("enabled", True)
                and id in self._generators
                and id != "index"
            ):
                available[id] = metadata
        return available

    def create_generator(self, name: str) -> Optional[BaseGenerator]:
        """Create an instance of the specified visualization generator.

        Args:
            name: Identifier of the generator to create

        Returns:
            BaseGenerator: Instantiated generator or None if not found
        """
        # Check if the generator is available and enabled
        available = self.get_all_generators()
        if name not in available:
            return None

        # Get the generator class and instantiate it
        generator_class = self._generators.get(name)
        if not generator_class:
            return None

        return generator_class()

    def get_all_generators(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered visualization generators, including internal ones.

        Returns:
            dict: Mapping of generator IDs to metadata
        """
        available = {}
        for id, metadata in self._config["visualizations"].items():
            if metadata.get("enabled", True) and id in self._generators:
                available[id] = metadata
        return available

    def create_all_generators(self, exclude: List[str]) -> Dict[str, BaseGenerator]:
        """Create instances of all available visualization generators.

        Args:
            exclude: List of generator IDs to exclude

        Returns:
            dict: Mapping of generator IDs to instantiated generators
        """
        if exclude is None:
            exclude = []

        generators = {}
        for id, metadata in self.get_available_generators().items():
            if id not in exclude:
                generator = self.create_generator(id)
                if generator:
                    generators[id] = generator

        return generators


# Singleton instance for use throughout the application
visualization_factory = VisualizationFactory()
