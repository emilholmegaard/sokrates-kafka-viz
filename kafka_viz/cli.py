import click
import logging
from pathlib import Path
from .analyzers import JavaAnalyzer
from .graphviz import GraphvizWriter
from .logging_config import configure_logging

@click.command()
@click.argument('source_dir', type=click.Path(exists=True))
@click.option('--output', '-o', default='kafka-topics.dot', help='Output file name')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(source_dir: str, output: str, verbose: bool):
    """Analyze Java source files for Kafka topics and create a visualization."""
    # Configure logging
    logger = configure_logging(verbose)
    
    try:
        logger.info(f"Starting analysis of directory: {source_dir}")
        source_path = Path(source_dir)
        analyzer = JavaAnalyzer()
        all_topics = []

        # Find all Java files
        java_files = list(source_path.glob('**/*.java'))
        logger.info(f"Found {len(java_files)} Java files to analyze")

        # Analyze each file
        for file in java_files:
            try:
                file_topics = analyzer.analyze_file(file)
                all_topics.extend(file_topics)
            except Exception as e:
                logger.error(f"Error analyzing file {file}: {str(e)}")

        logger.info(f"Analysis complete. Found {len(all_topics)} topics in total")
        
        # Write the graph
        writer = GraphvizWriter()
        writer.write_graph(all_topics, output)
        logger.info(f"Graph written to {output}")

    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise click.ClickException(str(e))

if __name__ == '__main__':
    main()
