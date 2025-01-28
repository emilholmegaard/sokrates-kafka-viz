"""Command-line interface for Kafka visualization tool."""
from pathlib import Path
import typer
from rich.console import Console
from rich.progress import Progress

from .analyzers.kafka_analyzer import KafkaAnalyzer
from .analyzers.service_analyzer import ServiceAnalyzer
from .visualization.mermaid import MermaidGenerator
from .models import ServiceCollection

app = typer.Typer()
console = Console()

@app.command()
def analyze(
    source_dir: Path = typer.Argument(
        ...,
        help="Directory containing microservices source code",
        exists=True,
        dir_okay=True,
        resolve_path=True
    ),
    output: Path = typer.Option(
        "analysis_output.json",
        help="Output file for analysis results"
    ),
    include_tests: bool = typer.Option(
        False,
        help="Include test files in analysis"
    )
):
    """Analyze Kafka usage in a microservices codebase."""
    try:
        # Initialize analyzers
        service_analyzer = ServiceAnalyzer()
        kafka_analyzer = KafkaAnalyzer()
        services = ServiceCollection()

        with Progress() as progress:
            # First pass: identify services
            task = progress.add_task("Identifying services...", total=None)
            for service in service_analyzer.find_services(source_dir):
                services.add_service(service)
            progress.remove_task(task)

            # Second pass: analyze Kafka usage
            task = progress.add_task(
                "Analyzing services...",
                total=len(services.services)
            )
            for service in services.services.values():
                kafka_analyzer.analyze_service(service)
                progress.advance(task)

        # Save results
        result = {
            "services": {
                name: {
                    "path": str(svc.root_path),
                    "language": svc.language,
                    "topics": {
                        topic.name: {
                            "producers": list(topic.producers),
                            "consumers": list(topic.consumers)
                        } for topic in svc.topics.values()
                    }
                } for name, svc in services.services.items()
            }
        }

        import json
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)

        console.print(f"\n[green]Analysis complete! Results written to {output}")

    except Exception as e:
        console.print(f"[red]Error during analysis: {e}")
        raise typer.Exit(1)

@app.command()
def visualize(
    input_file: Path = typer.Argument(
        ...,
        help="JSON file containing analysis results",
        exists=True
    ),
    output: Path = typer.Option(
        "architecture.html",
        help="Output HTML file for visualization"
    )
):
    """Generate visualization from analysis results."""
    try:
        # Load analysis results
        import json
        with open(input_file) as f:
            data = json.load(f)

        # Generate visualization
        generator = MermaidGenerator()
        html_content = generator.generate_html(data)

        with open(output, 'w') as f:
            f.write(html_content)

        console.print(f"\n[green]Visualization generated at {output}")

    except Exception as e:
        console.print(f"[red]Error generating visualization: {e}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()