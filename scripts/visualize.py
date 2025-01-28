#!/usr/bin/env python3

import json
import typer
from pathlib import Path
from typing import Dict, Any

def generate_mermaid(data: Dict[str, Any]) -> str:
    """Generate a Mermaid diagram from the analysis data."""
    mermaid = ["""
graph TB
    %% Style definitions
    classDef service fill:#2ecc71,stroke:#27ae60,stroke-width:2px
    classDef topic fill:#3498db,stroke:#2980b9,stroke-width:2px
    classDef schema fill:#9b59b6,stroke:#8e44ad,stroke-width:2px
    """]

    # Add services
    for service_name in data['services']:
        mermaid.append(f"    {service_name}[{service_name}]:::service")

    # Add topics
    for topic in data['topics']:
        topic_id = f"topic_{topic.replace('.', '_')}"
        mermaid.append(f"    {topic_id}({topic}):::topic")

    # Add relationships
    for service_name, service_data in data['services'].items():
        # Producer relationships
        for topic in service_data['producers']:
            topic_id = f"topic_{topic.replace('.', '_')}"
            mermaid.append(f"    {service_name} --> {topic_id}")

        # Consumer relationships
        for topic in service_data['consumers']:
            topic_id = f"topic_{topic.replace('.', '_')}"
            mermaid.append(f"    {topic_id} --> {service_name}")

    return '\n'.join(mermaid)

def generate_html(mermaid_diagram: str) -> str:
    """Generate an HTML page with the Mermaid diagram."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Kafka Architecture Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        #diagram {{ width: 100%; overflow: auto; }}
    </style>
</head>
<body>
    <h1>Kafka Architecture Visualization</h1>
    <div id="diagram">
        <pre class="mermaid">
{mermaid_diagram}
        </pre>
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</body>
</html>
"""

def main(
    input_file: Path = typer.Argument(..., help="Input JSON file from analysis"),
    output_file: Path = typer.Option("architecture.html", help="Output HTML file path")
):
    """Generate visualization from analysis results."""
    # Read analysis data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Generate Mermaid diagram
    mermaid_diagram = generate_mermaid(data)

    # Generate HTML
    html_content = generate_html(mermaid_diagram)

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Visualization generated at {output_file}")

if __name__ == "__main__":
    typer.run(main)