# Kafka Visualization Tool

A tool for visualizing Kafka microservices architecture using static code analysis.

## Features

Current implemented features:
- Service discovery through static code analysis
- Basic schema support:
  - Avro schemas (implemented)
  - JSON Schema (implemented)
  - Additional formats planned (see issues #22)
- Kafka topic dependency mapping
- Multiple visualization types:
  - Interactive React-based visualization
  - Mermaid diagrams
  - Simple HTML outputs
- Configurable analysis rules
- Basic state persistence
- Analysis resume capability

## Installation

```bash
pip install kafka-viz
```

## Usage

The tool provides two main commands: `analyze` and `visualize`.

### Analyze Command

Analyze a directory containing microservices source code:

```bash
kafka-viz analyze SOURCE_DIR [OPTIONS]

Arguments:
  SOURCE_DIR  Directory containing microservices source code [required]

Options:
  --output PATH         Output file for analysis results [default: analysis_output.json]
  --include-tests      Include test files in analysis [default: False]
  --verbose, -v        Enable verbose logging
  --help              Show this message and exit.
```

Example:
```bash
kafka-viz analyze ./services --output my-analysis.json
```

### Visualize Command

Generate a visualization from analysis results:

```bash
kafka-viz visualize INPUT_FILE [OPTIONS]

Arguments:
  INPUT_FILE  JSON file containing analysis results [required]

Options:
  --output PATH        Output directory for visualization [default: kafka_visualization]
  --type, -t TEXT      Type of visualization to generate (react, mermaid, simple)
  --list, -l           List available visualization types
  --help               Show this message and exit.
```

Example with specific visualization type:
```bash
kafka-viz visualize my-analysis.json --type react
```

### Info Command

View information about available visualizations:

```bash
kafka-viz info
```

## Visualization Types

The tool supports multiple visualization types:

1. **React Interactive** (`--type react`)
   - Interactive D3.js visualization with React UI
   - Shows services, topics, and their relationships
   - Includes detailed sidebar with additional information
   - Supports filtering, zooming, and panning

2. **Mermaid Diagram** (`--type mermaid`)
   - Simple Mermaid.js flowchart diagram
   - Shows services, topics, and their relationships
   - Lightweight and embeddable

3. **Simple HTML** (`--type simple`)
   - Basic HTML visualization with minimal dependencies
   - Shows services, topics, and their relationships

## Configuration

For custom analysis configuration, create a `kafka_viz_config.yaml` in your project root:

```yaml
analyzers:
  service:
    enabled: true
    include_tests: false
    paths:
      - ./src
      - ./services
    exclude_patterns:
      - '**/test/**'
      - '**/mock/**'
  
  schemas:
    enabled: true
    detectors:
      - avro
      - json
    schema_registry:  # Coming soon, see issue #26
      url: http://localhost:8081
      cache_schemas: true
      timeout_seconds: 30
  
  kafka:
    enabled: true
    topics_patterns:
      - '^app\\.'
      - '^service\\.'
    exclude_patterns:
      - '^_internal\\.'
    broker_config:
      bootstrap_servers: 'localhost:9092'
      security_protocol: 'PLAINTEXT'

output:
  format: json  # Currently only JSON is supported
  path: ./analysis_output
  include_details: true
  group_by: ['service', 'topic']

logging:
  level: INFO
  file: kafka_viz.log

# Visualization configuration
visualizations:
  default: react  # Default visualization type
  types:
    react:
      enabled: true
      name: "React Interactive"
      description: "Interactive D3.js visualization with React UI"
    mermaid:
      enabled: true
      name: "Mermaid Diagram"
      description: "Simple Mermaid.js flowchart diagram"
    simple:
      enabled: true
      name: "Simple HTML"
      description: "Basic HTML visualization"
```

## Analysis Output

The tool generates a detailed analysis of your Kafka-based microservices architecture:

- Service dependencies
- Topic producers and consumers
- Message schema compatibility (for supported formats)
- Service interaction patterns
- Schema evolution tracking
- Analysis progress tracking

Results are saved in the specified output directory in JSON format.

## Schema Support

The tool currently supports:

1. Avro Schemas
   - Standard Avro schema definitions
   - Local file parsing
   - Basic schema validation

2. JSON Schema
   - Draft-07 support
   - Schema references
   - Basic validation

Additional schema support is planned (see issue #22) for:
- Protocol Buffers
- CloudEvents
- Apache Parquet
- Custom formats

## State Persistence

The tool provides basic state management:
- File-based state storage
- Checkpoint/resume capability
- Progress tracking
- Emergency state saves on errors

## Language Support

Current language analyzer support:
- Java (basic implementation)
- Python (planned, see issue #15)
- TypeScript/JavaScript (planned, see issue #16)

## Extending the Tool

### Creating Custom Analyzers

You can create custom analyzers by implementing the `BaseAnalyzer` interface:

```python
from kafka_viz.core.analyzer import BaseAnalyzer
from kafka_viz.core.config import Config

class CustomAnalyzer(BaseAnalyzer):
    async def analyze(self, config: Config) -> Any:
        # Implement your analysis logic here
        pass
```

Then register your analyzer with the analysis runner:

```python
from kafka_viz.core.runner import AnalysisRunner

runner = AnalysisRunner(config)
runner.register_analyzer(CustomAnalyzer())
```

### Creating Custom Visualization Generators

You can create custom visualization generators by extending the `BaseGenerator` class:

```python
from kafka_viz.visualization import BaseGenerator
from pathlib import Path
from typing import Dict, Any

class CustomVisualizer(BaseGenerator):
    def __init__(self):
        super().__init__()
        self.name = "Custom Visualization"
        self.description = "My custom visualization type"
        
    def generate_html(self, data: Dict[str, Any]) -> str:
        # Generate HTML content
        return "<html>...</html>"
        
    def generate_output(self, data: Dict[str, Any], file_path: Path) -> None:
        # Generate visualization files
        html = self.generate_html(data)
        with open(file_path / "custom_viz.html", "w") as f:
            f.write(html)
```

Then register your visualization generator with the factory:

```python
from kafka_viz.visualization import visualization_factory

visualization_factory.register_generator("custom", CustomVisualizer)
```

## Troubleshooting

Common issues and solutions:

1. Schema Detection
   - Ensure schema files are in supported formats (currently Avro and JSON Schema)
   - Check file permissions for schema directories
   - Verify schema file extensions (.avsc for Avro, .json for JSON Schema)

2. Service Analysis
   - Check if source directories are correctly specified
   - Ensure correct file permissions
   - Verify language-specific patterns match your codebase

3. Visualization
   - Check if output directory is writable
   - Ensure input JSON file is properly formatted
   - Verify all referenced files exist

## Contributing

Contributions are welcome! Please check out our [Contributing Guide](CONTRIBUTING.md) for guidelines.

## Development Status

For current development status and planned features, see our [Development Roadmap](https://github.com/emilholmegaard/sokrates-kafka-viz/issues/51).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
