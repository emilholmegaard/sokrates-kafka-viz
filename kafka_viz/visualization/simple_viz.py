# mermaid_generator.py
from .base import BaseGenerator


class SimpleViz(BaseGenerator):

    def generate_mermaid(self, analysis_result) -> str:
        """Generate Mermaid diagram with Kafka dependencies."""
        mermaid_lines = ["graph TD"]  # Using TD (top-down) for better layout

        # Track nodes
        added_nodes = set()
        topic_nodes = set()
        service_nodes = set()
        schema_nodes = set()

        # Add subgraphs for organization
        mermaid_lines.append("    subgraph Services")

        # Add services
        for service_name in analysis_result["services"].keys():
            node_id = self.clean_id(service_name)
            mermaid_lines.append(f'        {node_id}["{service_name}"]')
            service_nodes.add(node_id)
            added_nodes.add(node_id)
        mermaid_lines.append("    end")

        mermaid_lines.append("    subgraph Topics")
        # Add topics and their relationships
        for service_name, service_info in analysis_result["services"].items():
            service_id = self.clean_id(service_name)

            for topic, topic_info in service_info.get("topics", {}).items():
                # Clean topic name and create shorter display version
                topic_id = "topic_" + self.clean_id(topic)
                if topic_id not in added_nodes:
                    display_name = self.shorten_topic_name(topic)
                    mermaid_lines.append(f'        {topic_id}["{display_name}"]')
                    topic_nodes.add(topic_id)
                    added_nodes.add(topic_id)

                # Add relationships
                if service_name in topic_info.get("producers", []):
                    mermaid_lines.append(f"    {service_id} --> {topic_id}")
                if service_name in topic_info.get("consumers", []):
                    mermaid_lines.append(f"    {topic_id} --> {service_id}")
        mermaid_lines.append("    end")

        # Add schemas if present
        if any(
            service.get("schemas") for service in analysis_result["services"].values()
        ):
            mermaid_lines.append("    subgraph Schemas")
            for service_name, service_info in analysis_result["services"].items():
                service_id = self.clean_id(service_name)

                for schema_name in service_info.get("schemas", {}).keys():
                    schema_id = "schema_" + self.clean_id(schema_name)
                    if schema_id not in added_nodes:
                        mermaid_lines.append(f'        {schema_id}["{schema_name}"]')
                        schema_nodes.add(schema_id)
                        added_nodes.add(schema_id)
                    mermaid_lines.append(f"    {service_id} -.-> {schema_id}")
            mermaid_lines.append("    end")

        # Add styling
        mermaid_lines.extend(
            [
                "    %% Styling",
                "    classDef service fill:#f9f,stroke:#333,stroke-width:2px",
                "    classDef topic fill:#bbf,stroke:#333,stroke-width:2px",
                "    classDef schema fill:#bfb,stroke:#333,stroke-width:2px",
            ]
        )

        # Apply styles to nodes
        if service_nodes:
            mermaid_lines.append(f"    class {' '.join(service_nodes)} service")
        if topic_nodes:
            mermaid_lines.append(f"    class {' '.join(topic_nodes)} topic")
        if schema_nodes:
            mermaid_lines.append(f"    class {' '.join(schema_nodes)} schema")

        return "\n".join(mermaid_lines)

    def clean_id(self, name: str):
        """Clean string to make it a valid Mermaid ID."""
        return (
            name.replace("-", "_")
            .replace(".", "_")
            .replace("${", "")
            .replace("}", "")
            .replace("#", "hash")
            .replace("@", "at")
            .replace(" ", "_")
            .replace(":", "_")
            .replace("/", "_")
        )

    def shorten_topic_name(self, topic: str) -> str:
        """Create a shorter, readable version of topic name."""
        # Remove common prefixes and variable notation
        cleaned = (
            topic.replace("${kafka.streams.", "")
            .replace("${config.kafka.", "")
            .replace("${env.deployment}", "env")
            .replace("}", "")
        )
        return cleaned

    def generate_html(self, data: dict) -> str:

        mermaid_code = self.generate_mermaid(data)

        html_template = f"""
            <!DOCTYPE html>
            <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Kafka Service Architecture</title>
                    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
                <style>
                    .mermaid {{
                        width: 100%;
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
                            curve: 'basis',
                            rankSpacing: 100,
                            nodeSpacing: 100
                        }},
                        securityLevel: 'loose'
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
