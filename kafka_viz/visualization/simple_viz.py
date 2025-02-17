from .base import BaseGenerator


def clean_mermaid_id(name: str) -> str:
    """Clean a string to be a valid Mermaid ID."""
    # Use a more comprehensive list of invalid characters
    invalid_chars = {
        "-": "_",
        ".": "_",
        "${": "",
        "}": "",
        "#": "hash",
        "@": "at",
        " ": "_",
        ":": "_",
        "/": "_",
        "\\": "_",
        "{": "",
        "env.deployment": "env",
    }
    result = name
    for old, new in invalid_chars.items():
        result = result.replace(old, new)
    return result


def shorten_topic_name(topic: str) -> str:
    """Create a shorter display name for topics."""
    # Handle special characters and prefixes
    if topic.startswith("${"):
        main_part = topic.split("}")[-1] if "}" in topic else topic
        main_part = main_part.strip("${}")
    else:
        main_part = topic

    # Split by dots
    parts = main_part.split(".")

    if len(parts) >= 3:
        # For long topics, keep key parts
        if parts[0] == "kafka":
            # For kafka streams topics, take the meaningful part
            return f"kafka...{parts[-1]}"
        elif parts[0].startswith("app"):
            # For app related topics
            return f"{parts[0]}...{parts[-1]}"
        else:
            # For other long topics
            return f"{parts[0]}...{parts[-1]}"

    return main_part


class SimpleViz(BaseGenerator):
    def __init__(self):
        self.nodes = {}  # {node_id: display_name}
        self.edges = []  # List to maintain edge order
        self.schema_nodes = set()  # Track unique schema nodes
        self.schema_edges = []  # Track schema edges

    def generate_diagram(self, analysis_result: dict) -> str:
        """Generate Mermaid diagram with Kafka dependencies."""
        mermaid_lines = ["graph TB"]

        # Add Services subgraph
        service_nodes = self._add_services(analysis_result, mermaid_lines)

        # Add Topics subgraph
        topic_nodes = self._add_topics(analysis_result, mermaid_lines)

        # Add Schemas subgraph if present
        schema_nodes = self._add_schemas(analysis_result, mermaid_lines)

        # Add styling
        self._add_styling(mermaid_lines, service_nodes, topic_nodes, schema_nodes)

        return "\n".join(mermaid_lines)

    def _add_services(self, analysis_result: dict, mermaid_lines: list) -> set:
        """Add services to the diagram."""
        service_nodes = set()
        mermaid_lines.append("    subgraph Services")

        for service_name in sorted(analysis_result["services"].keys()):
            node_id = clean_mermaid_id(service_name)
            service_nodes.add(node_id)
            mermaid_lines.append(f'        {node_id}["{service_name}"]')

        mermaid_lines.append("    end")
        return service_nodes

    def _add_schemas(self, analysis_result: dict, mermaid_lines: list) -> set:
        """Add schemas and their relationships to the diagram."""
        has_schemas = any(
            service.get("schemas") for service in analysis_result["services"].values()
        )

        if has_schemas:
            mermaid_lines.append("    subgraph Schemas")

            # First add all unique schema nodes
            for service_info in analysis_result["services"].values():
                for schema_name in service_info.get("schemas", {}):
                    schema_id = f"schema_{schema_name}"
                    if schema_id not in self.schema_nodes:
                        self.schema_nodes.add(schema_id)
                        mermaid_lines.append(f'        {schema_id}["{schema_name}"]')

            # Then add all schema relationships
            for service_name, service_info in analysis_result["services"].items():
                service_id = service_name.replace("-", "_")
                for schema_name in service_info.get("schemas", {}):
                    schema_id = f"schema_{schema_name}"
                    self.schema_edges.append(f"    {service_id} -.-> {schema_id}")

            # Add edges in a consistent order
            mermaid_lines.extend(sorted(set(self.schema_edges)))
            mermaid_lines.append("    end")

        return self.schema_nodes

    def _add_topics(self, analysis_result: dict, mermaid_lines: list) -> set:
        """Add topics and their relationships to the diagram."""
        topic_nodes = set()
        mermaid_lines.append("    subgraph Topics")

        # First collect all edges
        for service_name, service_info in analysis_result["services"].items():
            service_id = service_name.replace("-", "_")

            for topic, topic_info in service_info.get("topics", {}).items():
                topic_id = f"topic_{clean_mermaid_id(topic)}"

                if topic_id not in self.nodes:
                    display_name = shorten_topic_name(topic)
                    self.nodes[topic_id] = display_name
                    topic_nodes.add(topic_id)

                # Add edges
                if service_name in topic_info.get("producers", []):
                    self.edges.append(f"    {service_id} --> {topic_id}")
                if service_name in topic_info.get("consumers", []):
                    self.edges.append(f"    {topic_id} --> {service_id}")

        # Add all topic nodes first
        for topic_id in sorted(topic_nodes):
            display_name = self.nodes[topic_id]
            mermaid_lines.append(f'        {topic_id}["{display_name}"]')

        # Add edges after all nodes
        mermaid_lines.extend(sorted(set(self.edges)))
        mermaid_lines.append("    end")
        return topic_nodes

    def _add_styling(
        self,
        mermaid_lines: list,
        service_nodes: set,
        topic_nodes: set,
        schema_nodes: set,
    ) -> None:
        """Add styling definitions to the diagram."""
        mermaid_lines.extend(
            [
                "    %% Styling",
                "    classDef service fill:#f9f,stroke:#333,stroke-width:2px",
                "    classDef topic fill:#bbf,stroke:#333,stroke-width:2px",
                "    classDef schema fill:#bfb,stroke:#333,stroke-width:2px",
            ]
        )

        if service_nodes:
            mermaid_lines.append(f"    class {' '.join(service_nodes)} service")
        if topic_nodes:
            mermaid_lines.append(f"    class {' '.join(topic_nodes)} topic")
        if schema_nodes:
            mermaid_lines.append(f"    class {' '.join(schema_nodes)} schema")

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
