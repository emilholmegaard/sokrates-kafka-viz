# base.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional


class BaseGenerator(ABC):
    """Base class for all visualization generators.
    
    This abstract class defines the interface that all visualization generators
    must implement. Visualization generators are responsible for converting the
    Kafka analysis data into visual representations.
    
    Attributes:
        name (str): Display name of the visualization
        description (str): Description of the visualization
    """
    
    def __init__(self):
        self.name = "Base Visualization"
        self.description = "Abstract base class for visualizations"
    
    @abstractmethod
    def generate_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML content for the visualization.
        
        Args:
            data: The parsed Kafka analysis data
            
        Returns:
            str: HTML content for the visualization
        """
        pass

    @abstractmethod
    def generate_output(self, data: Dict[str, Any], file_path: Path) -> None:
        """Generate the visualization output files.
        
        Args:
            data: The parsed Kafka analysis data
            file_path: Path where to save the visualization files
        """
        pass
    
    def get_info(self) -> Dict[str, str]:
        """Get information about this visualization generator.
        
        Returns:
            dict: Information about the generator
        """
        return {
            "name": getattr(self, "name", "Unknown"),
            "description": getattr(self, "description", "No description available")
        }
