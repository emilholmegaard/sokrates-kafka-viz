from pathlib import Path

from .base import BaseGenerator
from .utils import clean_node_id, format_topic_name, load_template, write_file


class MermaidGenerator(BaseGenerator):
    """Mermaid diagram generator for Kafka visualization."""
    
    def __init__(self):
        super().__init__()
        self.name = "Mermaid Diagram"
        self.description = "Simple Mermaid.js flowchart diagram"
        self.output_filename = "kafka_architecture.html"
        self.nodes = {}  # {node_id: display_name}
        self.edges = []  # List to maintain edge order
        self.schema_nodes = set()  # Track unique schema nodes
        self.schema_edges = []  # Track schema edges

    def generate_diagram(self, analysis_result: dict) -> str:
        """Generate Mermaid diagram with Kafka dependencies."""
        # Change from TB (top to bottom) to LR (left to right) for better space usage
        lines = ["graph LR"]

        # Add Services section
        lines.append("  subgraph Services")
        services = []
        for service_name in sorted(analysis_result["services"].keys()):
            # Remove any special characters that might cause syntax issues
            node_id = f"service_{clean_node_id(service_name)}"
            services.append(node_id)
            # Make sure quotes are properly escaped for node labels
            lines.append(f'    {node_id}["{service_name}"]')
        lines.append("  end")

        # Add Topics section
        lines.append("  subgraph Topics")
        topics = []
        topic_edges = []
        for service_name, service_info in analysis_result["services"].items():
            service_id = f"service_{clean_node_id(service_name)}"
            for topic, topic_info in service_info.get("topics", {}).items():
                topic_id = f"topic_{clean_node_id(topic)}"
                if topic_id not in topics:
                    topics.append(topic_id)
                    # Make sure quotes are properly escaped for node labels
                    display_name = format_topic_name(topic).replace('"', '\\"')
                    lines.append(f'    {topic_id}["{display_name}"]')

                # Collect edges but don't add them yet
                if service_name in topic_info.get("producers", []):
                    topic_edges.append(f"  {service_id} --> {topic_id}")
                if service_name in topic_info.get("consumers", []):
                    topic_edges.append(f"  {topic_id} --> {service_id}")
        lines.append("  end")

        # Add Schemas section if there are any schemas
        schemas = []
        schema_edges = []
        has_schemas = False
        
        for service_name, service_info in analysis_result["services"].items():
            if service_info.get("schemas"):
                has_schemas = True
                break
                
        if has_schemas:
            lines.append("  subgraph Schemas")
            for service_name, service_info in analysis_result["services"].items():
                service_id = f"service_{clean_node_id(service_name)}"
                for schema_name in service_info.get("schemas", {}).keys():
                    schema_id = f"schema_{clean_node_id(schema_name)}"
                    if schema_id not in schemas:
                        schemas.append(schema_id)
                        schema_display = schema_name.replace('"', '\\"')
                        lines.append(f'    {schema_id}["{schema_display}"]')
                    # Collect schema edges
                    schema_edges.append(f"  {service_id} -.-> {schema_id}")
            lines.append("  end")

        # Add all relationships
        lines.extend(sorted(set(topic_edges)))
        lines.extend(sorted(set(schema_edges)))

        # Basic styling (simplified to avoid syntax errors)
        lines.extend([
            "  %% Styling",
            "  classDef service fill:#f9f",
            "  classDef topic fill:#bbf",
            "  classDef schema fill:#bfb",
            "  class service service",
            "  class topic topic",
            "  class schema schema",
        ])

        return "\n".join(lines)

    def generate_html(self, data: dict) -> str:
        """Generate HTML with embedded Mermaid diagram."""
        mermaid_code = self.generate_diagram(data)

        # Simple HTML template with Mermaid.js
        html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Kafka Service Architecture</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@9.3.0/dist/mermaid.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        h1 {
            color: #333;
        }
        .mermaid {
            width: 100%;
            overflow: auto;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <h1>Kafka Architecture Diagram</h1>
    <div class="mermaid">
{0}
    </div>
    <script>
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            logLevel: 'error',
            securityLevel: 'loose',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            }
        });
    </script>
</body>
</html>""".format(mermaid_code)

        return html_template

    def generate_output(self, data: dict, file_path: Path) -> None:
        """Generate the visualization output."""
        try:
            html_content = self.generate_html(data)
            
            # Ensure directory exists
            if not file_path.exists():
                file_path.mkdir(parents=True)
                
            output_file = file_path / self.output_filename
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            print(f"Mermaid visualization generated at {output_file}")
        except Exception as e:
            print(f"Error generating Mermaid visualization: {e}")
            raise
