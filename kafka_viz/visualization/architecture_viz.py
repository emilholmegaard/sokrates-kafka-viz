from typing import Dict, List, Optional, Set
from pathlib import Path

from .base import BaseGenerator


class ArchitectureVisualizer(BaseGenerator):
    """Architecture visualization using Mermaid."""
    
    def __init__(self) -> None:
        super().__init__()
        self.name = "Architecture Diagram"
        self.description = "Service and schema architecture diagram"
        self.output_filename = "architecture.html"
        self.data: Dict = {}
        self.services: List[str] = []
        self.schemas: List[str] = []
        self.schema_relationships: Dict[str, List[str]] = {}

    def _extract_services(self) -> List[str]:
        """
        Extract services from the architecture data

        :return: Sorted list of service names
        """
        services = set(self.data.get("services", {}).keys())
        return sorted(services)

    def _extract_schemas(self) -> List[str]:
        """
        Extract unique schemas from services

        :return: Sorted list of schema names
        """
        schemas: Set[str] = set()
        for service_info in self.data.get("services", {}).values():
            schemas.update(service_info.get("schemas", {}).keys())
        return sorted(schemas)

    def _extract_schema_relationships(self) -> Dict[str, List[str]]:
        """
        Extract schema relationships for services

        :return: Dictionary of service to schemas mappings
        """
        relationships = {}
        for service_name, service_info in self.data.get("services", {}).items():
            service_schemas = list(service_info.get("schemas", {}).keys())
            if service_schemas:
                relationships[service_name] = service_schemas
        return relationships

    def _clean_node_id(self, name: str) -> str:
        """
        Create a clean, CSS-friendly node ID

        :param name: Original name
        :return: Cleaned node ID
        """
        replacements = {
            "-": "_",
            ".": "_",
            "#": "hash",
            "@": "at",
            " ": "_",
            ":": "_",
            "/": "_",
            "\\": "_",
            "${": "",
            "}": "",
        }
        result = name
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    def generate_mermaid_diagram(
        self,
        custom_services: Optional[List[str]] = None,
        custom_schemas: Optional[List[str]] = None,
        custom_relationships: Optional[Dict[str, List[str]]] = None,
    ) -> str:
        """
        Generate Mermaid diagram with architecture dependencies

        :param custom_services: Optional custom list of services
        :param custom_schemas: Optional custom list of schemas
        :param custom_relationships: Optional custom schema relationships
        :return: Mermaid diagram as a string
        """
        # Use custom or extracted data
        services = custom_services or self.services
        schemas = custom_schemas or self.schemas
        relationships = custom_relationships or self.schema_relationships

        lines = ["graph TB"]

        # Add Services section
        lines.append("    subgraph Services")
        for service_name in services:
            node_id = self._clean_node_id(service_name)
            lines.append(f'        {node_id}["{service_name}"]')
        lines.append("    end")

        # Add Schemas section
        lines.append("    subgraph Schemas")
        for schema_name in schemas:
            schema_id = f"schema_{self._clean_node_id(schema_name)}"
            lines.append(f'        {schema_id}["{schema_name}"]')
        lines.append("    end")

        # Add Schema Relationships
        for service, service_schemas in relationships.items():
            service_id = self._clean_node_id(service)
            for schema_name in service_schemas:
                schema_id = f"schema_{self._clean_node_id(schema_name)}"
                lines.append(f"    {service_id} -.-> {schema_id}")

        # Add Styling
        lines.extend(
            [
                "    %% Styling",
                "    classDef service fill:#f9f,stroke:#333,stroke-width:2px",
                "    classDef topic fill:#bbf,stroke:#333,stroke-width:2px",
                "    classDef schema fill:#bfb,stroke:#333,stroke-width:2px",
            ]
        )

        # Apply classes
        if services:
            lines.append(
                f"    class {' '.join(self._clean_node_id(s) for s in services)} service"
            )
        if schemas:
            lines.append(
                f"    class {' '.join(f'schema_{self._clean_node_id(s)}' for s in schemas)} schema"
            )

        return "\n".join(lines)

    def _generate_html_content(
        self,
        custom_services: Optional[List[str]] = None,
        custom_schemas: Optional[List[str]] = None,
        custom_relationships: Optional[Dict[str, List[str]]] = None,
    ) -> str:
        """
        Generate HTML with embedded Mermaid diagram

        :param custom_services: Optional custom list of services
        :param custom_schemas: Optional custom list of schemas
        :param custom_relationships: Optional custom schema relationships
        :return: HTML string with Mermaid diagram
        """
        mermaid_code = self.generate_mermaid_diagram(
            custom_services, custom_schemas, custom_relationships
        )

        html_template = """<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <title>Kafka Service Architecture</title>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }
            .mermaid {
                width: 100%;
                height: 100vh;
                overflow: auto;
            }
            h1 {
                color: #2196F3;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <h1>Kafka Service Architecture</h1>
        <div class="mermaid">
{diagram_content}
        </div>
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
    </body>
</html>"""

        return html_template.format(diagram_content=mermaid_code)

    def generate_html(self, data: Dict) -> str:
        """Generate HTML for the visualization."""
        self.data = data
        self.services = self._extract_services()
        self.schemas = self._extract_schemas()
        self.schema_relationships = self._extract_schema_relationships()

        html_output = self._generate_html_content(
            self.services, self.schemas, self.schema_relationships
        )

        return html_output
        
    def generate_output(self, data: Dict, file_path: Path) -> None:
        """Generate the visualization output files."""
        self.data = data
        self.services = self._extract_services()
        self.schemas = self._extract_schemas()
        self.schema_relationships = self._extract_schema_relationships()
        
        try:
            # Generate HTML
            html_content = self._generate_html_content(
                self.services, self.schemas, self.schema_relationships
            )
            
            # Ensure directory exists
            if not file_path.exists():
                file_path.mkdir(parents=True)
                
            # Write output file
            output_file = file_path / self.output_filename
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            print(f"Architecture visualization generated at {output_file}")
        except Exception as e:
            print(f"Error generating architecture visualization: {e}")
            raise
