import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Load configuration
def load_config() -> Dict[str, Any]:
    """Load visualization configuration."""
    config_path = Path(__file__).parent / "resources" / "config.json"
    if not config_path.exists():
        # Fallback to old resources path
        config_path = Path(__file__).parent / "ressources" / "config.json"
        if not config_path.exists():
            # Return default config if no config file exists
            return {
                "visualizations": {
                    "react": {
                        "name": "React Interactive",
                        "description": "Interactive D3.js visualization with React UI",
                        "enabled": True
                    },
                    "mermaid": {
                        "name": "Mermaid Diagram",
                        "description": "Simple Mermaid.js flowchart diagram",
                        "enabled": True
                    },
                    "simple": {
                        "name": "Simple HTML",
                        "description": "Basic HTML visualization",
                        "enabled": True
                    }
                }
            }
    
    with open(config_path, "r") as f:
        return json.load(f)

# Get available visualizations
def get_available_visualizations() -> Dict[str, Dict[str, Any]]:
    """Get available visualization options."""
    config = load_config()
    return {k: v for k, v in config["visualizations"].items() if v.get("enabled", True)}

# Load template file
def load_template(vis_type: str, template_name: str) -> str:
    """Load a template file for the specified visualization type."""
    template_path = Path(__file__).parent / "resources" / "templates" / vis_type / template_name
    if not template_path.exists():
        # Fallback to old resources path
        template_path = Path(__file__).parent / "ressources" / "templates" / vis_type / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_name} for {vis_type}")
    
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

# Get generator class by name
def get_generator_by_name(name: str):
    """Get a visualization generator class by name."""
    from .kafka_viz import KafkaViz
    from .simple_viz import SimpleViz
    from .mermaid import MermaidGenerator
    
    generators = {
        "react": KafkaViz,
        "simple": SimpleViz,
        "mermaid": MermaidGenerator
    }
    
    return generators.get(name)

# Helper function to write file
def write_file(output_dir: Path, filename: str, content: str) -> None:
    """Write content to a file, creating directories if needed."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Write the file
    with open(output_dir / filename, "w", encoding="utf-8") as f:
        f.write(content)

# Clean node ID
def clean_node_id(topic: str) -> str:
    """Create safe node ID by replacing invalid characters."""
    # Special case for hash topic
    if topic == "#{":
        return "topic_hash"

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
        "{": "",  # Add explicit handling for curly braces
        "}": "",
    }
    result = topic
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result

# Format topic name
def format_topic_name(topic: str) -> str:
    """Format topic name for display."""
    if topic == "#{":
        return "hash_topic"
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
