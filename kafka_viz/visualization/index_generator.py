"""
Generator for the index page that links to all visualizations.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseGenerator
from .utils import load_template, write_file


class IndexGenerator(BaseGenerator):
    """Generator for the index page linking all visualizations.

    This generator creates an HTML index page that links to all generated
    visualizations, providing a unified entry point.
    """

    def __init__(self):
        super().__init__()
        self.name = "Visualization Index"
        self.description = "Entry point linking to all visualizations"
        self.output_filename = "index.html"

    def generate_html(
        self, data: Dict[str, Any], vis_links: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate the HTML for the index page.

        Args:
            data: The parsed Kafka analysis data
            vis_links: Optional list of visualization links and metadata

        Returns:
            str: The generated HTML
        """
        if vis_links is None:
            vis_links = []

        try:
            # Load template
            template = load_template("index", "index.html")

            # Calculate stats
            services = data.get("services", {})
            service_count = len(services)

            # Count topics (unique across all services)
            all_topics = set()
            for service_info in services.values():
                for topic_name in service_info.get("topics", {}).keys():
                    all_topics.add(topic_name)
            topic_count = len(all_topics)

            # Count schemas (unique across all services)
            all_schemas = set()
            for service_info in services.values():
                for schema_name in service_info.get("schemas", {}).keys():
                    all_schemas.add(schema_name)
            schema_count = len(all_schemas)

            # Generate visualization links HTML
            vis_links_html = ""
            for vis in vis_links:
                vis_links_html += f"""
                <div class="visualization-item">
                    <div class="visualization-name">{vis["name"]}</div>
                    <div class="visualization-description">{vis["description"]}</div>
                    <a href="{vis["path"]}" class="visualization-link">View Visualization</a>
                </div>
                """

            # Replace placeholders in template
            return template.format(
                visualization_links=vis_links_html,
                service_count=service_count,
                topic_count=topic_count,
                schema_count=schema_count,
            )
        except Exception:
            # Fallback to a simple HTML page if template can't be loaded
            vis_links_html = ""
            for vis in vis_links:
                vis_links_html += (
                    f"<li><a href='{vis['path']}'>{vis['name']}</a> - "
                    f"{vis['description']}</li>"
                )

            return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Kafka Visualization Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2196F3; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 10px; }}
    </style>
</head>
<body>
    <h1>Kafka Visualizations</h1>
    <p>Select a visualization type below:</p>
    <ul>
        {vis_links_html}
    </ul>
</body>
</html>"""

    def generate_output(
        self,
        data: Dict[str, Any],
        output_dir: Path,
        vis_links: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Generate the index page in the output directory.

        Args:
            data: The parsed Kafka analysis data
            output_dir: The path to the output directory
            vis_links: List of visualization links and metadata
        """
        if vis_links is None or len(vis_links) == 0:
            print("No visualization links provided. Skipping index generation.")
            return

        try:
            # Create output directory if it doesn't exist
            if not output_dir.exists():
                output_dir.mkdir(parents=True)

            # Generate HTML
            html = self.generate_html(data, vis_links)
            write_file(output_dir, self.output_filename, html)

            # Copy CSS file
            try:
                css_template = load_template("index", "styles.css")
                write_file(output_dir, "styles.css", css_template)
            except Exception as e:
                print(f"Warning: Could not copy CSS file: {e}")

            print(f"Index page generated at {output_dir / self.output_filename}")

        except Exception as e:
            print(f"Error generating index page: {e}")
            raise
