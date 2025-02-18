# mermaid_generator.py
from .base import BaseGenerator


class MermaidGenerator(BaseGenerator):
    def generate_html(self, data: dict) -> str:
        mermaid_diagram = self._generate_mermaid_diagram(data)
        return f"""
        <html>
        <body>
            <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            <script>mermaid.initialize({{startOnLoad:true}});</script>
            <div class="mermaid">
            {mermaid_diagram}
            </div>
        </body>
        </html>
        """

    def _generate_mermaid_diagram(self, data: dict) -> str:
        diagram = "graph LR\n"
        services = data.get("services", {})

        # Add nodes for each service
        for service_name in services:
            diagram += f"  {self._escape_node_name(service_name)}[{service_name}]\n"

        # Add edges for dependencies
        for service_name, service_data in services.items():
            for dependency in service_data.get("dependencies", []):
                diagram += (
                    f"  {self._escape_node_name(service_name)} --> "
                    f"{self._escape_node_name(dependency)}\n"
                )

        return diagram

    @staticmethod
    def _escape_node_name(name: str) -> str:
        return name.replace(" ", "_").replace("-", "_")


def generate_mermaid(analysis_result):
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


def visualize(analysis_result: dict):
    """Create visualization with Kafka dependencies."""
    mermaid_code = generate_mermaid(analysis_result)

    html_template = (
        """
    <html>
    <body>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>mermaid.initialize({startOnLoad:true});</script>
        <div class="mermaid">
        %s
        </div>
    </body>
    </html>
    """
        % mermaid_code
    )

    output_file = "architecture.html"
    with open(output_file, "w") as f:
        f.write(html_template)

    print(f"Generated visualization in {output_file}")
