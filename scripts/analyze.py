#!/usr/bin/env python3

import os
import json
import re
import sys
from typing import Dict, List, Set, Optional
from pathlib import Path
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console
from rich.traceback import install
from kafka_pattern_finder import KafkaPatternFinder
from parse_avro import AvroSchemaParser

# Install rich traceback handler
install(show_locals=True)
console = Console()

class KafkaAnalyzer:
    # Define supported file extensions and their languages
    SUPPORTED_EXTENSIONS = {
        # JVM languages
        '.java': 'Java',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.groovy': 'Groovy',
        # .NET languages
        '.cs': 'C#',
        '.vb': 'Visual Basic',
        # Python
        '.py': 'Python',
        # JavaScript/TypeScript
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        # Go
        '.go': 'Go',
        # Rust
        '.rs': 'Rust',
        # Schema files
        '.avsc': 'Avro Schema',
        '.proto': 'Protocol Buffers'
    }

    # Directories to skip
    SKIP_DIRS = {
        'node_modules', 'venv', '.git', '.idea', 'target', 'build', 
        'dist', '__pycache__', '.vscode', 'bin', 'obj'
    }

    def __init__(self, source_dir: str):
        self.source_dir = Path(source_dir)
        self.pattern_finder = KafkaPatternFinder()
        self.avro_parser = AvroSchemaParser()
        self.services: Dict[str, Dict] = {}
        self.topics: Set[str] = set()
        self.processed_files: Set[str] = set()
        self.checkpoint_file = Path('analysis_checkpoint.json')
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'skipped_files': 0,
            'errors': 0,
            'by_language': {}
        }

    def load_checkpoint(self) -> bool:
        """Load progress from checkpoint if it exists."""
        try:
            if self.checkpoint_file.exists():
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                    self.services = {k: {
                        'producers': set(v['producers']),
                        'consumers': set(v['consumers']),
                        'schemas': set(v['schemas'])
                    } for k, v in checkpoint['services'].items()}
                    self.topics = set(checkpoint['topics'])
                    self.processed_files = set(checkpoint['processed_files'])
                    self.stats = checkpoint['stats']
                return True
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load checkpoint: {e}[/]")
        return False

    def save_checkpoint(self):
        """Save current progress to checkpoint file."""
        try:
            checkpoint = {
                'services': {k: {
                    'producers': list(v['producers']),
                    'consumers': list(v['consumers']),
                    'schemas': list(v['schemas'])
                } for k, v in self.services.items()},
                'topics': list(self.topics),
                'processed_files': list(self.processed_files),
                'stats': self.stats
            }
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save checkpoint: {e}[/]")

    def should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed based on extension and path."""
        # Skip if already processed
        if str(file_path) in self.processed_files:
            return False

        # Skip if in ignored directory
        if any(part in self.SKIP_DIRS for part in file_path.parts):
            return False

        # Only process supported file types
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single file for Kafka patterns."""
        if not self.should_process_file(file_path):
            self.stats['skipped_files'] += 1
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            language = self.SUPPORTED_EXTENSIONS[file_path.suffix.lower()]
            self.stats['by_language'][language] = self.stats['by_language'].get(language, 0) + 1

            # Detect service name from path or build file
            service_name = self._detect_service_name(file_path)
            
            if service_name not in self.services:
                self.services[service_name] = {
                    'producers': set(),
                    'consumers': set(),
                    'schemas': set()
                }

            # Find Kafka producers and consumers based on file type
            producers = self.pattern_finder.find_producers(content, language)
            consumers = self.pattern_finder.find_consumers(content, language)

            self.services[service_name]['producers'].update(producers)
            self.services[service_name]['consumers'].update(consumers)
            self.topics.update(producers)
            self.topics.update(consumers)

            # Parse schema files
            if file_path.suffix == '.avsc':
                schema = self.avro_parser.parse_schema(content)
                if schema and 'name' in schema:
                    self.services[service_name]['schemas'].add(schema['name'])

            self.processed_files.add(str(file_path))
            self.stats['processed_files'] += 1

        except UnicodeDecodeError:
            self.stats['skipped_files'] += 1
            console.print(f"[yellow]Skipping binary file: {file_path}[/]")
        except Exception as e:
            self.stats['errors'] += 1
            console.print(f"[red]Error processing {file_path}: {e}[/]")

    def analyze(self) -> Dict:
        """Analyze the entire codebase with progress tracking and checkpointing."""
        # Try to load checkpoint
        resumed = self.load_checkpoint()
        if resumed:
            console.print("[green]Resumed from previous checkpoint[/]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            # Count files first
            if not resumed:
                count_task = progress.add_task("Counting files...", total=None)
                self.stats['total_files'] = sum(1 for _ in self.source_dir.rglob('*') 
                                              if _.is_file() and self.should_process_file(_))
                progress.remove_task(count_task)

            # Process files
            scan_task = progress.add_task(
                "Scanning files...", 
                total=self.stats['total_files']
            )
            progress.update(scan_task, completed=len(self.processed_files))

            try:
                for file_path in self.source_dir.rglob('*'):
                    if file_path.is_file():
                        self.analyze_file(file_path)
                        progress.update(scan_task, completed=len(self.processed_files))
                        # Save checkpoint periodically
                        if len(self.processed_files) % 100 == 0:
                            self.save_checkpoint()

            except KeyboardInterrupt:
                console.print("\n[yellow]Analysis interrupted. Progress saved to checkpoint.[/]")
                self.save_checkpoint()
                sys.exit(1)

        # Save final checkpoint
        self.save_checkpoint()

        # Convert sets to lists for JSON serialization
        result = {
            'services': {},
            'topics': list(self.topics),
            'stats': self.stats
        }

        for service, data in self.services.items():
            result['services'][service] = {
                'producers': list(data['producers']),
                'consumers': list(data['consumers']),
                'schemas': list(data['schemas'])
            }

        return result

    def _detect_service_name(self, file_path: Path) -> str:
        """Extract service name from build files or directory structure."""
        # Implementation remains the same
        possible_build_files = ['pom.xml', 'build.gradle', 'package.json']
        current_dir = file_path.parent

        while current_dir != self.source_dir and current_dir.parent != current_dir:
            for build_file in possible_build_files:
                if (current_dir / build_file).exists():
                    return self._extract_service_name_from_build_file(current_dir / build_file)
            current_dir = current_dir.parent

        return file_path.parent.name

    def _extract_service_name_from_build_file(self, build_file: Path) -> str:
        """Extract service name from build file based on its type."""
        # Implementation remains the same
        if build_file.name == 'pom.xml':
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
            try:
                with open(build_file, 'r') as f:
                    package_data = json.load(f)
                    if 'name' in package_data:
                        return package_data['name']
            except Exception:
                pass
        
        elif build_file.name == 'build.gradle':
            try:
                with open(build_file, 'r') as f:
                    content = f.read()
                    match = re.search(r'rootProject\.name\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                    if match:
                        return match.group(1)
            except Exception:
                pass

        return build_file.parent.name

app = typer.Typer()

@app.command()
def main(
    source_dir: Path = typer.Argument(..., help="Directory containing microservices source code"),
    output: Path = typer.Option("analysis_output.json", help="Output JSON file path"),
    clean: bool = typer.Option(False, help="Start fresh analysis (ignore checkpoint)")
):
    """Analyze Kafka microservices architecture from source code."""
    # Delete checkpoint if clean start requested
    if clean and Path('analysis_checkpoint.json').exists():
        Path('analysis_checkpoint.json').unlink()

    analyzer = KafkaAnalyzer(str(source_dir))
    result = analyzer.analyze()

    # Print analysis summary
    console.print("\n[bold]Analysis Summary:[/]")
    console.print(f"Total files scanned: {result['stats']['total_files']}")
    console.print(f"Files processed: {result['stats']['processed_files']}")
    console.print(f"Files skipped: {result['stats']['skipped_files']}")
    console.print(f"Errors encountered: {result['stats']['errors']}")
    console.print("\n[bold]Files analyzed by language:[/]")
    for lang, count in result['stats']['by_language'].items():
        console.print(f"- {lang}: {count}")

    with open(output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    console.print(f"\n[green]Analysis complete! Results written to {output}[/]")

if __name__ == "__main__":
    app()