"""Command line interface for Sokrates Kafka Visualization tool."""
import click
import yaml
from pathlib import Path
from typing import Optional
from .core.state import StateManager, AnalysisState
from .core.schemas import (
    SchemaRegistry, AvroSchemaDetector, CloudEventsDetector,
    ProtobufDetector, JSONSchema, ParquetSchema
)

def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)

@click.group()
def cli():
    """Sokrates Kafka Visualization Tool."""
    pass

@cli.command()
@click.option('-c', '--config', 'config_path',
              type=click.Path(exists=True, path_type=Path),
              default='kafka_viz_config.yaml',
              help='Path to configuration file')
@click.option('--resume/--no-resume', default=True,
              help='Resume from last saved state if available')
@click.option('-v', '--verbose', is_flag=True,
              help='Enable verbose output')
@click.option('--state-dir',
              type=click.Path(path_type=Path),
              default=Path('.kafka_viz_state'),
              help='Directory for state persistence')
def analyze(config_path: Path, resume: bool, verbose: bool, state_dir: Path):
    """Analyze Kafka services and generate visualization."""
    config = load_config(config_path)
    
    # Initialize state management
    state_manager = StateManager(state_dir)
    
    # Try to load previous state if resume is enabled
    initial_state = None
    if resume:
        initial_state = state_manager.load_latest_state()
        if initial_state:
            click.echo(f"Resuming analysis from previous state")
    
    # Initialize schema registry with configured detectors
    schema_detectors = []
    schema_config = config.get('analyzers', {}).get('schemas', {})
    
    if schema_config.get('enabled', True):
        enabled_detectors = schema_config.get('detectors', ['avro'])
        
        if 'avro' in enabled_detectors:
            schema_detectors.append(AvroSchemaDetector())
        if 'cloudevents' in enabled_detectors:
            schema_detectors.append(CloudEventsDetector())
        if 'protobuf' in enabled_detectors:
            schema_detectors.append(ProtobufDetector())
        # Add other detectors based on configuration
    
    registry = SchemaRegistry(detectors=schema_detectors)
    
    # Set up analysis runner with state management
    runner = AnalysisRunner(
        config=config,
        initial_state=initial_state,
        schema_registry=registry,
        state_manager=state_manager
    )
    
    try:
        runner.run()
    except Exception as e:
        click.echo(f"Error during analysis: {e}", err=True)
        # Save emergency state
        if hasattr(runner, 'current_state'):
            state_manager.save_state(runner.current_state)
        raise click.Abort()

@cli.command()
@click.option('--state-dir',
              type=click.Path(exists=True, path_type=Path),
              default=Path('.kafka_viz_state'),
              help='Directory containing state files')
def list_checkpoints(state_dir: Path):
    """List available analysis checkpoints."""
    state_manager = StateManager(state_dir)
    latest_state = state_manager.load_latest_state()
    
    if not latest_state:
        click.echo("No saved analysis states found.")
        return
    
    click.echo("\nAvailable checkpoints:")
    for idx, checkpoint in enumerate(latest_state.checkpoints, 1):
        click.echo(f"\n{idx}. {checkpoint.stage}")
        click.echo(f"   Timestamp: {checkpoint.timestamp}")
        click.echo(f"   Completed services: {len(checkpoint.completed_services)}")
        if checkpoint.metadata:
            click.echo("   Additional info:")
            for key, value in checkpoint.metadata.items():
                click.echo(f"   - {key}: {value}")

@cli.command()
@click.option('--state-dir',
              type=click.Path(exists=True, path_type=Path),
              default=Path('.kafka_viz_state'),
              help='Directory containing state files')
@click.option('--output',
              type=click.Path(path_type=Path),
              help='Output path for state summary')
def state_summary(state_dir: Path, output: Optional[Path]):
    """Generate summary of current analysis state."""
    state_manager = StateManager(state_dir)
    latest_state = state_manager.load_latest_state()
    
    if not latest_state:
        click.echo("No saved analysis states found.")
        return
    
    summary = {
        'timestamp': latest_state.timestamp.isoformat(),
        'services': {
            'analyzed': len([s for s in latest_state.services_analyzed.values() if s]),
            'pending': len([s for s in latest_state.services_analyzed.values() if not s])
        },
        'schemas': {
            'detected': len(latest_state.schemas_detected),
            'by_type': {}
        },
        'dependencies': len(latest_state.dependencies_mapped),
        'checkpoints': len(latest_state.checkpoints)
    }
    
    # Count schemas by type
    for schema_info in latest_state.schemas_detected.values():
        schema_type = schema_info.schema_type
        summary['schemas']['by_type'][schema_type] = \
            summary['schemas']['by_type'].get(schema_type, 0) + 1
    
    if output:
        with open(output, 'w') as f:
            yaml.dump(summary, f)
        click.echo(f"State summary written to {output}")
    else:
        click.echo("\nAnalysis State Summary:")
        click.echo(yaml.dump(summary, default_flow_style=False))

if __name__ == '__main__':
    cli()