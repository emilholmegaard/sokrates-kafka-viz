# Kafka Visualization Tool

A tool for analyzing and visualizing Kafka-based microservices architecture.

## Features

- Detects Kafka producers and consumers in source code
- Identifies message schemas (Avro and DTOs)
- Shows service dependencies through Kafka topics
- Supports multiple programming languages:
  - Java/Kotlin/Scala
  - Python
  - C#
  - JavaScript/TypeScript

## Installation

```bash
pip install kafka-viz
```

## Usage

```bash
# Analyze a directory containing microservices
kafka-viz analyze /path/to/services

# Generate visualization
kafka-viz visualize --output architecture.html
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT
