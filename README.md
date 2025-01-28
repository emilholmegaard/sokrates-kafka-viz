# Kafka Visualization Tool

A tool for analyzing and visualizing Kafka-based microservices architecture.

## Features

- Detects Kafka producers and consumers in source code
- Identifies message schemas (Avro and DTOs)
- Shows service dependencies through Kafka topics
- Supports multiple programming languages:
  - Java/Kotlin/Scala (including Spring Cloud Stream)
  - Python
  - C#
  - JavaScript/TypeScript

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/emilholmegaard/sokrates-kafka-viz.git
cd sokrates-kafka-viz

# Install with development dependencies
pip install -e ".[dev]"

# Or install without development dependencies
pip install -e "."
```

### Prerequisites

- Python 3.8 or later
- Graphviz (for visualization)
  - Ubuntu/Debian: `sudo apt-get install graphviz`
  - macOS: `brew install graphviz`
  - Windows: Download from [Graphviz Downloads](https://graphviz.org/download/)

## Usage

```bash
# Analyze a directory containing microservices
kafka-viz analyze /path/to/services

# Generate visualization
kafka-viz visualize --output architecture.html

# Get help
kafka-viz --help
```

## Development

```bash
# Run tests
pytest

# Run linting
flake8 kafka_viz tests
black kafka_viz tests --check
isort kafka_viz tests --check

# Run type checking
mypy kafka_viz
```

## License

MIT