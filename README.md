# Kafka Visualization Tool

A tool for visualizing Kafka microservices architecture using static code analysis.

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
  --output PATH  Output HTML file for visualization [default: architecture.html]
  --help       Show this message and exit.
```

Example:
```bash
kafka-viz visualize my-analysis.json --output architecture.html
```

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
```

[Rest of the README content remains the same...]