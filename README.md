# Sokrates Kafka Viz

A tool for visualizing Kafka microservices architecture through static code analysis. This tool helps you understand the topology and data flow of your Kafka-based microservices system by analyzing source code and Avro schemas.

## Features

- Extracts Kafka topics from source code
- Identifies producer/consumer relationships
- Parses Avro schemas
- Generates visual diagrams of your architecture
- Supports multiple programming languages (Java, Python, Node.js)

## Prerequisites

- Python 3.8+

## Installation

```bash
# Clone the repository
git clone https://github.com/emilholmegaard/sokrates-kafka-viz.git
cd sokrates-kafka-viz

# Install Python dependencies
pip install -r requirements.txt
```

## Usage

1. Analyze your codebase:
```bash
# Basic usage
python scripts/analyze.py /path/to/your/services

# With custom output file
python scripts/analyze.py /path/to/your/services --output custom_output.json
```

2. Generate visualization:
```bash
# Basic usage (output will be architecture.html)
python scripts/visualize.py analysis_output.json

# With custom output file
python scripts/visualize.py analysis_output.json --output custom_viz.html
```

3. View the results:
```bash
# Start a simple HTTP server
python -m http.server 8000

# Open your browser and navigate to:
# http://localhost:8000/architecture.html
```

## Example Output

The tool generates an interactive visualization showing:
- Microservices (as green nodes)
- Kafka topics (as blue nodes)
- Producer/consumer relationships (as directed edges)
- Avro schema relationships (as purple nodes)

## How It Works

The tool uses regex patterns to identify:
- Kafka producers and consumers in your code
- Topic names and configurations
- Avro schema definitions
- Service relationships

Supported patterns include:
- `@KafkaProducer`, `@KafkaListener` (Java/Spring)
- `KafkaProducer`, `KafkaConsumer` (Python)
- `kafka.producer`, `kafka.consumer` (Node.js)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT