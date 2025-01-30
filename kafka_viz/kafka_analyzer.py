from typing import List, Set, Dict
from pathlib import Path
from .models.schema import KafkaTopic
from .models.service import Service
from .analyzers.java_analyzer import JavaAnalyzer

class KafkaAnalyzer:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.topics: Dict[str, KafkaTopic] = {}  # Change from Set to Dict
        self.analyzers = {
            '.java': JavaAnalyzer(),
        }

    def analyze(self) -> List[KafkaTopic]:
        """
        Analyze all supported files in the root path for Kafka topics.
        Now supports advanced patterns through specialized analyzers.
        """
        self.topics.clear()

        for file_path in self._find_files():
            suffix = file_path.suffix
            if suffix in self.analyzers:
                analyzer = self.analyzers[suffix]
                file_topics = analyzer.analyze_file(file_path)
                # Handle file_topics dictionary
                for topic_name, topic in file_topics.items():
                    if topic_name not in self.topics:
                        self.topics[topic_name] = topic
                    else:
                        # Merge data from both topics
                        self.topics[topic_name].producers.update(topic.producers)
                        self.topics[topic_name].consumers.update(topic.consumers)
                        for producer, locations in topic.producer_locations.items():
                            for location in locations:
                                self.topics[topic_name].add_producer_location(producer, location)
                        for consumer, locations in topic.consumer_locations.items():
                            for location in locations:
                                self.topics[topic_name].add_consumer_location(consumer, location)

        return list(self.topics.values())

    def _find_files(self) -> List[Path]:
        """Find all files with supported extensions."""
        files = []
        for ext in self.analyzers.keys():
            files.extend(self.root_path.rglob(f'*{ext}'))
        return files