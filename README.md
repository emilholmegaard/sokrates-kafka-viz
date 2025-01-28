# Sokrates Kafka Visualization Tool

A tool for visualizing Kafka microservices architecture using static code analysis.

## Features

- Service discovery through static code analysis
- Avro schema analysis and validation
- Kafka topic dependency mapping
- Interactive visualization of service relationships
- Configurable analysis rules

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
  
  avro:
    enabled: true
    schema_registry: http://localhost:8081
    cache_schemas: true
    timeout_seconds: 30
  
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

## Analysis Output

The tool generates a detailed analysis of your Kafka-based microservices architecture:

- Service dependencies
- Topic producers and consumers
- Message schema compatibility
- Service interaction patterns

Results are saved in the specified output directory in the chosen format (JSON, YAML, or visualization).

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
