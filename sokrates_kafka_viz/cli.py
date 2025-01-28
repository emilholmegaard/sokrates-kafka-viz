import asyncio
import click
import logging
from pathlib import Path
from typing import Optional

from .core.config import Config
from .core.runner import AnalysisRunner
from .analyzers import ServiceAnalyzer, AvroAnalyzer, KafkaAnalyzer
from .core.errors import AnalysisError, ConfigurationError

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@click.group()
def cli():
    """Sokrates Kafka Visualization Tool"""
    pass

@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def analyze(config: Optional[Path], verbose: bool):
    """Run the analysis"""
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        if not config:
            config = Path('sokrates.yaml')
        
        if not config.exists():
            raise ConfigurationError(f'Configuration file not found: {config}')
        
        config_obj = Config.from_file(config)
        
        # Setup runner
        runner = AnalysisRunner(config_obj)
        
        # Register analyzers
        runner.register_analyzer(ServiceAnalyzer())
        runner.register_analyzer(AvroAnalyzer())
        runner.register_analyzer(KafkaAnalyzer())
        
        # Run analysis
        result = asyncio.run(runner.run())
        
        # Handle results
        if result.errors:
            logger.error('Analysis completed with errors:')
            for error in result.errors:
                logger.error(f'{error["analyzer"]}: {error["error"]}')
            return 1
        
        logger.info('Analysis completed successfully')
        return 0
        
    except (ConfigurationError, AnalysisError) as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.exception('Unexpected error occurred')
        return 1

if __name__ == '__main__':
    cli()