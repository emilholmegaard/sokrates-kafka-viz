from abc import ABC, abstractmethod
from typing import List
from ..models.service import Service
from ..models.kafka import Topic
from ..utils.config import Config

class ServiceAnalyzer(ABC):
    @abstractmethod
    def analyze(self, path: str) -> List[Service]:
        pass

class KafkaAnalyzer:
    def __init__(self, config: Config, analyzers: List[ServiceAnalyzer]):
        self.config = config
        self.analyzers = analyzers

    def analyze_directory(self, path: str) -> List[Topic]:
        services = []
        for analyzer in self.analyzers:
            services.extend(analyzer.analyze(path))
        return self._extract_topics(services)

    def _extract_topics(self, services: List[Service]) -> List[Topic]:
        # Extract and consolidate topics from services
        pass