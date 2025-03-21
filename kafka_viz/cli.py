"""
Command Line Interface for Kafka-Viz.

This module provides the CLI commands for analyzing Kafka communication patterns
in a microservices architecture and generating visualizations.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from .analyzers.analyzer_manager import AnalyzerManager
from .visualization.factory import visualization_factory
from .visualization.index_generator import IndexGenerator

# Initialize Typer app and console
app = typer.Typer()
console = Console()

# Configure logging
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool) -> None:
    """Set up logging configuration.

    Args:
        verbose: Whether to enable verbose logging
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def is_source_file(file_path: Path) -> bool:
    """Check if a file is a source file that should be analyzed.

    Args:
        file_path: Path to check

    Returns:
        bool: True if the file should be analyzed, False otherwise
    """
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
        "_sokrates",
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


def discover_services(
    analyzer_manager: AnalyzerManager, source_dir: Path, progress: Progress
) -> Any:
    """Discover services in the source directory.

    Args:
        analyzer_manager: Analyzer manager instance
        source_dir: Directory to analyze
        progress: Progress instance for tracking

    Returns:
        Any: Service discovery results
    """
    task = progress.add_task("Identifying services...", total=None)
    services = analyzer_manager.discover_services(source_dir)
    progress.remove_task(task)

    if not services.services:
        logger.warning("No services were discovered in the source directory")
        raise typer.Exit(1)

    logger.info(f"Discovered {len(services.services)} services")
    for service_name in services.services:
        logger.debug(f"Found service: {service_name}")

    return services


def analyze_schemas(
    analyzer_manager: AnalyzerManager, services: Any, progress: Progress
) -> None:
    """Analyze schemas in the discovered services.

    Args:
        analyzer_manager: Analyzer manager instance
        services: Service discovery results
        progress: Progress instance for tracking
    """
    task = progress.add_task("Analyzing schemas...", total=len(services.services))

    for service in services.services.values():
        logger.debug(f"Analyzing schemas for service: {service.name}")
        analyzer_manager.analyze_schemas(service)
        if service.schemas:
            logger.debug(f"Found {len(service.schemas)} schemas in {service.name}")
        progress.advance(task)

    progress.remove_task(task)


def analyze_source_files(
    analyzer_manager: AnalyzerManager, services: Any, progress: Progress, verbose: bool
) -> None:
    """Analyze source files in the discovered services.

    Args:
        analyzer_manager: Analyzer manager instance
        services: Service discovery results
        progress: Progress instance for tracking
        verbose: Whether to enable verbose logging
    """
    task = progress.add_task("Analyzing source files...", total=len(services.services))

    for service in services.services.values():
        logger.debug(f"Starting source file analysis for service: {service.name}")
        files_analyzed = 0
        topics_found = 0

        for file_path in service.root_path.rglob("*"):
            if file_path.is_file() and is_source_file(file_path):
                files_analyzed += 1
                try:
                    topics = analyzer_manager.analyze_file(file_path, service)
                    if topics:
                        service.topics.update(topics)
                        topics_found += len(topics)
                        logger.debug(
                            f"Found {len(topics)} topics in "
                            f"{file_path.relative_to(service.root_path)}"
                        )
                except Exception as e:
                    if verbose:
                        logger.warning(f"Error analyzing file {file_path}: {e}")

        logger.debug(
            f"Service {service.name} analysis complete: "
            f"analyzed {files_analyzed} files, "
            f"found {topics_found} topics"
        )
        progress.advance(task)

    progress.remove_task(task)


def print_analysis_summary(services: Any) -> None:
    """Print a summary of the analysis results.

    Args:
        services: Service discovery results
    """
    console.print("Analysis Summary:")
    console.print(f"- Total services analyzed: {len(services.services)}")

    total_topics = sum(len(service.topics) for service in services.services.values())
    total_schemas = sum(len(service.schemas) for service in services.services.values())

    console.print(f"- Total topics found: {total_topics}")
    console.print(f"- Total schemas found: {total_schemas}")


def load_analysis_data(input_file: Path) -> Dict[str, Any]:
    """Load analysis data from a JSON file.

    Args:
        input_file: Path to the JSON file

    Returns:
        dict: Analysis data
    """
    try:
        with open(input_file) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load analysis data: {e}")
        raise typer.Exit(1)


def display_visualization_types(available_vis: Dict[str, Dict[str, Any]]) -> None:
    """Display available visualization types in a table.

    Args:
        available_vis: Available visualization types
    """
    console.print("[bold]Available Visualization Types:[/bold]")
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Description")

    for vis_id, vis_info in available_vis.items():
        table.add_row(vis_id, vis_info["name"], vis_info["description"])

    console.print(table)


def generate_single_visualization(
    data: Dict[str, Any], vis_type: str, output_dir: Path
) -> Optional[Dict[str, Any]]:
    """Generate a single visualization.

    Args:
        data: Analysis data
        vis_type: Visualization type
        output_dir: Output directory

    Returns:
        Optional[Dict[str, Any]]: Visualization metadata if successful
    """
    # Get the generator for the selected visualization type
    available_vis = visualization_factory.get_available_generators()
    generator = visualization_factory.create_generator(vis_type)

    if not generator:
        console.print(
            f"[red]Error: Visualization generator '{vis_type}' not found.[/red]"
        )
        return None

    # Create subdirectory for this visualization
    vis_dir = output_dir / vis_type
    if not vis_dir.exists():
        vis_dir.mkdir(parents=True)

    # Generate output
    try:
        generator.generate_output(data, vis_dir)

        # Get the main output file from the generator
        output_file = generator.get_main_output_file()

        # Return metadata for this visualization
        return {
            "name": available_vis[vis_type]["name"],
            "description": available_vis[vis_type]["description"],
            "path": f"{vis_type}/{output_file}",
            "type": vis_type,
        }
    except Exception as e:
        logger.error(f"Error generating {vis_type} visualization: {e}")
        return None


def generate_all_visualizations(data: Dict[str, Any], output_dir: Path) -> None:
    """Generate all available visualizations.

    Args:
        data: Analysis data
        output_dir: Output directory
    """
    # Get all available generators
    generators = visualization_factory.create_all_generators(list())

    # Track successful visualizations for the index
    vis_links = []

    with Progress() as progress:
        # Create a task for each visualization type
        task = progress.add_task("Generating visualizations...", total=len(generators))

        # Generate each visualization
        for vis_type, generator in generators.items():
            progress.update(task, description=f"Generating {vis_type} visualization...")

            try:
                # Create subdirectory for this visualization
                vis_dir = output_dir / vis_type
                if not vis_dir.exists():
                    vis_dir.mkdir(parents=True)

                # Generate the visualization
                generator.generate_output(data, vis_dir)

                # Get the main output file from the generator
                output_file = generator.get_main_output_file()

                # Add to successful visualizations
                available_vis = visualization_factory.get_available_generators()
                vis_links.append(
                    {
                        "name": available_vis[vis_type]["name"],
                        "description": available_vis[vis_type]["description"],
                        "path": f"{vis_type}/{output_file}",
                        "type": vis_type,
                    }
                )

                progress.update(task, advance=1)

            except Exception as e:
                logger.error(f"Error generating {vis_type} visualization: {e}")
                progress.update(task, advance=1)

    # Generate the index page
    if vis_links:
        console.print("Generating index page...")
        index_generator = IndexGenerator()
        index_generator.generate_output(data, output_dir, vis_links)


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
    """Analyze Kafka usage in a microservices codebase.

    This command analyzes a directory containing microservices source code to
    discover services, Kafka topics, and schema information. The results are
    saved to a JSON file that can be visualized using the `visualize` command.
    """
    # Set up logging
    setup_logging(verbose)
    logger.info(f"Starting analysis of {source_dir}")
    logger.debug(f"Output will be written to {output}")
    logger.debug(f"Include tests: {include_tests}")

    try:
        # Initialize analyzer manager
        analyzer_manager = AnalyzerManager()

        with Progress() as progress:
            # First pass: identify services
            services = discover_services(analyzer_manager, source_dir, progress)

            # Second pass: analyze schemas
            analyze_schemas(analyzer_manager, services, progress)

            # Third pass: analyze source files
            analyze_source_files(analyzer_manager, services, progress, verbose)

        # Save analysis results
        logger.info("Saving analysis results...")
        analyzer_manager.save_output(services, output, include_debug=verbose)

        # Print summary
        console.print(f"[green]Analysis complete! Results written to {output}")
        print_analysis_summary(services)

    except Exception as e:
        console.print(f"[red]Error during analysis: {e}")
        logger.exception("Analysis failed with error")
        raise typer.Exit(1)


@app.command()
def visualize(
    input_file: Path = typer.Argument(
        ..., help="JSON file containing analysis results", exists=True
    ),
    output: Path = typer.Option(
        "kafka_visualization", help="Output directory for visualization"
    ),
    visualization_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Type of visualization to generate (or 'all' for all types)",
    ),
    list_visualizations: bool = typer.Option(
        False, "--list", "-l", help="List available visualization types"
    ),
    all_visualizations: bool = typer.Option(
        False, "--all", "-a", help="Generate all visualization types"
    ),
):
    """Generate visualization from analysis results.

    This command generates visual representations of the Kafka communication
    patterns found in the analysis results. Different visualization types
    are available, such as interactive React-based visualizations, Mermaid
    diagrams, and simple HTML outputs.

    By default, it generates all available visualization types with an index page.
    """
    # Set up logging
    setup_logging(False)

    # Get available visualization types
    available_vis = visualization_factory.get_available_generators()

    # List visualizations if requested
    if list_visualizations:
        display_visualization_types(available_vis)
        return

    # Check if we should generate all visualizations
    if all_visualizations or visualization_type == "all":
        visualization_type = "all"

    # If no visualization type specified, default to "all" (no interactive selection)
    if not visualization_type:
        visualization_type = "all"

    try:
        # Load analysis results
        data = load_analysis_data(input_file)

        # Create base output directory
        if not output.exists():
            output.mkdir(parents=True)

        # Generate visualizations
        if visualization_type == "all":
            # Generate all visualization types
            console.print("[bold]Generating all visualization types...[/bold]")
            generate_all_visualizations(data, output)
            console.print(f"[green]All visualizations generated at {output}[/green]")
            console.print(
                f"[green]Open {output}/index.html to access the visualizations[/green]"
            )
        else:
            # Generate a single visualization type
            if visualization_type not in available_vis:
                console.print(
                    f"[red]Error: Visualization type '{visualization_type}' not found. "
                    "Use --list to see available types.[/red]"
                )
                raise typer.Exit(1)

            console.print(
                f"Generating [bold]{available_vis[visualization_type]['name']}[/bold] "
                "visualization..."
            )
            result = generate_single_visualization(data, visualization_type, output)

            if result:
                vis_dir = output / visualization_type
                console.print(f"[green]Visualization generated at {vis_dir}[/green]")
                console.print(
                    f"[green]Open {vis_dir}/{result['path'].split('/')[-1]} "
                    "to view the visualization[/green]"
                )
            else:
                console.print("[red]Failed to generate visualization.[/red]")
                raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error generating visualization: {e}[/red]")
        logger.exception("Visualization generation failed")
        raise typer.Exit(1)


@app.command()
def info():
    """Show information about available visualizations and features.

    This command displays information about the available visualization
    types and other features of the Kafka-Viz tool.
    """
    # Get available visualization types
    available_vis = visualization_factory.get_available_generators()

    # Display available visualization types
    console.print("[bold]Kafka Visualization Options:[/bold]")
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Description")

    for vis_id, vis_info in available_vis.items():
        table.add_row(vis_id, vis_info["name"], vis_info["description"])

    console.print(table)
    console.print("\n[bold]Usage:[/bold]")
    console.print(
        "1. First analyze your codebase with: [cyan]kafka-viz analyze [PATH][/cyan]"
    )
    console.print(
        "2. Then visualize the results with: [cyan]kafka-viz visualize [RESULTS_FILE][/cyan]"
    )
    console.print(
        "\nBy default, all visualization types will be generated with an index page."
    )
    console.print(
        "Use [bold]--type TYPE[/bold] to select a specific visualization type."
    )
    console.print(
        "Use [bold]--all[/bold] or [bold]--type all[/bold] to explicitly generate all types."
    )
    console.print("Use [bold]--list[/bold] to see all available visualization types.")


if __name__ == "__main__":
    app()
