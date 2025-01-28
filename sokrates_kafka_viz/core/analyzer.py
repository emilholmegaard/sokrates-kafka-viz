from abc import ABC, abstractmethod
from typing import Any, Dict

from .config import Config

class BaseAnalyzer(ABC):
    @abstractmethod
    async def analyze(self, config: Config) -> Any:
        """Execute the analysis and return results"""
        pass
    
    def is_enabled(self, config: Config) -> bool:
        """Check if this analyzer is enabled in the configuration"""
        analyzer_config = config.get_analyzer_config(self.__class__.__name__.lower())
        return analyzer_config.enabled if analyzer_config else True