from pathlib import Path

from .base import BaseGenerator
from .utils import clean_node_id, format_topic_name


class MermaidGenerator(BaseGenerator):
    """Mermaid diagram generator for Kafka visualization."""
    
    def __init__(self):
        super().__init__()
        self.name = "Mermaid Diagram"
        self.description = "Simple Mermaid.js flowchart diagram"
        self.output_filename = "kafka_architecture.html"
        
    def generate_diagram(self, analysis_result: dict) -> str:
        """Generate Mermaid diagram with Kafka dependencies."""
        mermaid_code = ["graph LR"]

        # Track nodes to avoid duplicates
        added_nodes = set()

        # Add services
        for service_name, service_info in analysis_result["services"].items():
            if service_name not in added_nodes:
                node_id = service_name.replace("-", "_")
                mermaid_code.append(f'    {node_id}["{service_name}"]')
                added_nodes.add(service_name)

        # Add topics
        for service_name, service_info in analysis_result["services"].items():
            for topic, topic_info in service_info.get("topics", {}).items():
                if topic not in added_nodes:
                    topic_id = f'topic_{topic.replace("-", "_").replace(".", "_")}'
                    mermaid_code.append(f'    {topic_id}["{topic}"]')
                    added_nodes.add(topic)

                # Add producer relationships
                if topic_info.get("producers"):
                    for producer in topic_info["producers"]:
                        producer_id = producer.replace("-", "_")
                        mermaid_code.append(f"    {producer_id} -->|produces| {topic_id}")

                # Add consumer relationships
                if topic_info.get("consumers"):
                    for consumer in topic_info["consumers"]:
                        consumer_id = consumer.replace("-", "_")
                        mermaid_code.append(
                            f"    {topic_id} -->|consumed by| {consumer_id}"
                        )

        # Add schema relationships if present
        for service_name, service_info in analysis_result["services"].items():
            for schema_name, schema_info in service_info.get("schemas", {}).items():
                if schema_name not in added_nodes:
                    schema_id = f'schema_{schema_name.replace("-", "_")}'
                    mermaid_code.append(f'    {schema_id}["Schema: {schema_name}"]')
                    added_nodes.add(schema_name)

        # Add styling
        mermaid_code.extend(
            [
                "    %% Style definitions",
                "    classDef service fill:#f9f,stroke:#333,stroke-width:2px",
                "    classDef topic fill:#bbf,stroke:#333,stroke-width:2px",
                "    classDef schema fill:#bfb,stroke:#333,stroke-width:2px",
                "",
                "    %% Apply styles",
                "    class "
                + ",".join(s.replace("-", "_") for s in analysis_result["services"].keys())
                + " service",
                "    class "
                + ",".join(
                    f'topic_{t.replace("-", "_").replace(".", "_")}'
                    for s in analysis_result["services"].values()
                    for t in s.get("topics", {})
                )
                + " topic",
                "    class "
                + ",".join(
                    f'schema_{s.replace("-", "_")}'
                    for svc in analysis_result["services"].values()
                    for s in svc.get("schemas", {})
                )
                + " schema",
            ]
        )

        return "\n".join(mermaid_code)

    def generate_html(self, data: dict) -> str:
        """Generate HTML with embedded Mermaid diagram."""
        mermaid_code = self.generate_diagram(data)
        
        # Using the % formatting operator from the working main branch implementation
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Kafka Service Architecture</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        .mermaid {
            width: 100%%;
            overflow: auto;
            padding: 20px;
        }
    </style>
</head>
<body>
    <h1>Kafka Service Architecture</h1>
    <script>
        mermaid.initialize({
            startOnLoad: true,
            theme: "default",
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: "monotoneX"
            },
            securityLevel: "loose",
            maxTextSize: 90000
        });
    </script>
    <div class="mermaid">
%s
    </div>
</body>
</html>
""" % mermaid_code

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
