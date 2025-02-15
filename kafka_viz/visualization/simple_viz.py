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
    # Handle special prefixes
    if topic.startswith("${"):
        # Extract the main part between ${ and }
        main_part = topic[2:].split("}")[0] if "}" in topic else topic[2:]
        # Take only the meaningful part of the topic name
        parts = main_part.split(".")
        if len(parts) > 2:
            return f"{parts[0]}...{parts[-1]}"
        return main_part

    # Handle app prefixes
    if topic.startswith("app"):
        parts = topic.split(".")
        if len(parts) > 2:
            return f"{parts[0]}...{parts[-1]}"

    return topic


class SimpleViz(BaseGenerator):
    def __init__(self):
        self.nodes = {}  # Track node IDs and display names
        self.edges = set()  # Track unique edges

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

    def _add_topics(self, analysis_result: dict, mermaid_lines: list) -> set:
        """Add topics and their relationships to the diagram."""
        topic_nodes = set()
        topic_edges = []
        mermaid_lines.append("    subgraph Topics")

        # First pass: collect and add all topics
        for service_info in analysis_result["services"].values():
            for topic in service_info.get("topics", {}):
                topic_id = f"topic_{clean_mermaid_id(topic)}"
                if topic_id not in self.nodes:
                    display_name = shorten_topic_name(topic)
                    self.nodes[topic_id] = display_name
                    topic_nodes.add(topic_id)
                    mermaid_lines.append(f'        {topic_id}["{display_name}"]')

        # Second pass: add relationships
        for service_name, service_info in analysis_result["services"].items():
            service_id = clean_mermaid_id(service_name)

            for topic, topic_info in service_info.get("topics", {}).items():
                topic_id = f"topic_{clean_mermaid_id(topic)}"

                # Add producer/consumer relationships
                if service_name in topic_info.get("producers", []):
                    self.edges.add(f"    {service_id} --> {topic_id}")
                if service_name in topic_info.get("consumers", []):
                    self.edges.add(f"    {topic_id} --> {service_id}")

        # Add all edges after node definitions
        mermaid_lines.extend(sorted(set(topic_edges)))
        mermaid_lines.append("    end")
        return topic_nodes

    def _add_schemas(self, analysis_result: dict, mermaid_lines: list) -> set:
        """Add schemas and their relationships to the diagram."""
        schema_nodes = set()
        has_schemas = any(
            service.get("schemas") for service in analysis_result["services"].values()
        )

        if has_schemas:
            mermaid_lines.append("    subgraph Schemas")
            for service_name, service_info in analysis_result["services"].items():
                service_id = clean_mermaid_id(service_name)

                for schema_name in service_info.get("schemas", {}):
                    schema_id = f"schema_{clean_mermaid_id(schema_name)}"
                    if schema_id not in self.nodes:
                        schema_nodes.add(schema_id)
                        mermaid_lines.append(f'        {schema_id}["{schema_name}"]')
                    mermaid_lines.append(f"    {service_id} -.-> {schema_id}")

            mermaid_lines.append("    end")

        return schema_nodes

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
