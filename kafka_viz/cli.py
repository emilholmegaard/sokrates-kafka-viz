"""Command-line interface for Kafka visualization tool."""

import json
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress

from .analyzers.analyzer_manager import AnalyzerManager
from .visualization.mermaid import MermaidGenerator

app = typer.Typer()
console = Console()


def is_source_file(file_path: Path) -> bool:
    """Check if a file is a source file that should be analyzed."""
    # Define extensions for source files we want to analyze
    SOURCE_EXTENSIONS = {
        ".java",
        ".kt",
        ".scala",  # JVM languages
        ".py",  # Python
        ".js",
        ".ts",  # JavaScript/TypeScript
        ".go",  # Go
        ".cs",  # C#
        ".xml",
        ".yaml",
        ".yml",  # Config files
        ".properties",  # Java properties
        ".gradle",
        ".sbt",  # Build files
    }

    # Skip hidden files and directories
    if any(part.startswith(".") for part in file_path.parts):
        return False

    # Skip common binary and non-source directories
    SKIP_DIRS = {
        "node_modules",
        "target",
        "build",
        "dist",
        "venv",
        "__pycache__",
        ".git",
        ".idea",
        ".vscode",
    }
    if any(part in SKIP_DIRS for part in file_path.parts):
        return False

    return file_path.suffix.lower() in SOURCE_EXTENSIONS


@app.command()
def analyze(
    source_dir: Path = typer.Argument(
        ...,
        help="Directory containing microservices source code",
        exists=True,
        dir_okay=True,
        resolve_path=True,
    ),
    output: Path = typer.Option(
        "analysis_output.json", help="Output file for analysis results"
    ),
    include_tests: bool = typer.Option(False, help="Include test files in analysis"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
):
    """Analyze Kafka usage in a microservices codebase."""
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logger = logging.getLogger("kafka_viz")

    try:
        # Initialize analyzer manager
        analyzer_manager = AnalyzerManager()

        with Progress() as progress:
            # First pass: identify services
            task = progress.add_task("Identifying services...", total=None)
            services = analyzer_manager.discover_services(source_dir)
            progress.remove_task(task)

            # Second pass: analyze schemas
            task = progress.add_task(
                "Analyzing schemas...", total=len(services.services)
            )
            for service in services.services.values():
                analyzer_manager.analyze_schemas(service)
                progress.advance(task)
            progress.remove_task(task)

            # Third pass: analyze source files
            task = progress.add_task(
                "Analyzing source files...", total=len(services.services)
            )
            for service in services.services.values():
                for file_path in service.root_path.rglob("*"):
                    if file_path.is_file() and is_source_file(file_path):
                        try:
                            topics = analyzer_manager.analyze_file(file_path, service)
                            if topics:
                                service.topics.update(topics)
                        except Exception as e:
                            if verbose:
                                logger.warning(f"Error analyzing file {file_path}: {e}")
                progress.advance(task)

        # Save analysis results
        analyzer_manager.save_output(services, output, include_debug=verbose)
        console.print(f"\n[green]Analysis complete! Results written to {output}")

    except Exception as e:
        console.print(f"[red]Error during analysis: {e}")
        raise typer.Exit(1)


@app.command()
def visualize(
    input_file: Path = typer.Argument(
        ..., help="JSON file containing analysis results", exists=True
    ),
    output: Path = typer.Option(
        "architecture.html", help="Output HTML file for visualization"
    ),
):
    """Generate visualization from analysis results."""
    try:
        # Load analysis results
        with open(input_file) as f:
            data = json.load(f)

        # Generate visualization
        generator = MermaidGenerator()
        html_content = generator.generate_html(data)

        with open(output, "w") as f:
            f.write(html_content)

        console.print(f"\n[green]Visualization generated at {output}")

    except Exception as e:
        console.print(f"[red]Error generating visualization: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
