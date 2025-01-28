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
- Graphviz
- Node.js 14+ (for the web viewer)

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
python scripts/analyze.py --source-dir /path/to/your/services
```

2. Generate visualization:
```bash
python scripts/visualize.py --input analysis_output.json --output architecture.html
```

3. View the results:
```bash
python -m http.server 8000
# Open http://localhost:8000/architecture.html in your browser
```

## Example Output

The tool generates an interactive visualization showing:
- Microservices (as nodes)
- Kafka topics (as intermediary nodes)
- Producer/consumer relationships (as directed edges)
- Avro schema relationships

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