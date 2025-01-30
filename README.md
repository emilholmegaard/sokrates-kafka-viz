# Sokrates Kafka Visualization Tool

A tool for visualizing Kafka microservices architecture using static code analysis.

## Features

Current implemented features:
- Service discovery through static code analysis
- Basic schema support:
  - Avro schemas (implemented)
  - JSON Schema (implemented)
  - Additional formats planned (see issues #22)
- Kafka topic dependency mapping
- Interactive visualization of service relationships
- Configurable analysis rules
- Basic state persistence
- Analysis resume capability

## Installation

```bash
pip install sokrates-kafka-viz
```

## Usage

1. Create a configuration file named `kafka_viz_config.yaml` in your project root:

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

state:
  enabled: true
  persistence_dir: ./.kafka_viz_state
  checkpoint_interval: 300  # seconds
  save_on_error: true

output:
  format: json  # Currently only JSON is supported
  path: ./analysis_output
  include_details: true
  group_by: ['service', 'topic']

logging:
  level: INFO
  file: kafka_viz.log
```

2. Run the analysis:

```bash
sokrates-kafka-viz analyze
```

Or specify a custom config file:

```bash
sokrates-kafka-viz analyze -c my_config.yaml
```

3. Managing Analysis State:

List available checkpoints:
```bash
sokrates-kafka-viz list-checkpoints
```

Resume from last checkpoint:
```bash
sokrates-kafka-viz analyze --resume
```

## Analysis Output

The tool generates a detailed analysis of your Kafka-based microservices architecture:

- Service dependencies
- Topic producers and consumers
- Message schema compatibility (for supported formats)
- Service interaction patterns
- Analysis progress and checkpoints

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

## Contributing

Contributions are welcome! Please check out our [Contributing Guide](CONTRIBUTING.md) for guidelines.

## Development Status

For current development status and planned features, see our [Development Roadmap](https://github.com/emilholmegaard/sokrates-kafka-viz/issues/51).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.