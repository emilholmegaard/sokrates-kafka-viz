"""
Command Line Interface for Kafka-Viz.
"""
import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from .analyzers.analyzer_manager import AnalyzerManager
from .visualization.factory import visualization_factory

app = typer.Typer()
console = Console()

# Configure logging
logger = logging.getLogger(__name__)


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
    logger.info(f"Starting analysis of {source_dir}")
    logger.debug(f"Output will be written to {output}")
    logger.debug(f"Include tests: {include_tests}")

    try:
        # Initialize analyzer manager
        analyzer_manager = AnalyzerManager()

        with Progress() as progress:
            # First pass: identify services
            task = progress.add_task("Identifying services...", total=None)
            services = analyzer_manager.discover_services(source_dir)
            progress.remove_task(task)

            if not services.services:
                logger.warning("No services were discovered in the source directory")
                raise typer.Exit(1)

            logger.info(f"Discovered {len(services.services)} services")
            for service_name in services.services:
                logger.debug(f"Found service: {service_name}")

            # Second pass: analyze schemas
            task = progress.add_task(
                "Analyzing schemas...", total=len(services.services)
            )
            for service in services.services.values():
                logger.debug(f"Analyzing schemas for service: {service.name}")
                analyzer_manager.analyze_schemas(service)
                if service.schemas:
                    logger.debug(
                        f"Found {len(service.schemas)} schemas in {service.name}"
                    )
                progress.advance(task)
            progress.remove_task(task)

            # Third pass: analyze source files
            task = progress.add_task(
                "Analyzing source files...", total=len(services.services)
            )
            for service in services.services.values():
                logger.debug(
                    f"Starting source file analysis for service: {service.name}"
                )
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

        # Save analysis results
        logger.info("Saving analysis results...")
        analyzer_manager.save_output(services, output, include_debug=verbose)

        # Print summary
        console.print(
            f"[green]Analysis complete! Results written to {output}"
        )
        console.print(
            "Analysis Summary:"
        )
        console.print(f"- Total services analyzed: {len(services.services)}")
        total_topics = sum(
            len(service.topics) for service in services.services.values()
        )
        total_schemas = sum(
            len(service.schemas) for service in services.services.values()
        )
        console.print(f"- Total topics found: {total_topics}")
        console.print(f"- Total schemas found: {total_schemas}")

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
        None, "--type", "-t", help="Type of visualization to generate"
    ),
    list_visualizations: bool = typer.Option(
        False, "--list", "-l", help="List available visualization types"
    ),
):
    """Generate visualization from analysis results.
    
    This command generates visual representations of the Kafka communication
    patterns found in the analysis results. Different visualization types
    are available, such as interactive React-based visualizations, Mermaid
    diagrams, and simple HTML outputs.
    """
    # List available visualizations if requested
    available_vis = visualization_factory.get_available_generators()
    
    if list_visualizations:
        console.print("[bold]Available Visualization Types:[/bold]")
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("ID", style="dim")
        table.add_column("Name")
        table.add_column("Description")
        
        for vis_id, vis_info in available_vis.items():
            table.add_row(
                vis_id,
                vis_info["name"],
                vis_info["description"]
            )
        
        console.print(table)
        return

    # If no visualization type specified, use interactive selection
    if not visualization_type:
        options = list(available_vis.keys())
        if not options:
            console.print("[red]No visualization types available.")
            raise typer.Exit(1)
        
        console.print("[bold]Select visualization type:[/bold]")
        for i, vis_id in enumerate(options):
            console.print(f"[{i+1}] {available_vis[vis_id]['name']} - {available_vis[vis_id]['description']}")
        
        choice = 0
        while choice < 1 or choice > len(options):
            try:
                choice = int(typer.prompt("Enter number", default="1"))
                if choice < 1 or choice > len(options):
                    console.print(f"[red]Please enter a number between 1 and {len(options)}[/red]")
            except ValueError:
                console.print("[red]Please enter a valid number[/red]")
        
        visualization_type = options[choice - 1]

    # Check if the specified visualization type exists
    if visualization_type not in available_vis:
        console.print(f"[red]Error: Visualization type '{visualization_type}' not found. Use --list to see available types.[/red]")
        raise typer.Exit(1)

    try:
        # Load analysis results
        with open(input_file) as f:
            data = json.load(f)

        # Get the appropriate generator for the selected visualization type
        generator = visualization_factory.create_generator(visualization_type)
        if not generator:
            console.print(f"[red]Error: Visualization generator '{visualization_type}' not found.[/red]")
            raise typer.Exit(1)
            
        # Generate visualization
        console.print(f"Generating [bold]{available_vis[visualization_type]['name']}[/bold] visualization...")
        
        # Create output directory
        output_dir = Path(output)
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
            
        # Generate output
        generator.generate_output(data, output_dir)
        
        console.print(f"[green]Visualization generated at {output_dir}[/green]")

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
    
    available_vis = visualization_factory.get_available_generators()
    
    console.print("[bold]Kafka Visualization Options:[/bold]")
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Description")
    
    for vis_id, vis_info in available_vis.items():
        table.add_row(
            vis_id,
            vis_info["name"],
            vis_info["description"]
        )
    
    console.print(table)
    console.print("\n[bold]Usage:[/bold]")
    console.print("1. First analyze your codebase with: [cyan]kafka-viz analyze [PATH][/cyan]")
    console.print("2. Then visualize the results with: [cyan]kafka-viz visualize [RESULTS_FILE][/cyan]")
    console.print("\nUse [bold]--type TYPE[/bold] to select a specific visualization type.")
    console.print("Use [bold]--list[/bold] to see all available visualization types.")


if __name__ == "__main__":
    app()
