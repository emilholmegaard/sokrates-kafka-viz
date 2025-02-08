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
