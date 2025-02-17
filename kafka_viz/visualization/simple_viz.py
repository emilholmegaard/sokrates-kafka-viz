from .base import BaseGenerator


def clean_node_id(topic: str) -> str:
    """Create safe node ID by replacing invalid characters."""
    replacements = {
        "${": "",
        "}": "",
        "-": "_",
        ".": "_",
        "#": "hash",
        "@": "at",
        " ": "_",
        ":": "_",
        "/": "_",
        "\\": "_",
    }
    result = topic
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def format_topic_name(topic: str) -> str:
    """Format topic name for display."""
    if topic == "#{":
        return "#{}"
    if topic == "M" or topic == "topic":
        return topic

    if "kafka.streams" in topic:
        parts = topic.replace("${", "").replace("}", "").split(".")
        meaningful_part = parts[-1]
        if meaningful_part == "target-topic":
            meaningful_part = "target"
        return f"kafka.streams...{meaningful_part}"

    if topic.startswith("app"):
        parts = topic.split(".")
        if "event" in parts:
            event_idx = parts.index("event")
            if event_idx + 1 < len(parts):
                return f"app...{parts[event_idx+1]}"
        return f"app...{parts[-1]}"

    if topic.startswith("${config"):
        parts = topic.replace("${", "").replace("}", "").split(".")
        return f"config.kafka...{parts[-1]}"

    return topic


class SimpleViz(BaseGenerator):
    def __init__(self):
        self.nodes = {}  # {node_id: display_name}
        self.edges = []  # List to maintain edge order
        self.schema_nodes = set()  # Track unique schema nodes
        self.schema_edges = []  # Track schema edges

    def generate_diagram(self, analysis_result: dict) -> str:
        """Generate Mermaid diagram with Kafka dependencies."""
        lines = ["graph TB"]

        # Add Services section
        service_nodes = self._add_services(analysis_result, lines)

        # Add Topics section
        topic_nodes = self._add_topics(analysis_result, lines)

        # Add Schemas section
        schema_nodes = self._add_schemas(analysis_result, lines)

        # Add styling
        lines.extend(
            [
                "    %% Styling",
                "    classDef service fill:#f9f,stroke:#333,stroke-width:2px",
                "    classDef topic fill:#bbf,stroke:#333,stroke-width:2px",
                "    classDef schema fill:#bfb,stroke:#333,stroke-width:2px",
            ]
        )

        # Apply classes
        if service_nodes:
            lines.append(f"    class {' '.join(sorted(service_nodes))} service")
        if topic_nodes:
            lines.append(f"    class {' '.join(sorted(topic_nodes))} topic")
        if schema_nodes:
            lines.append(f"    class {' '.join(sorted(schema_nodes))} schema")

        return "\n".join(lines)

    def _add_services(self, analysis_result: dict, lines: list) -> set:
        """Add services section."""
        service_nodes = set()
        lines.append("    subgraph Services")

        for service_name in sorted(analysis_result["services"].keys()):
            node_id = clean_node_id(service_name)
            service_nodes.add(node_id)
            lines.append(f'        {node_id}["{service_name}"]')

        lines.append("    end")
        return service_nodes

    def _add_topics(self, analysis_result: dict, lines: list) -> set:
        """Add topics section with relationships."""
        topic_nodes = set()
        topic_edges = []

        # First collect all topics
        topics = {}  # {topic_id: display_name}
        for service_info in analysis_result["services"].values():
            for topic in service_info.get("topics", {}):
                topic_id = f"topic_{clean_node_id(topic)}"
                if topic_id not in topics:
                    topics[topic_id] = format_topic_name(topic)
                    topic_nodes.add(topic_id)

        # Start Topics section
        lines.append("    subgraph Topics")

        # Add topic nodes
        for topic_id in sorted(topics.keys()):
            lines.append(f'        {topic_id}["{topics[topic_id]}"]')

        lines.append("")  # Add spacing

        # Add relationships
        for service_name, service_info in analysis_result["services"].items():
            service_id = clean_node_id(service_name)
            for topic, topic_info in service_info.get("topics", {}).items():
                topic_id = f"topic_{clean_node_id(topic)}"

                if service_name in topic_info.get("producers", []):
                    topic_edges.append(f"    {service_id} --> {topic_id}")
                if service_name in topic_info.get("consumers", []):
                    topic_edges.append(f"    {topic_id} --> {service_id}")

        # Add edges in sorted order
        lines.extend(sorted(set(topic_edges)))
        lines.append("    end")
        return topic_nodes

    def _add_schemas(self, analysis_result: dict, lines: list) -> set:
        """Add schemas section."""
        schema_nodes = set()
        schema_edges = []

        has_schemas = any(
            service.get("schemas") for service in analysis_result["services"].values()
        )

        if has_schemas:
            lines.append("    subgraph Schemas")

            # Collect unique schemas
            schemas = set()
            for service_info in analysis_result["services"].values():
                schemas.update(service_info.get("schemas", {}).keys())

            # Add schema nodes
            for schema_name in sorted(schemas):
                schema_id = f"schema_{clean_node_id(schema_name)}"
                schema_nodes.add(schema_id)
                lines.append(f'        {schema_id}["{schema_name}"]')

            lines.append("")  # Add spacing

            # Add schema relationships
            for service_name, service_info in analysis_result["services"].items():
                service_id = clean_node_id(service_name)
                for schema_name in service_info.get("schemas", {}):
                    schema_id = f"schema_{clean_node_id(schema_name)}"
                    schema_edges.append(f"    {service_id} -.-> {schema_id}")

            # Add edges in sorted order
            lines.extend(sorted(schema_edges))
            lines.append("    end")

        return schema_nodes

    def generate_html(self, data: dict) -> str:

        mermaid_code = self.generate_diagram(data)

        html_template = f"""
        <!DOCTYPE html>
        <html>
            <head>
            <meta charset="UTF-8">
            <title>Kafka Service Architecture</title>
            <script src='https://cdn.jsdelivr.net/npm/mermaid@9.3.0/dist/mermaid.min.js'></script>
            <style>
                .mermaid {{
                width: 100%;
                height: 100%;
                overflow: auto;
                }}
            </style>
            <script>
                mermaid.initialize({{
                startOnLoad: true,
                theme: 'default',
                flowchart: {{
                    useMaxWidth: true,
                    htmlLabels: true,
                    curve: 'basis'
                }},
                securityLevel: 'loose',
                maxTextSize: 90000
                }});
            </script>
            </head>
            <body>
            <div class="mermaid">
                {mermaid_code}
            </div>
            </body>
        </html>
        """

        return html_template
