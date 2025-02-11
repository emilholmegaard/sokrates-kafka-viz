"""Command line interface for Kafka-Viz."""

import logging
import sys
from pathlib import Path
from typing import Optional

import rich_click as click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.traceback import install

from .analyzers.analyzer_manager import AnalyzerManager
from .models.service_collection import ServiceCollection
from .version import __version__

# Install rich traceback handler
install()

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)

logger = logging.getLogger("kafka_viz")
console = Console()


@click.group()
@click.version_option(__version__)
def app():
    """Kafka-Viz: Generate service dependency visualizations from Kafka usage."""
    pass


@app.command()
@click.argument(
    "source",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.argument(
    "output",
    type=click.Path(dir_okay=False, path_type=Path),
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging",
)
def analyze(source: Path, output: Path, verbose: bool, debug: bool) -> None:
    """Analyze source directory and generate visualization data.

    SOURCE is the directory containing microservices to analyze
    OUTPUT is the path where to save the analysis results
    """
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("kafka_viz").setLevel(logging.DEBUG)

    try:
        logger.info("Starting analysis...")
        source_dir = source.resolve()
        analyzer_manager = AnalyzerManager()

        # First pass: Discover services
        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Discovering services...", total=None)
            services = analyzer_manager.discover_services(source_dir)
            progress.update(task, completed=True)

        logger.info(f"Found {len(services.services)} services")
        if not services.services:
            logger.warning("No services found in directory")
            sys.exit(1)

        # Second pass: Analyze schemas
        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Analyzing schemas...", total=len(services.services))
            for service in services.services.values():
                analyzer_manager.analyze_schemas(service)
                progress.advance(task)

        # Third pass: Analyze source files for Kafka topics
        with Progress(
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            for service_name, service in services.services.items():
                file_count = len(service.source_files)
                if not file_count:
                    logger.debug(f"No source files found for service {service_name}")
                    continue

                task = progress.add_task(
                    f"Analyzing source files...",
                    total=file_count,
                )

                for source_file in service.source_files:
                    analyzer_manager.analyze_file(source_file, service)
                    progress.advance(task)

                logger.debug(
                    f"Service {service_name} analysis complete: "
                    f"analyzed {file_count} files, "
                    f"found {len(service.topics)} topics"
                )

        # Fourth pass: Analyze service dependencies
        analyzer_manager.analyze_service_dependencies()

        # Save results
        logger.info("Saving analysis results...")
        analyzer_manager.save_output(output_path=output, include_debug=verbose)

        logger.info(f"Analysis complete. Results saved to {output}")

    except Exception as e:
        logger.error("Analysis failed with error")
        raise click.ClickException(str(e))


@app.command()
@click.argument(
    "data",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to save the visualization",
)
@click.option(
    "--show/--no-show",
    default=True,
    help="Show the visualization in browser",
)
def visualize(data: Path, output: Optional[Path], show: bool) -> None:
    """Generate visualization from analysis data.

    DATA is the path to the analysis results JSON file
    """
    raise NotImplementedError("Visualization is not yet implemented")


if __name__ == "__main__":
    app()
