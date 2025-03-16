"""Generator for Mermaid diagram-based visualization."""
from pathlib import Path

from .base import BaseGenerator
from .utils import clean_node_id, format_topic_name, write_file


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

        # Add Services section with explicit positioning
        lines.append("subgraph Services[Services]")
        services = []
        for i, service_name in enumerate(sorted(analysis_result["services"].keys())):
            node_id = clean_node_id(service_name)
            services.append(node_id)
            # Add positioning hint
            lines.append(f'    {node_id}["{service_name}"]:::service')
        lines.append("end")

        # Add Topics section
        lines.append("subgraph Topics[Topics]")
        topics = []
        topic_edges = []
        for service_name, service_info in analysis_result["services"].items():
            service_id = clean_node_id(service_name)
            for topic, topic_info in service_info.get("topics", {}).items():
                topic_id = f"topic_{clean_node_id(topic)}"
                if topic_id not in topics:
                    topics.append(topic_id)
                    lines.append(f'    {topic_id}["{format_topic_name(topic)}"]')

                # Collect edges but don't add them yet
                if service_name in topic_info.get("producers", []):
                    topic_edges.append(f"{service_id} --> {topic_id}")
                if service_name in topic_info.get("consumers", []):
                    topic_edges.append(f"{topic_id} --> {service_id}")
        lines.append("end")

        # Add Schemas section
        lines.append("subgraph Schemas[Schemas]")
        schemas = []
        schema_edges = []
        for service_name, service_info in analysis_result["services"].items():
            service_id = clean_node_id(service_name)
            for schema_name in service_info.get("schemas", {}).keys():
                schema_id = f"schema_{clean_node_id(schema_name)}"
                if schema_id not in schemas:
                    schemas.append(schema_id)
                    lines.append(f'    {schema_id}["{schema_name}"]')
                # Collect schema edges
                schema_edges.append(f"{service_id} -.-> {schema_id}")
        lines.append("end")

        # Add all relationships
        lines.extend(sorted(set(topic_edges)))
        lines.extend(sorted(set(schema_edges)))

        # Enhanced styling
        lines.extend(
            [
                "%% Styling",
                "classDef service fill:#f9f,stroke:#333,stroke-width:2px;",
                "classDef topic fill:#bbf,stroke:#333,stroke-width:2px;",
                "classDef schema fill:#bfb,stroke:#333,stroke-width:2px;",
                "classDef default fill:#fff,stroke:#333,stroke-width:1px;",
                "%% Layout configuration",
                "%%{init: {",
                "'flowchart': {",
                "'curve': 'monotoneX',",
                "'nodeSpacing': 100,",
                "'rankSpacing': 100,",
                "'ranker': 'tight-tree'",
                "},",
                "'theme': 'default'",
                "} }%%",
                "%% Apply styles",
                "class Services service;",
                "class Topics topic;",
                "class Schemas schema;",
            ]
        )

        return "\n".join(lines)

    def generate_html(self, data: dict) -> str:
        """Generate HTML with embedded Mermaid diagram."""
        mermaid_code = self.generate_diagram(data)
        
        # Create HTML with direct string concatenation instead of templating
        html = """<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <title>Kafka Service Architecture</title>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 0;
                padding: 0;
            }
            .mermaid {
                width: 100%;
                height: 100vh;
                overflow: auto;
                padding: 20px;
            }
        </style>
    </head>
    <body>
        <pre class="mermaid">
""" + mermaid_code + """
        </pre>
        <script>
            mermaid.initialize({
                startOnLoad: true,
                theme: "default",
                flowchart: {
                    useMaxWidth: true,
                    htmlLabels: true,
                    curve: "monotoneX",
                    nodeSpacing: 100,
                    rankSpacing: 100,
                    ranker: "tight-tree"
                },
                securityLevel: "loose",
                maxTextSize: 90000
            });
        </script>
    </body>
</html>"""

        return html

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
