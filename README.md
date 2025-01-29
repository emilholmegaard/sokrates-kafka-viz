# Sokrates Kafka Visualization Tool

A tool for visualizing Kafka microservices architecture using static code analysis.

## Features

- Service discovery through static code analysis
- Comprehensive schema support:
  - Avro schemas
  - CloudEvents
  - Protocol Buffers
  - JSON Schema
  - Apache Parquet
  - Custom formats
- Kafka topic dependency mapping
- Interactive visualization of service relationships
- Configurable analysis rules
- Robust state persistence
- Analysis checkpointing and resume capability

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
      - cloudevents
      - protobuf
      - json
      - parquet
    schema_registry:
      url: http://localhost:8081
      cache_schemas: true
      timeout_seconds: 30
    custom_formats:
      - module: myapp.schemas
        class: CustomSchemaDetector
  
  kafka:
    enabled: true
    topics_patterns:
      - '^app\.'
      - '^service\.'
    exclude_patterns:
      - '^_internal\.'
    broker_config:
      bootstrap_servers: 'localhost:9092'
      security_protocol: 'PLAINTEXT'

state:
  enabled: true
  persistence_dir: ./.kafka_viz_state
  checkpoint_interval: 300  # seconds
  save_on_error: true

output:
  format: json
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

Use verbose output for debugging:

```bash
sokrates-kafka-viz analyze -v
```

3. Managing Analysis State:

List available checkpoints:
```bash
sokrates-kafka-viz list-checkpoints
```

Get state summary:
```bash
sokrates-kafka-viz state-summary
```

Resume from last checkpoint:
```bash
sokrates-kafka-viz analyze --resume
```

## Analysis Output

The tool generates a detailed analysis of your Kafka-based microservices architecture:

- Service dependencies
- Topic producers and consumers
- Message schema compatibility
- Service interaction patterns
- Schema evolution tracking
- Analysis progress and checkpoints

Results are saved in the specified output directory in the chosen format (JSON, YAML, or visualization).

## Schema Support

The tool supports multiple schema formats:

1. Avro Schemas
   - Standard Avro schema definitions
   - Schema Registry integration
   - Schema evolution tracking

2. CloudEvents
   - Standard CloudEvents format
   - Custom CloudEvents extensions
   - Event type validation

3. Protocol Buffers
   - .proto file parsing
   - Message type detection
   - Field validation

4. JSON Schema
   - Draft-07 support
   - Schema references
   - Custom vocabularies

5. Apache Parquet
   - Column definitions
   - Compression options
   - Type inference

6. Custom Formats
   - Pluggable schema detector interface
   - Custom validation rules
   - Format-specific options

## State Persistence

The tool provides robust state management:

- SQLite-based state storage
- Automatic checkpointing
- Resume capability
- Progress tracking
- Emergency state saves
- Schema caching

## Extending the Tool

You can create custom analyzers by implementing the `BaseAnalyzer` interface:

```python
from sokrates_kafka_viz.core.analyzer import BaseAnalyzer
from sokrates_kafka_viz.core.config import Config

class CustomAnalyzer(BaseAnalyzer):
    async def analyze(self, config: Config) -> Any:
        # Implement your analysis logic here
        pass
```

Then register your analyzer with the analysis runner:

```python
from sokrates_kafka_viz.core.runner import AnalysisRunner

runner = AnalysisRunner(config)
runner.register_analyzer(CustomAnalyzer())
```

## Contributing

Contributions are welcome! Please check out our [Contributing Guide](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.