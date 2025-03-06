# Extending Kafka-Viz Visualizations

This guide explains how to create custom visualization generators for Kafka-Viz.

## Visualization Architecture

Kafka-Viz uses a flexible architecture for generating visualizations:

1. **BaseGenerator**: Abstract base class that defines the interface for all visualization generators
2. **Visualization Factory**: Factory class that manages and creates visualization generators
3. **Resources**: Static templates and assets for visualizations
4. **Utils**: Utility functions for resource handling and common operations

## Creating a Custom Visualization Generator

To create a custom visualization generator:

1. Create a new class that extends `BaseGenerator`
2. Implement the required methods
3. Register your generator with the factory

### Step 1: Create a New Visualization Generator Class

Create a new file in the `kafka_viz/visualization` directory, e.g., `custom_viz.py`:

```python
from pathlib import Path
from typing import Dict, Any

from .base import BaseGenerator
from .utils import write_file

class CustomVisualizer(BaseGenerator):
    """Custom visualization generator."""
    
    def __init__(self):
        super().__init__()
        self.name = "Custom Visualization"
        self.description = "My custom visualization type"
    
    def generate_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML content for the visualization.
        
        Args:
            data: The parsed Kafka analysis data
            
        Returns:
            str: HTML content for the visualization
        """
        # Example: Generate a simple HTML table of services and topics
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Custom Kafka Visualization</title>
    <style>
        body { font-family: Arial, sans-serif; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Kafka Services and Topics</h1>
    <h2>Services</h2>
    <table>
        <tr><th>Service</th><th>Language</th></tr>
"""
        
        # Add services to the table
        services = data.get("services", {})
        for service_name, service_info in services.items():
            language = service_info.get("language", "unknown")
            html += f"<tr><td>{service_name}</td><td>{language}</td></tr>\n"
            
        html += """
    </table>
    <h2>Topics</h2>
    <table>
        <tr><th>Topic</th><th>Producers</th><th>Consumers</th></tr>
"""
        
        # Add topics to the table
        for service_name, service_info in services.items():
            for topic_name, topic_info in service_info.get("topics", {}).items():
                producers = ", ".join(topic_info.get("producers", []))
                consumers = ", ".join(topic_info.get("consumers", []))
                html += f"<tr><td>{topic_name}</td><td>{producers}</td><td>{consumers}</td></tr>\n"
                
        html += """
    </table>
</body>
</html>
"""
        return html
        
    def generate_output(self, data: Dict[str, Any], file_path: Path) -> None:
        """Generate the visualization output files.
        
        Args:
            data: The parsed Kafka analysis data
            file_path: Path where to save the visualization files
        """
        # Generate HTML content
        html = self.generate_html(data)
        
        # Ensure output directory exists
        if not file_path.exists():
            file_path.mkdir(parents=True)
            
        # Write output file
        output_file = file_path / "custom_viz.html"
        write_file(file_path, "custom_viz.html", html)
        
        print(f"Custom visualization generated at {output_file}")
```

### Step 2: Register Your Generator with the Factory

You can register your generator in a few ways:

#### Option 1: Modify `kafka_viz/visualization/factory.py`

Add your generator to the `_generators` dictionary in the `VisualizationFactory.__init__` method:

```python
def __init__(self):
    self._generators: Dict[str, Type[BaseGenerator]] = {
        "react": KafkaViz,
        "mermaid": MermaidGenerator,
        "simple": SimpleViz,
        "custom": CustomVisualizer  # Add your generator here
    }
    self._config = self._load_config()
```

#### Option 2: Register at Runtime

Register your generator at runtime before using the factory:

```python
from kafka_viz.visualization import visualization_factory
from kafka_viz.visualization.custom_viz import CustomVisualizer

# Register your generator
visualization_factory.register_generator("custom", CustomVisualizer)
```

### Step 3: Update Configuration (Optional)

You can add your visualization to the configuration file to control its visibility and metadata:

`kafka_viz/visualization/resources/config.json`:

```json
{
  "visualizations": {
    "react": {
      "name": "React Interactive",
      "description": "Interactive D3.js visualization with React UI",
      "enabled": true
    },
    "mermaid": {
      "name": "Mermaid Diagram",
      "description": "Simple Mermaid.js flowchart diagram",
      "enabled": true
    },
    "simple": {
      "name": "Simple HTML",
      "description": "Basic HTML visualization",
      "enabled": true
    },
    "custom": {
      "name": "Custom Visualization",
      "description": "My custom visualization type",
      "enabled": true
    }
  }
}
```

## Using Templates

You can create template files for your visualization in the resources directory:

1. Create a directory for your templates: `kafka_viz/visualization/resources/templates/custom/`
2. Add template files (HTML, CSS, JavaScript, etc.)
3. Load templates using the `load_template` function:

```python
from .utils import load_template

def generate_html(self, data: Dict[str, Any]) -> str:
    try:
        # Load template
        template = load_template("custom", "template.html")
        
        # Replace placeholders
        # ...
        
        return template.format(...)
    except FileNotFoundError:
        # Fallback to hardcoded template
        return """..."""
```

## Best Practices

1. **Separation of Concerns**: Keep data processing, template rendering, and file operations separate
2. **Error Handling**: Handle errors gracefully, using fallbacks when necessary
3. **Documentation**: Document your code with docstrings and comments
4. **Testing**: Write tests for your visualization generator

## Example Visualization Data Structure

The data structure passed to visualization generators looks like:

```python
{
    "services": {
        "service1": {
            "language": "java",
            "topics": {
                "topic1": {
                    "producers": ["service1"],
                    "consumers": ["service2"]
                }
            },
            "schemas": {
                "schema1": {
                    "type": "avro",
                    "namespace": "com.example"
                }
            }
        },
        "service2": {
            # ...
        }
    }
}
```

Use this structure to generate your visualizations.
