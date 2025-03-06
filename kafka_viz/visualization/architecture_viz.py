from pathlib import Path
from .base import BaseGenerator


class ArchitectureVisualizer(BaseGenerator):
    """Visualization generator for architecture diagrams."""
    
    def __init__(self):
        super().__init__()
        self.name = "Architecture Visualization"
        self.description = "Visualization of system architecture"
        self.output_filename = "architecture.html"
    
    def generate_html(self, data: dict) -> str:
        """Generate HTML for the visualization."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Architecture Visualization</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        .service {
            margin-bottom: 30px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #f9f9f9;
        }
        .service h2 {
            margin-top: 0;
            color: #2196F3;
        }
        .service-detail {
            margin-bottom: 10px;
        }
        .topics, .schemas {
            margin-top: 15px;
        }
        .topic-item, .schema-item {
            margin-bottom: 10px;
            padding: 10px;
            background-color: #fff;
            border: 1px solid #eee;
            border-radius: 4px;
        }
        .topic-name, .schema-name {
            font-weight: bold;
            color: #333;
        }
        .producers, .consumers {
            margin-top: 5px;
            color: #666;
        }
        .schema-type {
            color: #888;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Kafka Architecture Visualization</h1>
"""
        
        # Add services
        for service_name, service_data in data.get("services", {}).items():
            html += f"""
        <div class="service">
            <h2>{service_name}</h2>
            <div class="service-detail">
                <strong>Language:</strong> {service_data.get("language", "Unknown")}
            </div>
            
            <div class="topics">
                <h3>Topics</h3>
"""
            
            # Add topics for this service
            has_topics = False
            for topic_name, topic_info in service_data.get("topics", {}).items():
                has_topics = True
                producers = ", ".join(topic_info.get("producers", []))
                consumers = ", ".join(topic_info.get("consumers", []))
                
                html += f"""
                <div class="topic-item">
                    <div class="topic-name">{topic_name}</div>
                    <div class="producers">Producers: {producers or "None"}</div>
                    <div class="consumers">Consumers: {consumers or "None"}</div>
                </div>
"""
            
            if not has_topics:
                html += """
                <p>No topics defined for this service.</p>
"""
            
            html += """
            </div>
            
            <div class="schemas">
                <h3>Schemas</h3>
"""
            
            # Add schemas for this service
            has_schemas = False
            for schema_name, schema_info in service_data.get("schemas", {}).items():
                has_schemas = True
                schema_type = schema_info.get("type", "unknown")
                namespace = schema_info.get("namespace", "")
                
                html += f"""
                <div class="schema-item">
                    <div class="schema-name">{schema_name}</div>
                    <div class="schema-type">Type: {schema_type}</div>
                    <div class="schema-namespace">Namespace: {namespace}</div>
                </div>
"""
            
            if not has_schemas:
                html += """
                <p>No schemas defined for this service.</p>
"""
            
            html += """
            </div>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_output(self, data: dict, file_path: Path) -> None:
        """Generate the visualization output."""
        try:
            html_content = self.generate_html(data)
            
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
