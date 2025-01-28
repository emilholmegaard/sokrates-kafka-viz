#!/usr/bin/env python3

import os
import json
import re
from typing import Dict, List, Set
from pathlib import Path
import typer
from rich.progress import Progress
from kafka_pattern_finder import KafkaPatternFinder
from parse_avro import AvroSchemaParser

class KafkaAnalyzer:
    def __init__(self, source_dir: str):
        self.source_dir = Path(source_dir)
        self.pattern_finder = KafkaPatternFinder()
        self.avro_parser = AvroSchemaParser()
        self.services: Dict[str, Dict] = {}
        self.topics: Set[str] = set()

    def analyze_file(self, file_path: Path) -> None:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Detect service name from path or build file
        service_name = self._detect_service_name(file_path)
        
        if service_name not in self.services:
            self.services[service_name] = {
                'producers': set(),
                'consumers': set(),
                'schemas': set()
            }

        # Find Kafka producers
        producers = self.pattern_finder.find_producers(content)
        self.services[service_name]['producers'].update(producers)
        self.topics.update(producers)

        # Find Kafka consumers
        consumers = self.pattern_finder.find_consumers(content)
        self.services[service_name]['consumers'].update(consumers)
        self.topics.update(consumers)

        # Parse Avro schemas if present
        if file_path.suffix == '.avsc':
            schema = self.avro_parser.parse_schema(content)
            if schema and 'name' in schema:
                self.services[service_name]['schemas'].add(schema['name'])

    def analyze(self) -> Dict:
        with Progress() as progress:
            task = progress.add_task("Analyzing codebase...", total=0)
            
            # Count total files
            total_files = sum(1 for _ in self.source_dir.rglob('*') 
                            if _.is_file() and not _.name.startswith('.'))
            progress.update(task, total=total_files)

            # Process each file
            for file_path in self.source_dir.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    self.analyze_file(file_path)
                    progress.advance(task)

        # Convert sets to lists for JSON serialization
        result = {
            'services': {},
            'topics': list(self.topics)
        }

        for service, data in self.services.items():
            result['services'][service] = {
                'producers': list(data['producers']),
                'consumers': list(data['consumers']),
                'schemas': list(data['schemas'])
            }

        return result

    def _detect_service_name(self, file_path: Path) -> str:
        # Try to detect service name from common build files or directory structure
        possible_build_files = ['pom.xml', 'build.gradle', 'package.json']
        current_dir = file_path.parent

        while current_dir != self.source_dir and current_dir.parent != current_dir:
            for build_file in possible_build_files:
                if (current_dir / build_file).exists():
                    # Extract service name from build file
                    return self._extract_service_name_from_build_file(
                        current_dir / build_file)
            current_dir = current_dir.parent

        # Fallback: use parent directory name
        return file_path.parent.name

    def _extract_service_name_from_build_file(self, build_file: Path) -> str:
        """Extract service name from build file based on its type."""
        if build_file.name == 'pom.xml':
            # Try to extract from Maven artifact ID
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(build_file)
                root = tree.getroot()
                artifact_id = root.find('{http://maven.apache.org/POM/4.0.0}artifactId')
                if artifact_id is not None:
                    return artifact_id.text
            except Exception:
                pass
        
        elif build_file.name == 'package.json':
            # Try to extract from npm package name
            try:
                with open(build_file, 'r') as f:
                    package_data = json.load(f)
                    if 'name' in package_data:
                        return package_data['name']
            except Exception:
                pass
        
        elif build_file.name == 'build.gradle':
            # Try to extract from Gradle project name
            try:
                with open(build_file, 'r') as f:
                    content = f.read()
                    match = re.search(r'rootProject\.name\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                    if match:
                        return match.group(1)
            except Exception:
                pass

        # Fallback to directory name if we couldn't extract from build file
        return build_file.parent.name

def main(
    source_dir: str = typer.Argument(..., help="Directory containing microservices source code"),
    output: str = typer.Option("analysis_output.json", help="Output JSON file path")
):
    """Analyze Kafka microservices architecture from source code."""
    analyzer = KafkaAnalyzer(source_dir)
    result = analyzer.analyze()

    with open(output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"Analysis complete! Results written to {output}")

if __name__ == "__main__":
    typer.run(main)