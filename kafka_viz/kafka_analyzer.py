from typing import List, Set, Dict
from pathlib import Path
from .models import KafkaTopic, TopicType
from .analyzers.java_analyzer import JavaAnalyzer
# Import other analyzers

class KafkaAnalyzer:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.topics: Set[KafkaTopic] = set()
        self.analyzers = {
            '.java': JavaAnalyzer(),
            # Add other analyzers
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
                self.topics.update(file_topics)

        return list(self.topics)

    def _find_files(self) -> List[Path]:
        """Find all files with supported extensions."""
        files = []
        for ext in self.analyzers.keys():
            files.extend(self.root_path.rglob(f'*{ext}'))
        return files

    def get_topology(self) -> Dict:
        """
        Generate a topology map of Kafka topics and their producers/consumers.
        Enhanced to handle advanced patterns and configurations.
        """
        topology = {
            'nodes': [],
            'edges': []
        }

        # Add service nodes
        services = self._get_services()
        topology['nodes'].extend([
            {'id': service, 'type': 'service'}
            for service in services
        ])

        # Add topic nodes and edges
        for topic in self.topics:
            topic_id = topic.name
            if topic_id not in [n['id'] for n in topology['nodes']]:
                topology['nodes'].append({
                    'id': topic_id,
                    'type': 'topic',
                    'configBased': topic_id.startswith('${')
                })

            # Add edges based on topic type
            if topic.type == TopicType.PRODUCER:
                for service in topic.services:
                    topology['edges'].append({
                        'source': service,
                        'target': topic_id,
                        'type': 'produces'
                    })
            else:  # CONSUMER
                for service in topic.services:
                    topology['edges'].append({
                        'source': topic_id,
                        'target': service,
                        'type': 'consumes'
                    })

        return topology

    def _get_services(self) -> Set[str]:
        """Get unique service names from topics."""
        services = set()
        for topic in self.topics:
            services.update(topic.services)
        return services